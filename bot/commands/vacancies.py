"""Команди для роботи з вакансіями"""
from telegram import Update
from telegram.ext import ContextTypes

from core.logger_settings import create_logger
from core.config import Config
from core.analytics import AnalyticsService
from bot.commands.decorators import require_group_topic

logger = create_logger(__name__)


@require_group_topic
async def list_vacancies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /vacancies - список відстежуваних вакансій"""
    try:
        vacancies = Config.get_vacancies()
        
        if not vacancies:
            message = (
                "📋 <b>Відстежувані вакансії</b>\n\n"
                "⚠️ Список порожній - відстежуються ВСІ вакансії\n\n"
                "💡 Додайте вакансію: /add_vacancy 12345 Назва вакансії"
            )
        else:
            message = (
                f"📋 <b>Відстежувані вакансії</b>\n\n"
                f"✅ Активних: {len(vacancies)}\n\n"
            )
            for vid, name in vacancies.items():
                message += f"• <b>{name}</b>\n  <code>ID: {vid}</code>\n\n"
            
            message += (
                "💡 Команди:\n"
                "• Додати: /add_vacancy [ID] [Назва]\n"
                "• Видалити: /remove_vacancy [ID]"
            )
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Помилка отримання списку вакансій: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")


@require_group_topic
async def add_vacancy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /add_vacancy - додати вакансію для відстеження"""
    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "❌ Вкажіть ID вакансії та назву\n"
            "Приклад: /add_vacancy 12345 Senior Python Developer"
        )
        return
    
    try:
        vacancy_id = int(context.args[0])
        vacancy_name = ' '.join(context.args[1:])
        
        if Config.add_vacancy(vacancy_id, vacancy_name):
            # Очищаємо кеш щоб нові дані завантажилися
            analytics: AnalyticsService = context.bot_data.get('analytics')
            if analytics:
                analytics.clear_cache()
            
            message = (
                f"✅ <b>Вакансію додано</b>\n\n"
                f"📋 <b>{vacancy_name}</b>\n"
                f"   <code>ID: {vacancy_id}</code>\n\n"
                f"📊 Всього відстежується: {len(Config.get_vacancy_ids())}\n\n"
                f"💡 Кеш очищено - при наступному звіті дані оновляться"
            )
        else:
            message = (
                f"⚠️ <b>Вакансія вже відстежується</b>\n\n"
                f"📋 <b>{vacancy_name}</b>\n"
                f"   <code>ID: {vacancy_id}</code>\n\n"
                f"Перегляньте список: /vacancies"
            )
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except ValueError:
        await update.message.reply_text(
            "❌ Невірний формат ID\n"
            "ID вакансії має бути числом\n"
            "Приклад: /add_vacancy 12345 Senior Python Developer"
        )
    except Exception as e:
        logger.error(f"Помилка додавання вакансії: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")


@require_group_topic
async def remove_vacancy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /remove_vacancy - видалити вакансію з відстеження"""
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Вкажіть ID вакансії\n"
            "Приклад: /remove_vacancy 12345\n\n"
            "Перегляньте список: /vacancies"
        )
        return
    
    try:
        vacancy_id = int(context.args[0])
        
        success, vacancy_name = Config.remove_vacancy(vacancy_id)
        
        if success:
            # Очищаємо кеш щоб нові дані завантажилися
            analytics: AnalyticsService = context.bot_data.get('analytics')
            if analytics:
                analytics.clear_cache()
            
            remaining = Config.get_vacancy_ids()
            message = (
                f"🗑 <b>Вакансію видалено</b>\n\n"
                f"📋 <b>{vacancy_name}</b>\n"
                f"   <code>ID: {vacancy_id}</code>\n\n"
                f"📊 Залишилось: {len(remaining)}\n\n"
            )
            
            if not remaining:
                message += "⚠️ Список порожній - тепер відстежуються ВСІ вакансії\n\n"
            
            message += "💡 Кеш очищено - при наступному звіті дані оновляться"
        else:
            message = (
                f"⚠️ <b>Вакансія не знайдена</b>\n\n"
                f"📋 ID вакансії: <code>{vacancy_id}</code>\n\n"
                f"Перегляньте список: /vacancies"
            )
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except ValueError:
        await update.message.reply_text(
            "❌ Невірний формат ID\n"
            "ID вакансії має бути числом\n"
            "Приклад: /remove_vacancy 12345"
        )
    except Exception as e:
        logger.error(f"Помилка видалення вакансії: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")
