"""
Команди для моніторингу руху кандидатів по воронці вакансій.
"""
from telegram import Update
from telegram.ext import ContextTypes

from core.candidate_flow_tracker import CandidateFlowTracker
from core.config import Config
from services.hurma_service import HurmaService
from bot.commands.decorators import admin_only
from core.logger_settings import create_logger

logger = create_logger(__name__)


@admin_only
async def funnel_health_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /funnel_health [vacancy_id] - показує здоров'я воронки вакансії.
    
    Без параметрів - показує всі активні вакансії.
    З vacancy_id - детальний аналіз конкретної вакансії.
    """
    user = update.effective_user
    config = Config()
    
    try:
        hurma = HurmaService(
            client_id=config.HURMA_CLIENT_ID,
            client_secret=config.HURMA_CLIENT_SECRET,
            username=config.HURMA_USERNAME,
            password=config.HURMA_PASSWORD,
            company=config.HURMA_COMPANY
        )
        
        tracker = CandidateFlowTracker(hurma)
        
        # Перевіряємо чи передано ID вакансії
        vacancy_id = None
        if context.args and len(context.args) > 0:
            try:
                vacancy_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Невірний формат ID вакансії. Використайте число.")
                return
        
        if vacancy_id:
            # Детальний аналіз однієї вакансії
            await _show_single_vacancy_health(update, tracker, vacancy_id)
        else:
            # Загальний огляд всіх активних вакансій
            await _show_all_vacancies_health(update, tracker, hurma)
            
    except Exception as e:
        logger.error(f"Помилка в funnel_health_command: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")


async def _show_single_vacancy_health(update: Update, tracker: CandidateFlowTracker, vacancy_id: int):
    """Показує детальний аналіз здоров'я воронки однієї вакансії"""
    await update.message.reply_text(f"🔍 Аналізую воронку вакансії #{vacancy_id}...")
    
    health = tracker.get_vacancy_funnel_health(vacancy_id)
    stagnant = tracker.detect_stagnant_candidates(vacancy_id, days_threshold=3)
    
    # Визначаємо емодзі статусу
    status_emoji = {
        'healthy': '✅',
        'warning': '⚠️',
        'critical': '🚨'
    }
    emoji = status_emoji.get(health['health_status'], '❓')
    
    # Формуємо повідомлення
    message = f"{emoji} <b>Здоров'я воронки вакансії #{vacancy_id}</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    message += f"👥 Всього кандидатів: <b>{health['total_candidates']}</b>\n"
    message += f"⏸️ Застійних: <b>{health['stagnant_candidates']}</b> ({health['stagnant_percentage']}%)\n"
    
    if health['average_days_stagnant'] > 0:
        message += f"📅 Середній час застою: <b>{health['average_days_stagnant']} днів</b>\n"
    
    message += f"\n🎯 Статус: <b>{health['health_status'].upper()}</b>\n"
    
    if health['issues']:
        message += "\n⚠️ <b>Виявлені проблеми:</b>\n"
        for issue in health['issues']:
            message += f"  • {issue}\n"
    
    # Показуємо застійних кандидатів
    if stagnant:
        message += f"\n<b>Застійні кандидати (3+ дні без змін):</b>\n"
        for candidate in stagnant[:10]:  # Максимум 10
            message += f"  • {candidate['name']} - етап {candidate['stage_id']} ({candidate['days_stagnant']} днів)\n"
        
        if len(stagnant) > 10:
            message += f"  ... та ще {len(stagnant) - 10}\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def _show_all_vacancies_health(update: Update, tracker: CandidateFlowTracker, hurma: HurmaService):
    """Показує загальний огляд здоров'я воронок всіх активних вакансій"""
    await update.message.reply_text("🔍 Аналізую всі активні вакансії...")
    
    # Отримуємо активні вакансії
    response = hurma.get_job_openings(per_page=100)
    
    if not response or 'data' not in response:
        await update.message.reply_text("❌ Не вдалося отримати список вакансій")
        return
    
    active_vacancies = [v for v in response['data'] if v.get('status') == 1]
    
    if not active_vacancies:
        await update.message.reply_text("📭 Немає активних вакансій")
        return
    
    # Аналізуємо кожну вакансію
    results = []
    for vacancy in active_vacancies[:20]:  # Обмежуємо до 20 вакансій
        vacancy_id = vacancy['id']
        vacancy_name = vacancy.get('title', f'Вакансія #{vacancy_id}')
        
        health = tracker.get_vacancy_funnel_health(vacancy_id)
        results.append({
            'id': vacancy_id,
            'name': vacancy_name,
            'health': health
        })
    
    # Сортуємо по серйозності проблем
    status_priority = {'critical': 0, 'warning': 1, 'healthy': 2}
    results.sort(key=lambda x: (
        status_priority.get(x['health']['health_status'], 3),
        -x['health']['stagnant_percentage']
    ))
    
    # Формуємо повідомлення
    message = "📊 <b>Здоров'я воронок активних вакансій</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    critical_count = sum(1 for r in results if r['health']['health_status'] == 'critical')
    warning_count = sum(1 for r in results if r['health']['health_status'] == 'warning')
    healthy_count = sum(1 for r in results if r['health']['health_status'] == 'healthy')
    
    message += f"🚨 Критичні: <b>{critical_count}</b>\n"
    message += f"⚠️ Увага: <b>{warning_count}</b>\n"
    message += f"✅ Здорові: <b>{healthy_count}</b>\n\n"
    
    # Показуємо проблемні вакансії
    if critical_count > 0 or warning_count > 0:
        message += "<b>Проблемні вакансії:</b>\n\n"
        
        for result in results:
            health = result['health']
            if health['health_status'] in ['critical', 'warning']:
                emoji = '🚨' if health['health_status'] == 'critical' else '⚠️'
                message += f"{emoji} <b>{result['name']}</b>\n"
                message += f"   ID: {result['id']} | Кандидатів: {health['total_candidates']} | "
                message += f"Застій: {health['stagnant_candidates']} ({health['stagnant_percentage']}%)\n"
                
                if health['issues']:
                    message += f"   • {health['issues'][0]}\n"
                
                message += "\n"
    else:
        message += "✅ Всі вакансії в здоровому стані!\n"
    
    message += "\n💡 <i>Детальніше: /funnel_health [vacancy_id]</i>"
    
    # Розбиваємо довге повідомлення
    if len(message) > 4000:
        await update.message.reply_text(message[:4000], parse_mode='HTML')
        await update.message.reply_text(message[4000:], parse_mode='HTML')
    else:
        await update.message.reply_text(message, parse_mode='HTML')


