"""
Команди для управління відстеженням топіків вакансій.
"""
from telegram import Update
from telegram.ext import ContextTypes

from core.topic_activity_tracker import TopicActivityTracker
from core.config import Config
from services.hurma_service import HurmaService
from bot.commands.decorators import admin_only
from core.logger_settings import create_logger

logger = create_logger(__name__)


@admin_only
async def register_topic_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /register_topic <vacancy_id> - реєструє поточний топік для вакансії.
    
    Використовується в топіку вакансії для прив'язки thread_id до vacancy_id.
    """
    # Перевіряємо чи це топік
    if not update.message.is_topic_message:
        await update.message.reply_text(
            "❌ Ця команда працює тільки в топіках.\n"
            "Використовуйте її в топіку вакансії."
        )
        return
    
    # Перевіряємо чи вказано vacancy_id
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Потрібно вказати ID вакансії.\n"
            "Використання: /register_topic <vacancy_id>"
        )
        return
    
    try:
        vacancy_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Невірний формат ID вакансії. Використайте число.")
        return
    
    thread_id = update.message.message_thread_id
    
    try:
        # Отримуємо назву вакансії з Hurma
        config = Config()
        hurma = HurmaService(
            client_id=config.HURMA_CLIENT_ID,
            client_secret=config.HURMA_CLIENT_SECRET,
            username=config.HURMA_USERNAME,
            password=config.HURMA_PASSWORD,
            company=config.HURMA_COMPANY
        )
        
        vacancies = hurma.get_job_openings(per_page=100)
        vacancy_name = None
        
        if vacancies and 'data' in vacancies:
            for vac in vacancies['data']:
                if vac['id'] == vacancy_id:
                    vacancy_name = vac.get('title', f'Вакансія #{vacancy_id}')
                    break
        
        if not vacancy_name:
            await update.message.reply_text(f"⚠️ Вакансію #{vacancy_id} не знайдено в Hurma")
            vacancy_name = f"Вакансія #{vacancy_id}"
        
        # Реєструємо топік
        tracker: TopicActivityTracker = context.bot_data.get('topic_tracker')
        if not tracker:
            await update.message.reply_text("❌ Трекер топіків не ініціалізовано")
            return
        
        tracker.register_topic(thread_id, vacancy_id, vacancy_name)
        
        # Оновлюємо активність (перше повідомлення)
        tracker.update_activity(
            thread_id, 
            update.message.from_user.id, 
            update.message.from_user.username
        )
        
        await update.message.reply_text(
            f"✅ Топік зареєстровано!\n\n"
            f"📋 Вакансія: <b>{vacancy_name}</b>\n"
            f"🆔 Vacancy ID: {vacancy_id}\n"
            f"💬 Thread ID: {thread_id}\n\n"
            f"Тепер активність в цьому топіку відстежується автоматично.",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Помилка реєстрації топіка: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")


@admin_only
async def topic_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /topic_stats - показує статистику по топіках вакансій.
    """
    tracker: TopicActivityTracker = context.bot_data.get('topic_tracker')
    
    if not tracker:
        await update.message.reply_text("❌ Трекер топіків не ініціалізовано")
        return
    
    stats = tracker.get_statistics()
    
    message = "📊 <b>Статистика топіків вакансій</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    message += f"📋 Всього топіків: <b>{stats['total_topics']}</b>\n"
    message += f"🟢 Активні сьогодні: <b>{stats['active_today']}</b>\n"
    message += f"📅 Активні цього тижня: <b>{stats['active_this_week']}</b>\n"
    message += f"⚠️ Неактивні 3+ дні: <b>{stats['inactive_3_plus_days']}</b>\n"
    message += f"📭 Ніколи не активні: <b>{stats['never_active']}</b>\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


