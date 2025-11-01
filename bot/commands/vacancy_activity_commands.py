"""
Команди для моніторингу активності вакансій.
"""
from telegram import Update
from telegram.ext import ContextTypes

from core.vacancy_activity_monitor import VacancyActivityMonitor
from core.config import Config
from services.hurma_service import HurmaService
from services.binotel_service import BinotelService
from bot.commands.decorators import admin_only
from core.logger_settings import create_logger

logger = create_logger(__name__)


@admin_only
async def vacancy_activity_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /vacancy_activity [vacancy_id] - показує активність вакансії.
    
    Без параметрів - загальна статистика.
    З vacancy_id - детальна інформація по конкретній вакансії.
    """
    config = Config()
    
    try:
        hurma = HurmaService(
            client_id=config.HURMA_CLIENT_ID,
            client_secret=config.HURMA_CLIENT_SECRET,
            username=config.HURMA_USERNAME,
            password=config.HURMA_PASSWORD,
            company=config.HURMA_COMPANY
        )
        
        binotel = BinotelService(config.BINOTEL_KEY, config.BINOTEL_SECRET)
        monitor = VacancyActivityMonitor(hurma, binotel)
        
        # Перевіряємо чи передано ID вакансії
        vacancy_id = None
        if context.args and len(context.args) > 0:
            try:
                vacancy_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Невірний формат ID вакансії.")
                return
        
        if vacancy_id:
            # Детальна інформація про вакансію
            await _show_vacancy_activity(update, monitor, vacancy_id)
        else:
            # Загальна статистика
            await _show_activity_summary(update, monitor)
            
    except Exception as e:
        logger.error(f"Помилка в vacancy_activity_command: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")


async def _show_vacancy_activity(update: Update, monitor: VacancyActivityMonitor, vacancy_id: int):
    """Показує детальну активність однієї вакансії"""
    await update.message.reply_text(f"🔍 Аналізую активність вакансії #{vacancy_id}...")
    
    activity = monitor.get_vacancy_activity(vacancy_id, days=7)
    
    # Визначаємо статус
    if activity['is_active']:
        status_emoji = "🟢"
        status_text = "Активна"
    elif activity['days_since_activity'] and activity['days_since_activity'] < 7:
        status_emoji = "🟡"
        status_text = "Знижена активність"
    else:
        status_emoji = "🔴"
        status_text = "Неактивна"
    
    message = f"{status_emoji} <b>Активність вакансії</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    message += f"📋 <b>{activity['vacancy_name']}</b>\n"
    message += f"🆔 ID: {activity['vacancy_id']}\n"
    message += f"📅 Період: останні {activity['period_days']} днів\n\n"
    
    message += f"📊 <b>Статус: {status_text}</b>\n\n"
    
    message += "<b>Активність:</b>\n"
    message += f"📞 Дзвінків: <b>{activity['calls_count']}</b>\n"
    message += f"🆕 Нових кандидатів: <b>{activity['new_candidates']}</b>\n"
    message += f"⬆️ Просунулися вперед: <b>{activity['candidates_moved_forward']}</b>\n"
    message += f"⬇️ Відкотилися назад: <b>{activity['candidates_moved_backward']}</b>\n\n"
    
    if activity['last_activity_date']:
        message += f"⏰ Остання активність: <b>{activity['last_activity_date']}</b>\n"
        if activity['days_since_activity'] is not None:
            message += f"📅 Днів тому: <b>{activity['days_since_activity']}</b>\n"
    else:
        message += "⚠️ Активності не виявлено\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def _show_activity_summary(update: Update, monitor: VacancyActivityMonitor):
    """Показує загальну статистику активності"""
    await update.message.reply_text("🔍 Аналізую активність всіх вакансій...")
    
    summary = monitor.get_activity_summary()
    
    message = "📊 <b>Загальна статистика активності вакансій</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    message += f"📋 Всього активних вакансій: <b>{summary['total_active_vacancies']}</b>\n\n"
    
    message += "<b>За статусом активності:</b>\n"
    message += f"🟢 Активні (< 3 дні): <b>{summary['active_vacancies']}</b>\n"
    message += f"🔴 Неактивні (3+ дні): <b>{summary['inactive_vacancies']}</b>\n\n"
    
    message += "<b>За останні 7 днів:</b>\n"
    message += f"📞 Всього дзвінків: <b>{summary['total_calls_week']}</b>\n"
    message += f"🆕 Нових кандидатів: <b>{summary['total_new_candidates_week']}</b>\n"
    message += f"⚠️ Вакансій без дзвінків: <b>{summary['vacancies_without_calls']}</b>\n\n"
    
    message += "💡 <i>Детальніше: /vacancy_activity [vacancy_id]</i>\n"
    message += "💡 <i>Неактивні: /inactive_vacancies</i>\n"
    message += "💡 <i>Без дзвінків: /vacancies_no_calls</i>"
    
    await update.message.reply_text(message, parse_mode='HTML')


@admin_only
async def inactive_vacancies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /inactive_vacancies [days] - показує вакансії без активності.
    """
    days_threshold = 3
    
    if context.args and len(context.args) > 0:
        try:
            days_threshold = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Невірний формат кількості днів.")
            return
    
    config = Config()
    
    try:
        hurma = HurmaService(
            client_id=config.HURMA_CLIENT_ID,
            client_secret=config.HURMA_CLIENT_SECRET,
            username=config.HURMA_USERNAME,
            password=config.HURMA_PASSWORD,
            company=config.HURMA_COMPANY
        )
        
        binotel = BinotelService(config.BINOTEL_KEY, config.BINOTEL_SECRET)
        monitor = VacancyActivityMonitor(hurma, binotel)
        
        await update.message.reply_text(f"🔍 Шукаю неактивні вакансії ({days_threshold}+ днів)...")
        
        inactive = monitor.get_inactive_vacancies(days_threshold)
        
        if not inactive:
            await update.message.reply_text(
                f"✅ Немає неактивних вакансій ({days_threshold}+ днів)"
            )
            return
        
        # Сортуємо за кількістю днів без активності
        inactive.sort(key=lambda x: x['days_since_activity'] if x['days_since_activity'] else 999, reverse=True)
        
        message = f"🔴 <b>Неактивні вакансії ({days_threshold}+ днів)</b>\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for vac in inactive[:15]:
            days = vac['days_since_activity'] if vac['days_since_activity'] else "∞"
            message += f"📋 <b>{vac['vacancy_name']}</b>\n"
            message += f"   🆔 ID: {vac['vacancy_id']} | Без активності: <b>{days} днів</b>\n"
            message += f"   📞 Дзвінків: {vac['calls_count']} | 🆕 Кандидатів: {vac['new_candidates']}\n"
            
            if vac.get('assigned_recruiters'):
                hrs = ', '.join(vac['assigned_recruiters'])
                message += f"   👤 HR: {hrs}\n"
            
            message += "\n"
        
        if len(inactive) > 15:
            message += f"... та ще {len(inactive) - 15} вакансій\n"
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Помилка в inactive_vacancies_command: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")


