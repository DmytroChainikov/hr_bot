"""Обробники команд телеграм бота"""
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, date, timedelta

from core.logger_settings import create_logger
from core.analytics import AnalyticsService
from core.config import Config

logger = create_logger(__name__)


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
    
    info_lines.append(f"\n<b>� Налаштування доступу:</b>")
    
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

<b>� Вакансії:</b>
/vacancies - Список відстежуваних вакансій
/add_vacancy [ID] [Назва] - Додати вакансію для відстеження
/remove_vacancy [ID] - Видалити вакансію з відстеження
   Приклад: /add_vacancy 12345 Senior Python Developer
   Приклад: /remove_vacancy 12345

<b>�🔧 Управління:</b>
/cache_info - Інформація про кеш кандидатів
/clear_cache - Очистити кеш (перезавантажити дані)
/chat_info - Отримати інформацію про чат (ID для налаштування)

<b>📋 Звіт містить:</b>
• Кількість дзвінків за день
• Список кандидатів у роботі (тільки по відстежуваних вакансіях)
• Розподіл по вакансіях та етапах
• Загальну статистику

<b>💡 Про вакансії:</b>
Якщо список відстежуваних вакансій порожній - показуються ВСІ вакансії. Додайте конкретні ID щоб звіти містили тільки потрібні вакансії.
"""
    await update.message.reply_text(help_message, parse_mode='HTML')


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
        error_message = "❌ <b>Помилка формування звіту</b>\n\n"
        
        if "Timeout" in str(e) or "Timed out" in str(e):
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
            error_message += f"📝 Деталі: <code>{str(e)}</code>"
        
        await update.message.reply_text(error_message, parse_mode='HTML')


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
        error_message = "❌ <b>Помилка формування звіту</b>\n\n"
        
        if "Timeout" in str(e) or "Timed out" in str(e):
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
            error_message += f"📝 Деталі: <code>{str(e)}</code>"
        
        await update.message.reply_text(error_message, parse_mode='HTML')


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
        error_message = "❌ <b>Помилка формування звіту</b>\n\n"
        
        if "Timeout" in str(e) or "Timed out" in str(e):
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
            error_message += f"📝 Деталі: <code>{str(e)}</code>"
        
        await update.message.reply_text(error_message, parse_mode='HTML')


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
        error_message = "❌ <b>Помилка формування звіту</b>\n\n"
        
        if "Timeout" in str(e) or "Timed out" in str(e):
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
            error_message += f"📝 Деталі: <code>{str(e)}</code>"
        
        await update.message.reply_text(error_message, parse_mode='HTML')


@require_group_topic
async def cache_info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /cache_info - інформація про кеш"""
    try:
        analytics: AnalyticsService = context.bot_data.get('analytics')
        if not analytics:
            await update.message.reply_text("❌ Сервіс аналітики недоступний")
            return
        
        cache_info = analytics.get_cache_info()
        
        if cache_info['cached']:
            message = (
                f"��� <b>Інформація про кеш</b>\n\n"
                f"✅ Статус: Активний\n"
                f"��� Кількість кандидатів: {cache_info['count']}\n"
                f"��� Дата кешу: {cache_info['date']}\n\n"
                f"��� Кеш автоматично оновлюється щодня"
            )
        else:
            message = (
                f"��� <b>Інформація про кеш</b>\n\n"
                f"⚠️ Статус: Порожній\n"
                f"��� Кеш буде створено при наступному запиті звіту"
            )
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Помилка отримання інформації про кеш: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")


@require_group_topic
async def clear_cache_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /clear_cache - очистка кешу"""
    try:
        analytics: AnalyticsService = context.bot_data.get('analytics')
        if not analytics:
            await update.message.reply_text("❌ Сервіс аналітики недоступний")
            return
        
        analytics.clear_cache()
        
        message = (
            f"��� <b>Кеш очищено</b>\n\n"
            f"✅ Кеш кандидатів успішно видалено\n"
            f"��� При наступному запиті дані будуть завантажені заново з Hurma API"
        )
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Помилка очистки кешу: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")


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
