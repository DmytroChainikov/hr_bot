"""Головний файл запуску HR Analytics бота"""
import asyncio
from telegram import Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler,
    filters,
    ContextTypes
)

from core.config import Config
from core.logger_settings import create_logger
from core.analytics import AnalyticsService
from services.hurma_service import HurmaService
from services.binotel_service import BinotelService
from services.gemini_service import GeminiService
from bot.conversation_handler import ConversationHandler
from bot.commands import (
    start_command,
    help_command,
    today_command,
    yesterday_command,
    report_command,
    my_report_command,
    chat_info_command,
    cache_info_command,
    clear_cache_command,
    list_vacancies_command,
    vacancy_analytics_command,
    vacancy_stats_callback,
)
from bot.handlers import (
    diff_command,
    hr_diff_command,
    mark_report_command,
    report_status_command,
)
from bot.commands.vacancy_progress import (
    vacancy_progress_command,
    vacancy_stagnant_command,
)
from bot.commands.funnel_tracking import (
    funnel_health_command,
    track_changes_command,
)
from bot.commands.topic_management import (
    register_topic_command,
    topic_stats_command,
    inactive_topics_command,
    topic_info_command,
    list_topics_command,
)
from bot.commands.vacancy_activity_commands import (
    vacancy_activity_command,
    inactive_vacancies_command,
    vacancies_no_calls_command,
)
from core.topic_activity_tracker import TopicActivityTracker
from schedulers import setup_scheduler
from schedulers.inactive_topics_check import setup_inactive_topics_scheduler
from schedulers.vacancy_activity_check import setup_vacancy_activity_scheduler

logger = create_logger(__name__)


