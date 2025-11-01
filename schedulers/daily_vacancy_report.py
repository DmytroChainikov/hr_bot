"""Scheduler для щоденного аналізу та звіту по проблемних вакансіях"""
import asyncio
from datetime import datetime, time
from typing import Dict, List, Any

from telegram.ext import Application
from telegram.constants import ParseMode

from core.config import Config
from core.vacancy_analytics import VacancyAnalytics
from core.hr_push_service import HRPushService
from services.hurma_service import HurmaService
from services.binotel_service import BinotelService
from services.gemini_service import GeminiService
from core.logger_settings import create_logger

logger = create_logger(__name__)


async def _analyze_all_vacancies(
    vacancy_analytics: VacancyAnalytics
) -> Dict[str, Any]:
    """
    Проаналізувати всі активні вакансії
    
    Returns:
        Словник з аналітикою
    """
    result = {
        'total_active': 0,
        'with_candidates': 0,
        'without_candidates': 0,
        'stagnant': [],
        'vacancies_with_issues': []
    }
    
    try:
        # Отримуємо всі активні вакансії
        active_vacancies = vacancy_analytics.get_active_vacancies(force_refresh=True)
        result['total_active'] = len(active_vacancies)
        
        logger.info(f"Аналіз {result['total_active']} активних вакансій")
        
        # Аналізуємо кожну вакансію
        for vacancy in active_vacancies:
            vacancy_id = vacancy['id']
            vacancy_name = vacancy.get('name', 'Unknown')
            
            # Отримуємо кількість кандидатів
            candidates = vacancy_analytics.get_vacancy_candidates_count(vacancy_id)
            total_candidates = candidates.get('__total__', 0)
            
            if total_candidates > 0:
                result['with_candidates'] += 1
                
                # Перевіряємо чи є проблеми
                # Якщо всі кандидати на першому етапі - можливий застій
                stage_counts = [v for k, v in candidates.items() if k != '__total__']
                if stage_counts and len(stage_counts) > 0:
                    first_stage_count = stage_counts[0]
                    
                    if first_stage_count == total_candidates and total_candidates > 3:
                        # Застій - всі на першому етапі
                        result['stagnant'].append({
                            'id': vacancy_id,
                            'name': vacancy_name,
                            'candidates_count': total_candidates,
                            'issue': 'Всі кандидати на першому етапі',
                            'responsible': vacancy.get('responsible', [])
                        })
                        result['vacancies_with_issues'].append({
                            'id': vacancy_id,
                            'name': vacancy_name,
                            'issue_type': 'stagnant',
                            'details': f'{total_candidates} кандидатів на першому етапі'
                        })
            else:
                result['without_candidates'] += 1
        
        logger.info(
            f"Результат аналізу: {result['with_candidates']} з кандидатами, "
            f"{len(result['stagnant'])} з застоєм"
        )
        
    except Exception as e:
        logger.error(f"Помилка аналізу вакансій: {e}", exc_info=True)
    
    return result


async def _format_daily_report(
    analysis: Dict[str, Any],
    config: Config
) -> str:
    """
    Форматувати щоденний звіт
    
    Args:
        analysis: Результати аналізу
        config: Конфігурація
        
    Returns:
        Форматований текст звіту
    """
    report = "📊 <b>Щоденний звіт по активних вакансіях</b>\n"
    report += f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}\n"
    report += "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Загальна статистика
    report += f"📋 Всього активних вакансій: <b>{analysis['total_active']}</b>\n"
    report += f"👥 З кандидатами: <b>{analysis['with_candidates']}</b>\n"
    report += f"📭 Без кандидатів: <b>{analysis['without_candidates']}</b>\n\n"
    
    # Проблемні вакансії
    total_issues = len(analysis['vacancies_with_issues'])
    
    if total_issues == 0:
        report += "✅ <b>Проблем не виявлено!</b>\n"
        report += "Всі активні вакансії в нормальному стані.\n"
    else:
        report += f"⚠️ <b>Виявлено проблем: {total_issues}</b>\n\n"
        
        # Застійні вакансії
        if analysis['stagnant']:
            report += "⏸️ <b>Вакансії з застоєм:</b>\n"
            
            for vac in analysis['stagnant'][:5]:  # Перші 5
                report += f"  • <b>{vac['name']}</b> (ID: {vac['id']})\n"
                report += f"    {vac['issue']} ({vac['candidates_count']} кандидатів)\n"
                
                # Знаходимо відповідальних HR
                responsible = vac.get('responsible', [])
                if responsible:
                    hrs = config.get_hrs()
                    hr_names = []
                    hr_tags = []
                    
                    for resp_id in responsible:
                        for hr in hrs:
                            if hr.hurma_id == resp_id:
                                hr_names.append(hr.name)
                                if hr.telegram_id:
                                    hr_tags.append(f'<a href="tg://user?id={hr.telegram_id}">{hr.name}</a>')
                                elif hr.username:
                                    hr_tags.append(f'@{hr.username}')
                                break
                    
                    if hr_tags:
                        report += f"    Відповідальні: {', '.join(hr_tags)}\n"
                
                report += "\n"
            
            if len(analysis['stagnant']) > 5:
                report += f"  ... та ще {len(analysis['stagnant']) - 5} вакансій\n\n"
    
    report += "━━━━━━━━━━━━━━━━━━━━\n"
    report += "💡 <i>Детальніше: /vacancy_progress problems</i>"
    
    return report


