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
👋 <b>Привіт! Я головний рекрутер вашої команди!</b>

🤖 <b>Я можу спілкуватися як людина:</b>
• Просто напиши мені повідомлення - я відповім
• Надішли звіт - я його проаналізую
• Запитай про роботу - я дам пораду
• Обговори кандидата - я допоможу

� <b>Розумію природні фрази як команди:</b>
• "Дай звіт за сьогодні" → покажу звіт
• "Покажи статистику вакансій" → відкрию аналітику
• "Список вакансій" → покажу всі вакансії
• "Допомога" → покажу всі можливості

📊 <b>Команди (можна і без /):</b>

<b>Звіти:</b>
/today - Звіт за сьогодні
/yesterday - Звіт за вчора
/report DD.MM.YYYY - Звіт за дату
/my_report [Ім'я] - Персональний звіт

<b>Аналітика:</b>
/vacancy_analytics - Статистика по вакансіях
/vacancies - Список вакансій

<b>Управління:</b>
/cache_info - Стан кешу
/clear_cache - Очистити кеш
/help - Детальна допомога

� <b>Приклади розмови:</b>
• "Привіт! Як справи?"
• "Сьогодні створив 3 кандидати"
• "Як покращити конверсію?"
• "Дай звіт за сьогодні"

✨ <b>Працюю на AI - розумію тебе!</b>
"""
    await update.message.reply_text(welcome_message, parse_mode='HTML')


@require_group_topic
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /help"""
    help_message = """
📖 <b>Довідка по роботі з ботом:</b>

🤖 <b>Природне спілкування:</b>
Пиши мені як людині - я розумію!

<b>Замість команд можна писати:</b>
• "Дай звіт за сьогодні" → /today
• "Покажи статистику вакансій" → /vacancy_analytics
• "Список вакансій" → /vacancies
• "Звіт за вчора" → /yesterday
• "Очисти кеш" → /clear_cache
• "Допомога" → /help

━━━━━━━━━━━━━━━━━━━━

<b>📊 Звіти:</b>
/today - Звіт за сьогодні
/yesterday - Звіт за вчора
/report DD.MM.YYYY - Звіт за дату
/my_report [Ім'я] - Персональний звіт

<b>📊 Аналітика:</b>
/vacancy_analytics - Детальна статистика
/vacancies - Список вакансій

<b>🔧 Управління:</b>
/cache_info - Інфо про кеш
/clear_cache - Очистити кеш
/chat_info - Інфо про чат

━━━━━━━━━━━━━━━━━━━━

💬 <b>Приклади розмови:</b>
• "Привіт! Що думаєш про мої результати?"
• "Сьогодні провів 5 інтерв'ю, створив 3 кандидати"
• "Що робити з кандидатом який не відповідає?"
• "Як покращити швидкість найму?"

✨ <b>Google Gemini AI розуміє контекст!</b>
Просто пиши - я завжди допоможу 💪
"""
    await update.message.reply_text(help_message, parse_mode='HTML')

from telegram import Update
from telegram.ext import ContextTypes

from core.logger_settings import create_logger
from bot.commands.decorators import require_group_topic

logger = create_logger(__name__)


@require_group_topic
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start"""
    welcome_message = """
👋 <b>Привіт! Я головний рекрутер вашої команди!</b>

🤖 <b>Я можу спілкуватися як людина:</b>
• Просто напиши мені повідомлення - я відповім
• Надішли звіт - я його проаналізую
• Запитай про роботу - я дам пораду
• Обговори кандидата - я допоможу

📊 <b>Також доступні команди:</b>

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

💬 <b>Приклади спілкування:</b>
• "Привіт, як справи?"
• "Сьогодні створив 5 кандидатів на позицію Python Developer"
• "Що думаєш про результати за тиждень?"
• "Як покращити конверсію на етапі інтерв'ю?"

✨ <b>Я використовую AI для природного спілкування!</b>
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