async def post_init(application: Application):
    """Ініціалізація сервісів після запуску бота"""
    logger.info("Ініціалізація сервісів...")
    
    # Створюємо сервіси
    # Перевіряємо чи є OAuth credentials, якщо так - використовуємо їх
    if all([Config.HURMA_CLIENT_ID, Config.HURMA_CLIENT_SECRET, Config.HURMA_USERNAME, Config.HURMA_PASSWORD]):
        logger.info("Використовуємо OAuth автентифікацію для Hurma")
        hurma_service = HurmaService(
            client_id=Config.HURMA_CLIENT_ID,
            client_secret=Config.HURMA_CLIENT_SECRET,
            username=Config.HURMA_USERNAME,
            password=Config.HURMA_PASSWORD,
            company=Config.HURMA_COMPANY,
        )
    elif Config.HURMA_API_KEY:
        logger.info("Використовуємо API ключ для Hurma")
        hurma_service = HurmaService(api_key=Config.HURMA_API_KEY)
    else:
        raise ValueError("Необхідно вказати або HURMA_API_KEY, або OAuth credentials (HURMA_CLIENT_ID, HURMA_CLIENT_SECRET, HURMA_USERNAME, HURMA_PASSWORD)")
    
    binotel_service = BinotelService(Config.BINOTEL_KEY, Config.BINOTEL_SECRET)
    analytics_service = AnalyticsService(hurma_service, binotel_service)
    
    # Створюємо додаткові сервіси для Function Calling
    from core.candidate_flow_tracker import CandidateFlowTracker
    from core.vacancy_activity_monitor import VacancyActivityMonitor
    
    candidate_flow_tracker = CandidateFlowTracker(hurma_service)
    vacancy_activity_monitor = VacancyActivityMonitor(hurma_service, binotel_service)
    
    # Ініціалізуємо Gemini AI сервіс з Function Calling
    try:
        gemini_service = GeminiService(
            hurma_service=hurma_service,
            binotel_service=binotel_service,
            analytics=analytics_service,
            vacancy_activity_monitor=vacancy_activity_monitor,
            candidate_flow_tracker=candidate_flow_tracker
        )
        conversation_handler = ConversationHandler(gemini_service, analytics_service)
        logger.info("✅ Gemini AI сервіс ініціалізовано з Function Calling")
    except Exception as e:
        logger.warning(f"⚠️ Не вдалося ініціалізувати Gemini: {e}")
        logger.warning("Бот працюватиме без AI функцій")
        gemini_service = None
        conversation_handler = None
    
    # Зберігаємо в контексті бота
    application.bot_data['hurma'] = hurma_service
    application.bot_data['binotel'] = binotel_service
    application.bot_data['analytics'] = analytics_service
    application.bot_data['gemini'] = gemini_service
    application.bot_data['conversation_handler'] = conversation_handler
    application.bot_data['candidate_flow_tracker'] = candidate_flow_tracker
    application.bot_data['vacancy_activity_monitor'] = vacancy_activity_monitor
    
    # Ініціалізуємо трекер активності топіків
    try:
        topic_tracker = TopicActivityTracker()
        application.bot_data['topic_tracker'] = topic_tracker
        logger.info("✅ TopicActivityTracker ініціалізовано")
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації TopicActivityTracker: {e}")
    
    logger.info("Сервіси успішно ініціалізовані")
    
    # Виводимо інформацію про бота
    try:
        bot_info = await application.bot.get_me()
        logger.info(f"🤖 Bot: @{bot_info.username}")
    except Exception as e:
        logger.warning(f"Не вдалося отримати інформацію про бота: {e}")
    
    # Виводимо інформацію про HR
    hrs = Config.get_hrs()
    logger.info(f"Завантажено {len(hrs)} HR:")
    for hr in hrs:
        logger.info(f"  - {hr.name} (Hurma ID: {hr.hurma_id}, Binotel: {hr.binotel_internal})")
    
    # Запускаємо scheduler для автоматичних звітів
    try:
        scheduler = await setup_scheduler(application)
        application.bot_data['scheduler'] = scheduler
        logger.info("✅ Scheduler денних звітів запущено")
    except Exception as e:
        logger.error(f"❌ Помилка запуску scheduler: {e}")
        # Не критична помилка - продовжуємо роботу бота
    
    # Запускаємо scheduler для перевірки звітів HR
    try:
        from schedulers import setup_hr_report_check_scheduler
        hr_report_scheduler = await setup_hr_report_check_scheduler(application)
        application.bot_data['hr_report_check_scheduler'] = hr_report_scheduler
        logger.info("✅ Scheduler перевірки звітів HR запущено")
    except Exception as e:
        logger.error(f"❌ Помилка запуску HR report scheduler: {e}")
    
    # Запускаємо scheduler для щоденних звітів по вакансіях
    try:
        from schedulers.daily_vacancy_report import setup_daily_vacancy_report_scheduler
        vacancy_report_scheduler = await setup_daily_vacancy_report_scheduler(application)
        application.bot_data['vacancy_report_scheduler'] = vacancy_report_scheduler
        logger.info("✅ Scheduler щоденних звітів по вакансіях запущено")
    except Exception as e:
        logger.error(f"❌ Помилка запуску vacancy report scheduler: {e}")
    
    # Запускаємо scheduler для перевірки неактивних топіків
    try:
        setup_inactive_topics_scheduler(application)
        logger.info("✅ Scheduler перевірки неактивних топіків запущено")
    except Exception as e:
        logger.error(f"❌ Помилка запуску inactive topics scheduler: {e}")
    
    # Запускаємо scheduler для перевірки активності вакансій
    try:
        setup_vacancy_activity_scheduler(application)
        logger.info("✅ Scheduler перевірки активності вакансій запущено")
    except Exception as e:
        logger.error(f"❌ Помилка запуску vacancy activity scheduler: {e}")



async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник помилок"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Виникла помилка при обробці запиту. Спробуйте пізніше."
        )