@admin_only
async def vacancies_no_calls_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /vacancies_no_calls - показує вакансії з кандидатами, але без дзвінків.
    """
    config = Config()
    
    try:
        hurma = HurmaService(
            client_id=config.HURMA_CLIENT_ID,
            client_secret=config.HURMA_CLIENT_SECRET,
            username=config.HURMA_USERNAME,
            password=config.HURMA_PASSWORD,
            company=config.HURMA_COMPANY
        )
        
        binotel = BinotelService(config.BINOTEL_KEY, config.BINOTEL_SECRET)
        monitor = VacancyActivityMonitor(hurma, binotel)
        
        await update.message.reply_text("🔍 Шукаю вакансії без дзвінків...")
        
        no_calls = monitor.get_vacancies_without_calls()
        
        if not no_calls:
            await update.message.reply_text("✅ Всі вакансії з кандидатами мають дзвінки!")
            return
        
        message = "⚠️ <b>Вакансії з кандидатами, але без дзвінків</b>\n"
        message += "<i>(за останні 7 днів)</i>\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        for vac in no_calls[:20]:
            message += f"📋 <b>{vac['vacancy_name']}</b>\n"
            message += f"   🆔 ID: {vac['vacancy_id']}\n"
            message += f"   👥 Кандидатів: <b>{vac['candidates_count']}</b>\n"
            message += f"   🆕 Нових за тиждень: {vac['new_candidates_week']}\n"
            
            if vac.get('assigned_recruiters'):
                hrs = ', '.join(vac['assigned_recruiters'])
                message += f"   👤 HR: {hrs}\n"
            
            message += "\n"
        
        if len(no_calls) > 20:
            message += f"... та ще {len(no_calls) - 20} вакансій\n"
        
        message += "\n💡 <i>Це може вказувати на недостатню роботу з кандидатами</i>"
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Помилка в vacancies_no_calls_command: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")
