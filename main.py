"""Головний файл запуску HR Analytics бота"""
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

from core.config import Config
from core.logger_settings import create_logger
from core.analytics import AnalyticsService
from services.hurma_service import HurmaService
from services.binotel_service import BinotelService
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
    add_vacancy_command,
    remove_vacancy_command,
    vacancy_analytics_command,
    vacancy_stats_callback,
)
from schedulers import setup_scheduler

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
    
    # Зберігаємо в контексті бота
    application.bot_data['hurma'] = hurma_service
    application.bot_data['binotel'] = binotel_service
    application.bot_data['analytics'] = analytics_service
    
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
        application.add_handler(CommandHandler("cache_info", cache_info_command))
        application.add_handler(CommandHandler("clear_cache", clear_cache_command))
        application.add_handler(CommandHandler("vacancies", list_vacancies_command))
        application.add_handler(CommandHandler("add_vacancy", add_vacancy_command))
        application.add_handler(CommandHandler("remove_vacancy", remove_vacancy_command))
        application.add_handler(CommandHandler("vacancy_analytics", vacancy_analytics_command))
        
        # Реєструємо обробники callback (для inline кнопок)
        application.add_handler(CallbackQueryHandler(
            vacancy_stats_callback,
            pattern=r'^vacancy_stats:'
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
