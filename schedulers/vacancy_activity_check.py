"""
Scheduler для моніторингу неактивних вакансій.

Щодня о 16:00 перевіряє вакансії без активності та надсилає
AI-генеровані пуш-повідомлення відповідальним HR.
"""
import asyncio
from datetime import datetime, time as dt_time
from telegram.ext import Application

from core.vacancy_activity_monitor import VacancyActivityMonitor
from core.hr_push_service import HRPushService
from services.gemini_service import GeminiService
from services.hurma_service import HurmaService
from services.binotel_service import BinotelService
from core.config import Config
from core.logger_settings import create_logger

logger = create_logger(__name__)


async def _check_inactive_vacancies(
    monitor: VacancyActivityMonitor,
    gemini: GeminiService,
    config: Config
) -> dict:
    """
    Перевіряє неактивні вакансії та вакансії без дзвінків.
    
    Returns:
        {
            'inactive': [...],  # вакансії без активності
            'no_calls': [...]   # вакансії без дзвінків
        }
    """
    logger.info("Перевіряємо неактивні вакансії та вакансії без дзвінків...")
    
    # Неактивні вакансії (3+ дні)
    inactive = monitor.get_inactive_vacancies(days_threshold=3)
    
    # Вакансії без дзвінків
    no_calls = monitor.get_vacancies_without_calls()
    
    logger.info(f"Знайдено: {len(inactive)} неактивних, {len(no_calls)} без дзвінків")
    
    return {
        'inactive': inactive,
        'no_calls': no_calls
    }


async def _send_vacancy_activity_push(
    application: Application,
    hr_id: str,
    inactive_vacancies: list,
    no_call_vacancies: list,
    push_service: HRPushService,
    config: Config
):
    """
    Надсилає AI-пуш про проблемні вакансії конкретному HR.
    """
    hr_info = config.HR_USERS.get(hr_id)
    
    if not hr_info:
        logger.warning(f"HR {hr_id} не знайдено в конфігурації")
        return
    
    hr_name = hr_info.get('name', 'HR')
    telegram_id = hr_info.get('telegram_id')
    
    if not telegram_id:
        logger.warning(f"У HR {hr_name} не вказано telegram_id")
        return
    
    # Якщо немає проблемних вакансій - не надсилаємо пуш
    if not inactive_vacancies and not no_call_vacancies:
        return
    
    # Формуємо повідомлення
    message = f'<a href="tg://user?id={telegram_id}">{hr_name}</a>, '
    
    issues = []
    
    if inactive_vacancies:
        vac_names = [f'"{v["vacancy_name"]}"' for v in inactive_vacancies[:3]]
        if len(inactive_vacancies) > 3:
            vac_names.append(f"та ще {len(inactive_vacancies) - 3}")
        issues.append(f"{len(inactive_vacancies)} вакансій без активності: {', '.join(vac_names)}")
    
    if no_call_vacancies:
        vac_names = [f'"{v["vacancy_name"]}"' for v in no_call_vacancies[:3]]
        if len(no_call_vacancies) > 3:
            vac_names.append(f"та ще {len(no_call_vacancies) - 3}")
        issues.append(f"{len(no_call_vacancies)} вакансій без дзвінків: {', '.join(vac_names)}")
    
    # Генеруємо AI-частину
    try:
        # Використовуємо тип inactive_topic бо він найближчий за змістом
        ai_message = await push_service.gemini.generate_motivational_push(
            hr_name=hr_name,
            issue_type='inactive_topic',  # Перевикористовуємо існуючий тип
            details={'issues': issues}
        )
        
        message += ai_message
        
        # Додаємо деталі
        message += "\n\n<b>Деталі:</b>\n"
        
        if inactive_vacancies:
            message += f"\n🔴 <b>Без активності 3+ дні:</b>\n"
            for vac in inactive_vacancies[:5]:
                days = vac['days_since_activity'] if vac['days_since_activity'] else "∞"
                message += f"  • {vac['vacancy_name']} ({days} днів)\n"
        
        if no_call_vacancies:
            message += f"\n📞 <b>Без дзвінків (є кандидати):</b>\n"
            for vac in no_call_vacancies[:5]:
                message += f"  • {vac['vacancy_name']} ({vac['candidates_count']} кандидатів)\n"
        
        # Відправляємо в топік звітів
        topic_id = config.DAILY_REPORTS_TOPIC_ID
        
        await application.bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            message_thread_id=topic_id,
            text=message,
            parse_mode='HTML'
        )
        
        logger.info(f"Надіслано пуш для {hr_name}: {len(inactive_vacancies)} неактивних, {len(no_call_vacancies)} без дзвінків")
        
    except Exception as e:
        logger.error(f"Помилка відправки пушу для {hr_name}: {e}")


