"""
Scheduler для моніторингу неактивних топіків вакансій.

Щодня о 16:00 перевіряє топіки без активності та надсилає
AI-генеровані пуш-повідомлення відповідальним HR.
"""
import asyncio
from datetime import datetime, time as dt_time
from telegram.ext import Application

from core.topic_activity_tracker import TopicActivityTracker
from core.hr_push_service import HRPushService
from services.gemini_service import GeminiService
from services.hurma_service import HurmaService
from core.config import Config
from core.logger_settings import create_logger

logger = create_logger(__name__)


async def _check_inactive_topics(
    tracker: TopicActivityTracker,
    hurma: HurmaService,
    gemini: GeminiService,
    config: Config
) -> dict:
    """
    Перевіряє неактивні топіки та формує список для пушів.
    
    Returns:
        Словник вигляду:
        {
            'hr_user_id': [
                {'vacancy_name': '...', 'days': 5, 'thread_id': 123},
                ...
            ]
        }
    """
    logger.info("Перевіряємо неактивні топіки...")
    
    # Отримуємо неактивні топіки (3+ дні)
    inactive_topics = tracker.get_inactive_topics(days_threshold=3)
    
    if not inactive_topics:
        logger.info("Неактивних топіків не знайдено")
        return {}
    
    logger.info(f"Знайдено {len(inactive_topics)} неактивних топіків")
    
    # Групуємо по відповідальним HR
    hr_topics = {}
    
    for topic in inactive_topics:
        vacancy_id = topic['vacancy_id']
        
        # Отримуємо інформацію про вакансію з Hurma
        try:
            vacancies = hurma.get_job_openings(per_page=100)
            vacancy_data = None
            
            if vacancies and 'data' in vacancies:
                for vac in vacancies['data']:
                    if vac['id'] == vacancy_id:
                        vacancy_data = vac
                        break
            
            if not vacancy_data:
                logger.warning(f"Вакансію {vacancy_id} не знайдено в Hurma")
                continue
            
            # Отримуємо список відповідальних рекрутерів
            assigned_recruiters = vacancy_data.get('assigned_recruiters', [])
            
            if not assigned_recruiters:
                logger.warning(f"У вакансії {vacancy_id} немає відповідальних рекрутерів")
                continue
            
            # Додаємо топік до кожного HR
            for hr_id in assigned_recruiters:
                if hr_id not in hr_topics:
                    hr_topics[hr_id] = []
                
                hr_topics[hr_id].append({
                    'vacancy_name': topic['vacancy_name'],
                    'vacancy_id': vacancy_id,
                    'days_inactive': topic['days_inactive'],
                    'thread_id': topic['thread_id']
                })
                
        except Exception as e:
            logger.error(f"Помилка обробки вакансії {vacancy_id}: {e}")
            continue
    
    logger.info(f"Згруповано топіки для {len(hr_topics)} HR")
    return hr_topics


async def _send_inactive_topic_push(
    application: Application,
    hr_id: str,
    topics: list,
    push_service: HRPushService,
    config: Config
):
    """
    Надсилає AI-пуш про неактивні топіки конкретному HR.
    """
    # Отримуємо інформацію про HR з конфігу
    hr_info = config.HR_USERS.get(hr_id)
    
    if not hr_info:
        logger.warning(f"HR {hr_id} не знайдено в конфігурації")
        return
    
    hr_name = hr_info.get('name', 'HR')
    telegram_id = hr_info.get('telegram_id')
    username = hr_info.get('username')
    
    if not telegram_id:
        logger.warning(f"У HR {hr_name} не вказано telegram_id")
        return
    
    # Формуємо деталі для AI
    details = {
        'inactive_topics': topics,
        'total_count': len(topics)
    }
    
    # Генеруємо AI-пуш
    try:
        push_message = await push_service.create_inactive_topic_push(
            hr_name=hr_name,
            topics=topics
        )
        
        # Відправляємо в особисті повідомлення або в топік звітів
        topic_id = config.DAILY_REPORTS_TOPIC_ID
        
        await application.bot.send_message(
            chat_id=config.TELEGRAM_CHAT_ID,
            message_thread_id=topic_id,
            text=push_message,
            parse_mode='HTML'
        )
        
        logger.info(f"Надіслано пуш про {len(topics)} неактивних топіків для {hr_name}")
        
    except Exception as e:
        logger.error(f"Помилка відправки пушу для {hr_name}: {e}")


async def _run_inactive_topics_check(application: Application):
    """Виконує перевірку неактивних топіків"""
    logger.info("Запуск перевірки неактивних топіків")
    
    try:
        config = Config()
        
        # Ініціалізуємо сервіси
        tracker: TopicActivityTracker = application.bot_data.get('topic_tracker')
        if not tracker:
            logger.error("TopicActivityTracker не ініціалізовано")
            return
        
        hurma = HurmaService(
            client_id=config.HURMA_CLIENT_ID,
            client_secret=config.HURMA_CLIENT_SECRET,
            username=config.HURMA_USERNAME,
            password=config.HURMA_PASSWORD,
            company=config.HURMA_COMPANY
        )
        
        gemini = GeminiService(api_key=config.GEMINI_API_KEY)
        push_service = HRPushService(gemini)
        
        # Перевіряємо неактивні топіки
        hr_topics = await _check_inactive_topics(tracker, hurma, gemini, config)
        
        if not hr_topics:
            logger.info("Немає неактивних топіків для пушів")
            return
        
        # Надсилаємо пуші кожному HR
        for hr_id, topics in hr_topics.items():
            await _send_inactive_topic_push(
                application, hr_id, topics, push_service, config
            )
            await asyncio.sleep(1)  # Невелика пауза між повідомленнями
        
        logger.info("Перевірку неактивних топіків завершено")
        
    except Exception as e:
        logger.error(f"Помилка в _run_inactive_topics_check: {e}")


async def _scheduler_loop(application: Application):
    """Основний цикл scheduler"""
    logger.info("Scheduler неактивних топіків запущено (16:00 щодня)")
    
    while True:
        try:
            now = datetime.now()
            target_time = dt_time(16, 0)  # 16:00
            
            # Обчислюємо час до наступного запуску
            target_datetime = datetime.combine(now.date(), target_time)
            if now.time() >= target_time:
                # Якщо вже минуло 16:00 сьогодні, плануємо на завтра
                from datetime import timedelta
                target_datetime += timedelta(days=1)
            
            sleep_seconds = (target_datetime - now).total_seconds()
            
            logger.info(f"Наступна перевірка неактивних топіків о {target_datetime.strftime('%Y-%m-%d %H:%M')}")
            
            await asyncio.sleep(sleep_seconds)
            
            # Запускаємо перевірку
            await _run_inactive_topics_check(application)
            
        except Exception as e:
            logger.error(f"Помилка в scheduler loop: {e}")
            await asyncio.sleep(3600)  # Чекаємо годину перед повторною спробою


def setup_inactive_topics_scheduler(application: Application):
    """
    Ініціалізує та запускає scheduler для моніторингу неактивних топіків.
    
    Args:
        application: Telegram Application instance
    """
    try:
        # Створюємо та зберігаємо task
        scheduler_task = asyncio.create_task(_scheduler_loop(application))
        application.bot_data['inactive_topics_scheduler'] = scheduler_task
        
        logger.info("Scheduler неактивних топіків успішно налаштовано")
        
    except Exception as e:
        logger.error(f"Помилка налаштування scheduler неактивних топіків: {e}")
