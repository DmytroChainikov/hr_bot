"""Команди для роботи зі звітами"""
from datetime import date, timedelta, datetime
from telegram import Update
from telegram.ext import ContextTypes

from core.logger_settings import create_logger
from core.analytics import AnalyticsService
from bot.commands.decorators import require_group_topic

logger = create_logger(__name__)


@require_group_topic
async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /today - звіт за сьогодні"""
    await update.message.reply_text("⏳ Формую звіт за сьогодні...")
    
    try:
        analytics: AnalyticsService = context.bot_data.get('analytics')
        if not analytics:
            await update.message.reply_text("❌ Сервіс аналітики недоступний")
            return
        
        reports = analytics.get_daily_hr_report(date.today())
        
        # Надсилаємо кілька повідомлень
        for report in reports:
            await update.message.reply_text(report, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Помилка формування звіту за сьогодні: {e}")
        await _send_error_message(update, e)


@require_group_topic
async def yesterday_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /yesterday - звіт за вчора"""
    await update.message.reply_text("⏳ Формую звіт за вчора...")
    
    try:
        analytics: AnalyticsService = context.bot_data.get('analytics')
        if not analytics:
            await update.message.reply_text("❌ Сервіс аналітики недоступний")
            return
        
        yesterday = date.today() - timedelta(days=1)
        reports = analytics.get_daily_hr_report(yesterday)
        
        # Надсилаємо кілька повідомлень
        for report in reports:
            await update.message.reply_text(report, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Помилка формування звіту за вчора: {e}")
        await _send_error_message(update, e)


@require_group_topic
async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /report - звіт за конкретну дату"""
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Вкажіть дату у форматі DD.MM.YYYY\n"
            "Приклад: /report 28.10.2025"
        )
        return
    
    date_str = context.args[0]
    
    try:
        # Парсимо дату
        report_date = datetime.strptime(date_str, "%d.%m.%Y").date()
        
        await update.message.reply_text(f"⏳ Формую звіт за {date_str}...")
        
        analytics: AnalyticsService = context.bot_data.get('analytics')
        if not analytics:
            await update.message.reply_text("❌ Сервіс аналітики недоступний")
            return
        
        reports = analytics.get_daily_hr_report(report_date)
        
        # Надсилаємо кілька повідомлень
        for report in reports:
            await update.message.reply_text(report, parse_mode='HTML')
        
    except ValueError:
        await update.message.reply_text(
            "❌ Невірний формат дати. Використовуйте DD.MM.YYYY\n"
            "Приклад: /report 28.10.2025"
        )
    except Exception as e:
        logger.error(f"Помилка формування звіту за {date_str}: {e}")
        await _send_error_message(update, e)


@require_group_topic
async def my_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /my_report - персональний звіт HR"""
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Вкажіть ім'я HR\n"
            "Приклад: /my_report Ірина"
        )
        return
    
    hr_name = " ".join(context.args)
    
    try:
        await update.message.reply_text(f"⏳ Формую звіт для {hr_name}...")
        
        analytics: AnalyticsService = context.bot_data.get('analytics')
        if not analytics:
            await update.message.reply_text("❌ Сервіс аналітики недоступний")
            return
        
        report = analytics.get_hr_personal_report(hr_name, date.today())
        await update.message.reply_text(report, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Помилка формування персонального звіту для {hr_name}: {e}")
        await _send_error_message(update, e)


async def _send_error_message(update: Update, error: Exception):
    """
    Надіслати форматоване повідомлення про помилку
    
    Args:
        update: Telegram update
        error: Виняток що стався
    """
    error_message = "❌ <b>Помилка формування звіту</b>\n\n"
    
    if "Timeout" in str(error) or "Timed out" in str(error):
        error_message += (
            "⏱ <b>Таймаут запиту до API</b>\n\n"
            "Можливі причини:\n"
            "• Повільне з'єднання з інтернетом\n"
            "• API Hurma або Binotel не відповідає\n"
            "• Занадто велика кількість даних\n\n"
            "💡 Спробуйте:\n"
            "• Повторити запит через кілька хвилин\n"
            "• Перевірити доступність API\n"
            "• Звернутися до адміністратора"
        )
    else:
        error_message += f"📝 Деталі: <code>{str(error)}</code>"
    
    await update.message.reply_text(error_message, parse_mode='HTML')
