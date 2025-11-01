"""
Handler для автоматичного відстеження активності в топіках вакансій.
"""
from telegram import Update
from telegram.ext import ContextTypes

from core.topic_activity_tracker import TopicActivityTracker
from core.logger_settings import create_logger

logger = create_logger(__name__)


async def track_topic_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler який автоматично відстежує всі повідомлення в топіках.
    
    Оновлює час останньої активності для кожного топіка.
    """
    # Пропускаємо якщо це не повідомлення в топіку
    if not update.message or not update.message.is_topic_message:
        return
    
    # Пропускаємо повідомлення від бота
    if update.message.from_user.is_bot:
        return
    
    thread_id = update.message.message_thread_id
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    
    # Отримуємо трекер з bot_data
    tracker: TopicActivityTracker = context.bot_data.get('topic_tracker')
    
    if not tracker:
        logger.warning("TopicActivityTracker не ініціалізовано в bot_data")
        return
    
    # Оновлюємо активність
    tracker.update_activity(thread_id, user_id, username)
    
    logger.debug(
        f"Оновлено активність топіка {thread_id} "
        f"від користувача {username or user_id}"
    )