@admin_only
async def inactive_topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /inactive_topics [days] - показує топіки без активності.
    
    За замовчуванням показує топіки без активності 3+ дні.
    """
    days_threshold = 3
    
    if context.args and len(context.args) > 0:
        try:
            days_threshold = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Невірний формат кількості днів.")
            return
    
    tracker: TopicActivityTracker = context.bot_data.get('topic_tracker')
    
    if not tracker:
        await update.message.reply_text("❌ Трекер топіків не ініціалізовано")
        return
    
    inactive = tracker.get_inactive_topics(days_threshold)
    
    if not inactive:
        await update.message.reply_text(
            f"✅ Немає неактивних топіків ({days_threshold}+ днів)"
        )
        return
    
    # Сортуємо за кількістю днів неактивності
    inactive.sort(key=lambda x: x['days_inactive'], reverse=True)
    
    message = f"⚠️ <b>Неактивні топіки ({days_threshold}+ днів)</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for topic in inactive[:15]:  # Максимум 15
        message += f"📋 <b>{topic['vacancy_name']}</b>\n"
        message += f"   🆔 Vacancy: {topic['vacancy_id']} | Thread: {topic['thread_id']}\n"
        message += f"   ⏱️ Неактивний: <b>{topic['days_inactive']} днів</b>\n"
        
        if topic.get('last_username'):
            message += f"   👤 Останнє від: @{topic['last_username']}\n"
        
        message += "\n"
    
    if len(inactive) > 15:
        message += f"... та ще {len(inactive) - 15} топіків\n"
    
    message += f"\n💡 <i>Детальніше: /topic_info <thread_id></i>"
    
    await update.message.reply_text(message, parse_mode='HTML')


@admin_only
async def topic_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /topic_info <thread_id> - показує детальну інформацію про топік.
    """
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Потрібно вказати thread ID.\n"
            "Використання: /topic_info <thread_id>"
        )
        return
    
    try:
        thread_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Невірний формат thread ID.")
        return
    
    tracker: TopicActivityTracker = context.bot_data.get('topic_tracker')
    
    if not tracker:
        await update.message.reply_text("❌ Трекер топіків не ініціалізовано")
        return
    
    info = tracker.get_topic_info(thread_id)
    
    if not info:
        await update.message.reply_text(f"❌ Топік {thread_id} не зареєстровано")
        return
    
    message = f"📋 <b>Інформація про топік</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    message += f"📌 Вакансія: <b>{info['vacancy_name']}</b>\n"
    message += f"🆔 Vacancy ID: {info['vacancy_id']}\n"
    message += f"💬 Thread ID: {thread_id}\n"
    message += f"📨 Всього повідомлень: {info.get('total_messages', 0)}\n\n"
    
    if info.get('last_message_time'):
        from datetime import datetime
        last_time = datetime.fromisoformat(info['last_message_time'])
        days_ago = (datetime.now() - last_time).days
        
        message += f"⏰ Остання активність:\n"
        message += f"   📅 {last_time.strftime('%d.%m.%Y %H:%M')}\n"
        message += f"   ⏱️ {days_ago} днів тому\n"
        
        if info.get('last_message_from_username'):
            message += f"   👤 @{info['last_message_from_username']}\n"
    else:
        message += "⚠️ Активності ще не було\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


@admin_only
async def list_topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /list_topics - показує всі зареєстровані топіки.
    """
    tracker: TopicActivityTracker = context.bot_data.get('topic_tracker')
    
    if not tracker:
        await update.message.reply_text("❌ Трекер топіків не ініціалізовано")
        return
    
    topics = tracker.get_all_topics()
    
    if not topics:
        await update.message.reply_text("📭 Немає зареєстрованих топіків")
        return
    
    # Сортуємо за останньою активністю
    from datetime import datetime
    
    def sort_key(topic):
        if not topic.get('last_message_time'):
            return datetime.min
        return datetime.fromisoformat(topic['last_message_time'])
    
    topics.sort(key=sort_key, reverse=True)
    
    message = f"📋 <b>Зареєстровані топіки ({len(topics)})</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    for topic in topics[:20]:  # Максимум 20
        status = "🟢"
        if topic.get('last_message_time'):
            last_time = datetime.fromisoformat(topic['last_message_time'])
            days_ago = (datetime.now() - last_time).days
            if days_ago >= 3:
                status = "🔴"
            elif days_ago >= 1:
                status = "🟡"
        else:
            status = "⚪"
        
        message += f"{status} <b>{topic['vacancy_name']}</b>\n"
        message += f"   🆔 V:{topic['vacancy_id']} | T:{topic['thread_id']}\n"
        
        if topic.get('last_message_time'):
            last_time = datetime.fromisoformat(topic['last_message_time'])
            message += f"   ⏰ {last_time.strftime('%d.%m %H:%M')}\n"
        
        message += "\n"
    
    if len(topics) > 20:
        message += f"... та ще {len(topics) - 20} топіків\n"
    
    message += "\n🟢 Активний | 🟡 1+ день | 🔴 3+ дні | ⚪ Немає активності"
    
    await update.message.reply_text(message, parse_mode='HTML')
