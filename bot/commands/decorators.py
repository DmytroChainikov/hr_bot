"""Декоратори для обробників команд"""
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes

from core.logger_settings import create_logger
from core.config import Config

logger = create_logger(__name__)


def require_admin(func):
    """Декоратор для перевірки що команду виконує адміністратор"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if not user:
            await update.message.reply_text("❌ Не вдалося визначити користувача")
            return
        
        # Отримуємо ID адміністратора з конфігу
        admin_chat_id = Config.ADMIN_CHAT_ID
        
        # Якщо не налаштовано - дозволяємо всім (для розробки)
        if not admin_chat_id:
            logger.warning("ADMIN_CHAT_ID не налаштовано - команда доступна всім")
            return await func(update, context)
        
        # Перевіряємо чи користувач є адміном
        try:
            admin_id = int(admin_chat_id)
            if user.id != admin_id:
                logger.warning(f"Доступ заборонено: користувач {user.id} спробував виконати адмін-команду")
                await update.message.reply_text(
                    "❌ Доступ заборонено\n\n"
                    "Ця команда доступна лише адміністраторам."
                )
                return
        except ValueError:
            logger.error(f"Невірний формат ADMIN_CHAT_ID: {admin_chat_id}")
            await update.message.reply_text("❌ Помилка конфігурації")
            return
        
        # Користувач - адмін, виконуємо команду
        return await func(update, context)
    
    return wrapper


# Alias для сумісності
admin_only = require_admin


def require_group_topic(func):
    """Декоратор для перевірки що команда виконується в дозволеній групі/топіку"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        # Перевіряємо чи є дозволені групи
        allowed_groups = Config.get_allowed_group_ids()
        allowed_topics = Config.get_allowed_topic_ids()
        
        # Якщо обидва списки порожні - дозволяємо всім (для тестування)
        if not allowed_groups and not allowed_topics:
            logger.warning("ALLOWED_GROUP_IDS та ALLOWED_TOPIC_IDS не налаштовано - бот доступний всім")
            return await func(update, context)
        
        # Перевіряємо чи це повідомлення з групи
        chat = update.effective_chat
        message = update.message
        if not chat or not message:
            await update.message.reply_text("❌ Не вдалося визначити чат")
            return
        
        chat_id = chat.id
        topic_id = message.message_thread_id
        
        # Перевіряємо чи група в списку дозволених (якщо список не порожній)
        if allowed_groups and chat_id not in allowed_groups:
            logger.warning(f"Доступ заборонено з чату {chat_id} (користувач: {update.effective_user.id})")
            await update.message.reply_text(
                "❌ Доступ заборонено\n\n"
                "Цей бот доступний лише в авторизованих групах.\n"
                "Використайте /chat_info щоб дізнатися ID цього чату."
            )
            return
        
        # Перевіряємо топік (якщо список топіків не порожній)
        if allowed_topics:
            # Якщо топіки налаштовані, повідомлення ПОВИННО бути з топіка
            if topic_id is None:
                logger.warning(f"Доступ заборонено: повідомлення не з топіка (чат: {chat_id}, користувач: {update.effective_user.id})")
                await update.message.reply_text(
                    "❌ Доступ заборонено\n\n"
                    "Бот працює лише в певних топіках.\n"
                    "Використайте /chat_info щоб дізнатися ID поточного топіка."
                )
                return
            
            # Перевіряємо чи топік в списку дозволених
            if topic_id not in allowed_topics:
                logger.warning(f"Доступ заборонено з топіка {topic_id} (чат: {chat_id}, користувач: {update.effective_user.id})")
                await update.message.reply_text(
                    "❌ Доступ заборонено\n\n"
                    "Цей топік не авторизовано для роботи з ботом.\n"
                    f"Поточний Topic ID: {topic_id}\n"
                    "Використайте /chat_info для деталей."
                )
                return
        
        # Все ок - виконуємо команду
        return await func(update, context)
    
    return wrapper