async def _run_vacancy_activity_check(application: Application):
    """Виконує перевірку активності вакансій"""
    logger.info("Запуск перевірки активності вакансій")
    
    try:
        config = Config()
        
        # Ініціалізуємо сервіси
        hurma = HurmaService(
            client_id=config.HURMA_CLIENT_ID,
            client_secret=config.HURMA_CLIENT_SECRET,
            username=config.HURMA_USERNAME,
            password=config.HURMA_PASSWORD,
            company=config.HURMA_COMPANY
        )
        
        binotel = BinotelService(config.BINOTEL_KEY, config.BINOTEL_SECRET)
        monitor = VacancyActivityMonitor(hurma, binotel)
        
        gemini = GeminiService(api_key=config.GEMINI_API_KEY)
        push_service = HRPushService(gemini)
        
        # Перевіряємо проблемні вакансії
        results = await _check_inactive_vacancies(monitor, gemini, config)
        
        inactive = results['inactive']
        no_calls = results['no_calls']
        
        if not inactive and not no_calls:
            logger.info("Проблемних вакансій не знайдено")
            return
        
        # Групуємо по HR
        hr_vacancies = {}
        
        for vac in inactive:
            for hr_id in vac.get('assigned_recruiters', []):
                if hr_id not in hr_vacancies:
                    hr_vacancies[hr_id] = {'inactive': [], 'no_calls': []}
                hr_vacancies[hr_id]['inactive'].append(vac)
        
        for vac in no_calls:
            for hr_id in vac.get('assigned_recruiters', []):
                if hr_id not in hr_vacancies:
                    hr_vacancies[hr_id] = {'inactive': [], 'no_calls': []}
                hr_vacancies[hr_id]['no_calls'].append(vac)
        
        # Надсилаємо пуші кожному HR
        for hr_id, vacancies in hr_vacancies.items():
            await _send_vacancy_activity_push(
                application,
                hr_id,
                vacancies['inactive'],
                vacancies['no_calls'],
                push_service,
                config
            )
            await asyncio.sleep(1)
        
        logger.info("Перевірку активності вакансій завершено")
        
    except Exception as e:
        logger.error(f"Помилка в _run_vacancy_activity_check: {e}")


async def _scheduler_loop(application: Application):
    """Основний цикл scheduler"""
    logger.info("Scheduler перевірки активності вакансій запущено (16:00 щодня)")
    
    while True:
        try:
            now = datetime.now()
            target_time = dt_time(16, 0)  # 16:00
            
            # Обчислюємо час до наступного запуску
            target_datetime = datetime.combine(now.date(), target_time)
            if now.time() >= target_time:
                from datetime import timedelta
                target_datetime += timedelta(days=1)
            
            sleep_seconds = (target_datetime - now).total_seconds()
            
            logger.info(f"Наступна перевірка активності вакансій о {target_datetime.strftime('%Y-%m-%d %H:%M')}")
            
            await asyncio.sleep(sleep_seconds)
            
            # Запускаємо перевірку
            await _run_vacancy_activity_check(application)
            
        except Exception as e:
            logger.error(f"Помилка в scheduler loop: {e}")
            await asyncio.sleep(3600)


def setup_vacancy_activity_scheduler(application: Application):
    """
    Ініціалізує та запускає scheduler для моніторингу активності вакансій.
    
    Args:
        application: Telegram Application instance
    """
    try:
        scheduler_task = asyncio.create_task(_scheduler_loop(application))
        application.bot_data['vacancy_activity_scheduler'] = scheduler_task
        
        logger.info("Scheduler активності вакансій успішно налаштовано")
        
    except Exception as e:
        logger.error(f"Помилка налаштування scheduler активності вакансій: {e}")