def main():
    """Головна функція запуску бота"""
    try:
        # Перевірка конфігурації
        Config.validate()
        logger.info("✅ Конфігурація перевірена успішно")
        
        # Створюємо додаток
        application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).post_init(post_init).build()
        
        # Реєструємо обробники команд
        application.add_handler(CommandHandler("chat_info", chat_info_command))
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("today", today_command))
        application.add_handler(CommandHandler("yesterday", yesterday_command))
        application.add_handler(CommandHandler("report", report_command))
        application.add_handler(CommandHandler("my_report", my_report_command))
        application.add_handler(CommandHandler("diff", diff_command))
        application.add_handler(CommandHandler("hr_diff", hr_diff_command))
        application.add_handler(CommandHandler("mark_report", mark_report_command))
        application.add_handler(CommandHandler("report_status", report_status_command))
        application.add_handler(CommandHandler("cache_info", cache_info_command))
        application.add_handler(CommandHandler("clear_cache", clear_cache_command))
        application.add_handler(CommandHandler("vacancies", list_vacancies_command))
        application.add_handler(CommandHandler("vacancy_analytics", vacancy_analytics_command))
        application.add_handler(CommandHandler("vacancy_progress", vacancy_progress_command))
        application.add_handler(CommandHandler("vacancy_stagnant", vacancy_stagnant_command))
        application.add_handler(CommandHandler("funnel_health", funnel_health_command))
        application.add_handler(CommandHandler("track_changes", track_changes_command))
        application.add_handler(CommandHandler("register_topic", register_topic_command))
        application.add_handler(CommandHandler("topic_stats", topic_stats_command))
        application.add_handler(CommandHandler("inactive_topics", inactive_topics_command))
        application.add_handler(CommandHandler("topic_info", topic_info_command))
        application.add_handler(CommandHandler("list_topics", list_topics_command))
        application.add_handler(CommandHandler("vacancy_activity", vacancy_activity_command))
        application.add_handler(CommandHandler("vacancies_no_calls", vacancies_no_calls_command))
        
        # Реєструємо обробники callback (для inline кнопок)
        application.add_handler(CallbackQueryHandler(
            vacancy_stats_callback,
            pattern=r'^vacancy_stats:'
        ))
        
        # Реєструємо обробник звичайних повідомлень (для AI розмов)
        # MessageHandler повинен бути ОСТАННІМ, щоб команди оброблялись першими
        async def message_handler_wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            """Обгортка для обробника повідомлень з перевіркою топіку"""
            # Спочатку відстежуємо активність в топіку
            if update.message and update.message.is_topic_message:
                tracker = context.bot_data.get('topic_tracker')
                if tracker and not update.message.from_user.is_bot:
                    thread_id = update.message.message_thread_id
                    user_id = update.message.from_user.id
                    username = update.message.from_user.username
                    tracker.update_activity(thread_id, user_id, username)
            
            # Перевіряємо доступ до групи та топіку
            allowed_groups = Config.get_allowed_group_ids()
            allowed_topics = Config.get_allowed_topic_ids()
            
            chat = update.effective_chat
            message = update.message
            
            if not chat or not message:
                return
            
            chat_id = chat.id
            topic_id = message.message_thread_id
            
            # Перевіряємо групу
            if allowed_groups and chat_id not in allowed_groups:
                logger.warning(f"Доступ заборонено з чату {chat_id}")
                return
            
            # Перевіряємо топік
            if allowed_topics:
                if topic_id is None:
                    logger.warning(f"Повідомлення не з топіка в чаті {chat_id}")
                    return
                
                if topic_id not in allowed_topics:
                    logger.warning(f"Доступ заборонено з топіка {topic_id} в чаті {chat_id}")
                    return
            
            # Якщо перевірки пройдені - обробляємо повідомлення
            
            # Перевіряємо чи це схоже на звіт HR
            from bot.handlers import is_likely_report, mark_hr_report_received
            if message.text and is_likely_report(message.text):
                await mark_hr_report_received(update, context)
            
            conversation_handler = context.bot_data.get('conversation_handler')
            if conversation_handler:
                await conversation_handler.handle_message(update, context)
            else:
                # Якщо Gemini не доступний, показуємо список команд
                await update.message.reply_text(
                    "🤖 AI функції недоступні. Використовуй команди:\n"
                    "/help - список команд\n"
                    "/today - звіт за сьогодні\n"
                    "/vacancy_analytics - аналітика по вакансіях"
                )
        
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler_wrapper
        ))
        
        # Обробник помилок
        application.add_error_handler(error_handler)
        
        logger.info("🚀 HR Analytics Bot запущено")
        
        # Запускаємо polling
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"❌ Критична помилка при запуску бота: {e}")
        raise


if __name__ == "__main__":
    main()
