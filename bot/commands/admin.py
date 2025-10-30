"""Адміністративні команди (кеш, інформація про чат)"""
from telegram import Update
from telegram.ext import ContextTypes

from core.logger_settings import create_logger
from core.config import Config
from core.analytics import AnalyticsService

logger = create_logger(__name__)


async def chat_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для визначення ID чату та топіка"""
    chat = update.effective_chat
    user = update.effective_user
    message = update.message
    
    info_lines = []
    info_lines.append("🔍 <b>Інформація про чат:</b>\n")
    info_lines.append(f"<b>Chat ID:</b> <code>{chat.id}</code>")
    info_lines.append(f"<b>Chat Type:</b> {chat.type}")
    
    if chat.title:
        info_lines.append(f"<b>Chat Title:</b> {chat.title}")
    
    topic_id = message.message_thread_id
    if topic_id:
        info_lines.append(f"<b>Topic ID:</b> <code>{topic_id}</code>")
        # Перевіряємо чи топік в дозволених
        allowed_topics = Config.get_allowed_topic_ids()
        if allowed_topics:
            if topic_id in allowed_topics:
                info_lines.append(f"   ✅ Топік авторизовано")
            else:
                info_lines.append(f"   ❌ Топік НЕ авторизовано")
    else:
        info_lines.append(f"<b>Topic ID:</b> Немає (загальний чат)")
    
    info_lines.append(f"\n<b>Your User ID:</b> <code>{user.id}</code>")
    
    if user.username:
        info_lines.append(f"<b>Your Username:</b> @{user.username}")
    
    # Перевіряємо статус доступу
    allowed_groups = Config.get_allowed_group_ids()
    allowed_topics = Config.get_allowed_topic_ids()
    
    info_lines.append(f"\n<b>🔒 Налаштування доступу:</b>")
    
    if allowed_groups:
        if chat.id in allowed_groups:
            info_lines.append(f"✅ Група авторизована")
        else:
            info_lines.append(f"❌ Група НЕ авторизована")
    else:
        info_lines.append(f"⚠️  Список груп порожній (доступ для всіх)")
    
    if allowed_topics:
        info_lines.append(f"🔒 Обмеження по топіках активне ({len(allowed_topics)} топіків)")
    else:
        info_lines.append(f"🔓 Обмеження по топіках відсутнє")
    
    info_lines.append(f"\n💡 <b>Щоб налаштувати доступ, додайте в .env:</b>")
    info_lines.append(f"<code>ALLOWED_GROUP_IDS={chat.id}</code>")
    
    if topic_id:
        info_lines.append(f"<code>ALLOWED_TOPIC_IDS={topic_id}</code>")
        info_lines.append(f"\n<i>Або додайте через кому до існуючих</i>")
    
    await update.message.reply_text("\n".join(info_lines), parse_mode='HTML')


async def cache_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /cache_info - інформація про кеш"""
    try:
        analytics: AnalyticsService = context.bot_data.get('analytics')
        if not analytics:
            await update.message.reply_text("❌ Сервіс аналітики недоступний")
            return
        
        cache_info = analytics.get_cache_info()
        
        candidates_info = cache_info['candidates']
        vacancies_info = cache_info['vacancies']
        
        message = "💾 <b>Інформація про кеш</b>\n\n"
        
        # Інформація про кандидатів
        message += "<b>👥 Кандидати:</b>\n"
        if candidates_info['cached']:
            message += (
                f"✅ Статус: Активний\n"
                f"📊 Кількість: {candidates_info['count']}\n"
                f"🕐 Дата: {candidates_info['date']}\n\n"
            )
        else:
            message += "⚠️ Статус: Порожній\n\n"
        
        # Інформація про вакансії
        message += "<b>🎯 Вакансії:</b>\n"
        if vacancies_info['cached']:
            message += (
                f"✅ Статус: Активний\n"
                f"📊 Кількість: {vacancies_info['count']}\n"
                f"🕐 Дата: {vacancies_info['date']}\n\n"
            )
        else:
            message += "⚠️ Статус: Порожній\n\n"
        
        message += "🔄 Кеш автоматично оновлюється щодня"
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Помилка отримання інформації про кеш: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")


async def clear_cache_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /clear_cache - очистка кешу"""
    try:
        analytics: AnalyticsService = context.bot_data.get('analytics')
        if not analytics:
            await update.message.reply_text("❌ Сервіс аналітики недоступний")
            return
        
        analytics.clear_cache()
        
        message = (
            f"🗑 <b>Кеш очищено</b>\n\n"
            f"✅ Кеш кандидатів успішно видалено\n"
            f"🔄 При наступному запиті дані будуть завантажені заново з Hurma API"
        )
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Помилка очистки кешу: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")