async def _send_daily_vacancy_report(app: Application):
    """Надіслати щоденний звіт по вакансіях"""
    try:
        logger.info("Запуск щоденного звіту по вакансіях...")
        
        config = Config()
        
        # Отримуємо ID топіку звітів
        allowed_groups = config.get_allowed_group_ids()
        allowed_topics = config.get_allowed_topic_ids()
        
        if not allowed_groups or not allowed_topics:
            logger.warning("Не налаштовані групи або топіки для звітів")
            return
        
        chat_id = allowed_groups[0]
        topic_id = allowed_topics[0] if allowed_topics else None
        
        # Ініціалізуємо сервіси
        hurma = app.bot_data.get('hurma')
        binotel = app.bot_data.get('binotel')
        
        if not hurma or not binotel:
            logger.error("Сервіси Hurma/Binotel не ініціалізовані")
            return
        
        vacancy_analytics = VacancyAnalytics(hurma, binotel)
        
        # Аналізуємо вакансії
        analysis = await _analyze_all_vacancies(vacancy_analytics)
        
        # Форматуємо звіт
        report = await _format_daily_report(analysis, config)
        
        # Надсилаємо
        if topic_id:
            await app.bot.send_message(
                chat_id=chat_id,
                message_thread_id=topic_id,
                text=report,
                parse_mode=ParseMode.HTML
            )
        else:
            await app.bot.send_message(
                chat_id=chat_id,
                text=report,
                parse_mode=ParseMode.HTML
            )
        
        logger.info("✅ Щоденний звіт по вакансіях надіслано")
        
    except Exception as e:
        logger.error(f"❌ Помилка надсилання щоденного звіту: {e}", exc_info=True)


async def _run_scheduler(app: Application):
    """Запустити scheduler для щоденних звітів"""
    logger.info("🕐 Scheduler щоденних звітів по вакансіях запущено (10:00 щодня)")
    
    while True:
        try:
            now = datetime.now()
            target_time = time(10, 0)  # 10:00
            
            # Обчислюємо час до наступного запуску
            target_datetime = datetime.combine(now.date(), target_time)
            
            if now.time() > target_time:
                # Якщо вже пройшло 10:00 сьогодні - наступний запуск завтра
                from datetime import timedelta
                target_datetime += timedelta(days=1)
            
            wait_seconds = (target_datetime - now).total_seconds()
            
            logger.info(f"Наступний звіт о {target_datetime.strftime('%d.%m.%Y %H:%M')} (через {wait_seconds/3600:.1f} годин)")
            
            # Чекаємо до наступного запуску
            await asyncio.sleep(wait_seconds)
            
            # Перевіряємо чи робочий день (пн-пт)
            if target_datetime.weekday() < 5:  # 0-4 = пн-пт
                await _send_daily_vacancy_report(app)
            else:
                logger.info("Вихідний день - звіт не надсилається")
            
        except Exception as e:
            logger.error(f"Помилка в scheduler щоденних звітів: {e}", exc_info=True)
            # Чекаємо годину перед повтором
            await asyncio.sleep(3600)


async def setup_daily_vacancy_report_scheduler(app: Application):
    """
    Налаштувати scheduler для щоденних звітів по вакансіях
    
    Args:
        app: Telegram Application
        
    Returns:
        Task scheduler
    """
    try:
        # Запускаємо scheduler в фоні
        scheduler_task = asyncio.create_task(_run_scheduler(app))
        
        logger.info("✅ Scheduler щоденних звітів по вакансіях налаштовано")
        
        return scheduler_task
        
    except Exception as e:
        logger.error(f"❌ Помилка налаштування scheduler: {e}")
        raise