@admin_only
async def track_changes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда /track_changes <vacancy_id> - відстежує зміни етапів кандидатів.
    
    Порівнює поточний стан з попереднім snapshot і показує хто просунувся.
    """
    user = update.effective_user
    config = Config()
    
    # Перевіряємо чи передано ID вакансії
    if not context.args or len(context.args) == 0:
        await update.message.reply_text(
            "❌ Потрібно вказати ID вакансії.\n"
            "Використання: /track_changes <vacancy_id>"
        )
        return
    
    try:
        vacancy_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Невірний формат ID вакансії. Використайте число.")
        return
    
    try:
        hurma = HurmaService(
            client_id=config.HURMA_CLIENT_ID,
            client_secret=config.HURMA_CLIENT_SECRET,
            username=config.HURMA_USERNAME,
            password=config.HURMA_PASSWORD,
            company=config.HURMA_COMPANY
        )
        
        tracker = CandidateFlowTracker(hurma)
        
        await update.message.reply_text(f"🔍 Відстежую зміни для вакансії #{vacancy_id}...")
        
        moved_forward, moved_backward, new_candidates = tracker.track_stage_changes(vacancy_id)
        
        # Формуємо повідомлення
        message = f"📊 <b>Зміни по вакансії #{vacancy_id}</b>\n"
        message += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        if moved_forward:
            message += f"⬆️ <b>Просунулися вперед ({len(moved_forward)}):</b>\n"
            for candidate in moved_forward[:10]:
                message += (
                    f"  • {candidate['name']}: "
                    f"етап {candidate['previous_stage']} → {candidate['current_stage']}\n"
                )
            if len(moved_forward) > 10:
                message += f"  ... та ще {len(moved_forward) - 10}\n"
            message += "\n"
        
        if moved_backward:
            message += f"⬇️ <b>Відкотилися назад ({len(moved_backward)}):</b>\n"
            for candidate in moved_backward[:10]:
                message += (
                    f"  • {candidate['name']}: "
                    f"етап {candidate['previous_stage']} → {candidate['current_stage']}\n"
                )
            if len(moved_backward) > 10:
                message += f"  ... та ще {len(moved_backward) - 10}\n"
            message += "\n"
        
        if new_candidates:
            message += f"🆕 <b>Нові кандидати ({len(new_candidates)}):</b>\n"
            for candidate in new_candidates[:10]:
                message += f"  • {candidate['name']} (етап {candidate['stage_id']})\n"
            if len(new_candidates) > 10:
                message += f"  ... та ще {len(new_candidates) - 10}\n"
            message += "\n"
        
        if not moved_forward and not moved_backward and not new_candidates:
            message += "ℹ️ Змін не виявлено або це перший snapshot.\n"
        
        message += "\n💡 <i>Snapshot оновлено. Наступний виклик покаже зміни з цього моменту.</i>"
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Помилка в track_changes_command: {e}")
        await update.message.reply_text(f"❌ Помилка: {str(e)}")
