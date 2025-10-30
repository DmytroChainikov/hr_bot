"""Команди для аналізу вакансій"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from core.logger_settings import create_logger
from core.config import Config
from core.analytics import AnalyticsService
from bot.commands.decorators import require_group_topic

logger = create_logger(__name__)


@require_group_topic
async def vacancy_analysis_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /vacancy_analysis - аналіз конкретної вакансії"""
    try:
        analytics: AnalyticsService = context.bot_data.get('analytics')
        if not analytics:
            await update.message.reply_text("❌ Сервіс аналітики недоступний")
            return
        
        # Отримуємо активні вакансії
        vacancies_with_stages = analytics._get_active_vacancies_with_stages()
        
        if not vacancies_with_stages:
            await update.message.reply_text(
                "⚠️ Немає активних вакансій для аналізу\n\n"
                "Перевірте:\n"
                "• Чи є активні вакансії в Hurma\n"
                "• Чи правильно налаштовані відстежувані вакансії (/vacancies)"
            )
            return
        
        # Створюємо клавіатуру з вакансіями
        keyboard = []
        
        for vacancy_id, vacancy_data in sorted(vacancies_with_stages.items()):
            vacancy_info = vacancy_data['info']
            vacancy_name = vacancy_info.get('name', f'Вакансія {vacancy_id}')
            
            # Скорочуємо назву якщо занадто довга
            display_name = vacancy_name[:60] + '...' if len(vacancy_name) > 60 else vacancy_name
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📋 {display_name}",
                    callback_data=f"vacancy_stats_{vacancy_id}"
                )
            ])
        
        # Додаємо кнопку "Всі вакансії"
        keyboard.append([
            InlineKeyboardButton(
                text="📊 Всі вакансії (загальна статистика)",
                callback_data="vacancy_stats_all"
            )
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📊 <b>Аналіз вакансій</b>\n\n"
            f"Оберіть вакансію для детального аналізу:\n"
            f"Всього активних вакансій: {len(vacancies_with_stages)}",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Помилка команди vacancy_analysis: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")


async def vacancy_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник callback для показу статистики по вакансії"""
    query = update.callback_query
    await query.answer()
    
    try:
        analytics: AnalyticsService = context.bot_data.get('analytics')
        if not analytics:
            await query.edit_message_text("❌ Сервіс аналітики недоступний")
            return
        
        # Отримуємо ID вакансії з callback_data
        callback_data = query.data
        
        if callback_data == "vacancy_stats_all":
            # Показуємо загальну статистику по всіх вакансіях
            report = analytics.get_all_vacancies_stats()
        else:
            vacancy_id = int(callback_data.replace("vacancy_stats_", ""))
            report = analytics.get_vacancy_stats(vacancy_id)
        
        # Створюємо кнопку "Назад"
        keyboard = [[
            InlineKeyboardButton(
                text="« Назад до списку",
                callback_data="vacancy_stats_back"
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=report,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Помилка vacancy_stats_callback: {e}")
        await query.edit_message_text(f"❌ Помилка: {str(e)}")


async def vacancy_stats_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник callback для повернення до списку вакансій"""
    query = update.callback_query
    await query.answer()
    
    try:
        analytics: AnalyticsService = context.bot_data.get('analytics')
        if not analytics:
            await query.edit_message_text("❌ Сервіс аналітики недоступний")
            return
        
        # Отримуємо активні вакансії
        vacancies_with_stages = analytics._get_active_vacancies_with_stages()
        
        # Створюємо клавіатуру з вакансіями
        keyboard = []
        
        for vacancy_id, vacancy_data in sorted(vacancies_with_stages.items()):
            vacancy_info = vacancy_data['info']
            vacancy_name = vacancy_info.get('name', f'Вакансія {vacancy_id}')
            
            display_name = vacancy_name[:60] + '...' if len(vacancy_name) > 60 else vacancy_name
            
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📋 {display_name}",
                    callback_data=f"vacancy_stats_{vacancy_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="📊 Всі вакансії (загальна статистика)",
                callback_data="vacancy_stats_all"
            )
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📊 <b>Аналіз вакансій</b>\n\n"
            f"Оберіть вакансію для детального аналізу:\n"
            f"Всього активних вакансій: {len(vacancies_with_stages)}",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Помилка vacancy_stats_back_callback: {e}")
        await query.edit_message_text(f"❌ Помилка: {str(e)}")


# Експорт для використання в main.py
__all__ = [
    'vacancy_analysis_command',
    'vacancy_stats_callback',
    'vacancy_stats_back_callback',
]
