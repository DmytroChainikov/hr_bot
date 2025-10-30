"""Базові команди бота (start, help)"""
from telegram import Update
from telegram.ext import ContextTypes

from core.logger_settings import create_logger
from bot.commands.decorators import require_group_topic

logger = create_logger(__name__)


@require_group_topic
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    welcome_message = """
👋 <b>Привіт! Я бот для аналітики роботи HR.</b>

📊 Доступні команди:

<b>Звіти:</b>
/today - Звіт за сьогодні
/yesterday - Звіт за вчора
/report - Звіт за конкретну дату (формат: /report DD.MM.YYYY)
/my_report - Персональний звіт (вкажіть ім'я HR)

<b>Аналітика вакансій:</b>
/vacancy_analytics - Детальна статистика по вакансіях

<b>Вакансії:</b>
/vacancies - Список відстежуваних вакансій
/add_vacancy - Додати вакансію (ID та назва)
/remove_vacancy - Видалити вакансію

<b>Управління:</b>
/cache_info - Стан кешу кандидатів
/clear_cache - Очистити кеш
/chat_info - Інформація про чат та топік
/help - Детальна допомога

Приклади:
• /report 28.10.2025
• /add_vacancy 12345 Senior Python Developer

💡 Звіти формуються тільки по відстежуваних вакансіях
"""
    await update.message.reply_text(welcome_message, parse_mode='HTML')


@require_group_topic
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /help"""
    help_message = """
📖 <b>Довідка по командах:</b>

<b>📊 Звіти:</b>
/today - Отримати звіт за поточний день
/yesterday - Отримати звіт за вчорашній день
/report DD.MM.YYYY - Звіт за конкретну дату
/my_report [Ім'я HR] - Персональний звіт конкретного HR
   Приклад: /my_report Ірина

<b>📊 Аналітика вакансій:</b>
/vacancy_analytics - Інтерактивна статистика по вакансіях
   • Розподіл кандидатів по етапах
   • Візуалізація заповненості етапів
   • Статистика по HR
   • Останні оновлення

<b>�📁 Вакансії:</b>
/vacancies - Список відстежуваних вакансій
/add_vacancy [ID] [Назва] - Додати вакансію для відстеження
/remove_vacancy [ID] - Видалити вакансію з відстеження
   Приклад: /add_vacancy 12345 Senior Python Developer
   Приклад: /remove_vacancy 12345

<b>🔧 Управління:</b>
/cache_info - Інформація про кеш кандидатів
/clear_cache - Очистити кеш (перезавантажити дані)
/chat_info - Отримати інформацію про чат (ID для налаштування)

<b>📋 Звіт містить:</b>
• Кількість дзвінків за день
• Створені та оновлені кандидати окремо
• Розподіл по вакансіях та етапах
• Загальну статистику по HR

<b>💡 Про вакансії:</b>
Якщо список відстежуваних вакансій порожній - показуються ВСІ вакансії. Додайте конкретні ID щоб звіти містили тільки потрібні вакансії.

<b>⏰ Автоматичні звіти:</b>
Бот автоматично надсилає денні звіти о 18:00 по робочих днях.
"""
    await update.message.reply_text(help_message, parse_mode='HTML')
