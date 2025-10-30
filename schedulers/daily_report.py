"""Scheduler для автоматичної відправки денних звітів"""
import asyncio
from datetime import datetime, time, date, timedelta
from typing import TYPE_CHECKING

from telegram import Bot
from telegram.ext import Application

from core.logger_settings import create_logger
from core.config import Config
from core.analytics import AnalyticsService

if TYPE_CHECKING:
    from telegram.ext import Application

logger = create_logger(__name__)


class DailyReportScheduler:
    """Планувальник для автоматичної відправки денних звітів"""
    
    def __init__(self, application: Application):
        """
        Ініціалізація scheduler
        
        Args:
            application: Telegram Application
        """
        self.application = application
        self.is_running = False
        self._task = None
        
    async def start(self):
        """Запустити scheduler"""
        if self.is_running:
            logger.warning("Scheduler вже запущено")
            return
            
        self.is_running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("📅 Daily Report Scheduler запущено")
        
    async def stop(self):
        """Зупинити scheduler"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("📅 Daily Report Scheduler зупинено")
        
    async def _run_scheduler(self):
        """Основний цикл scheduler"""
        while self.is_running:
            try:
                # Визначаємо наступний час відправки звіту
                now = datetime.now()
                next_report_time = self._get_next_report_time(now)
                
                # Рахуємо скільки часу чекати
                wait_seconds = (next_report_time - now).total_seconds()
                
                logger.info(
                    f"⏰ Наступний звіт заплановано на {next_report_time.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"(через {wait_seconds / 3600:.1f} годин)"
                )
                
                # Чекаємо до наступного часу відправки
                await asyncio.sleep(wait_seconds)
                
                # Надсилаємо звіт
                if self.is_running:
                    await self._send_daily_report()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Помилка в scheduler: {e}")
                # Чекаємо 5 хвилин перед повторною спробою
                await asyncio.sleep(300)
                
    def _get_next_report_time(self, current_time: datetime) -> datetime:
        """
        Визначити наступний час відправки звіту
        
        Args:
            current_time: Поточний час
            
        Returns:
            Наступний час відправки
        """
        # Час відправки звіту - 18:00
        report_time = time(18, 0, 0)
        
        # Пробуємо сьогодні
        next_time = datetime.combine(current_time.date(), report_time)
        
        # Якщо час вже пройшов сьогодні, беремо завтра
        if next_time <= current_time:
            next_time = datetime.combine(
                current_time.date() + timedelta(days=1),
                report_time
            )
        
        # Перевіряємо чи це робочий день (Пн-Пт)
        # Якщо ні - переносимо на наступний робочий день
        while next_time.weekday() >= 5:  # 5 = Субота, 6 = Неділя
            next_time += timedelta(days=1)
            
        return next_time
        
    async def _send_daily_report(self):
        """Надіслати денний звіт"""
        try:
            logger.info("📊 Починаю формування денного звіту...")
            
            # Отримуємо аналітику
            analytics: AnalyticsService = self.application.bot_data.get('analytics')
            if not analytics:
                logger.error("❌ AnalyticsService недоступний")
                return
            
            # Формуємо звіт за вчорашній день
            yesterday = date.today() - timedelta(days=1)
            reports = analytics.get_daily_hr_report(yesterday)
            
            # Отримуємо ID чату для відправки
            chat_id = self._get_report_chat_id()
            if not chat_id:
                logger.error("❌ ADMIN_CHAT_ID не налаштовано - не можу відправити звіт")
                return
            
            # Відправляємо звіти
            bot: Bot = self.application.bot
            
            for report in reports:
                await bot.send_message(
                    chat_id=chat_id,
                    text=report,
                    parse_mode='HTML'
                )
                # Невелика затримка між повідомленнями
                await asyncio.sleep(0.5)
            
            logger.info(f"✅ Денний звіт за {yesterday.strftime('%d.%m.%Y')} успішно відправлено")
            
        except Exception as e:
            logger.error(f"❌ Помилка при відправці денного звіту: {e}")
            
    def _get_report_chat_id(self) -> str:
        """
        Отримати ID чату для відправки звітів
        
        Returns:
            Chat ID або None
        """
        # Спочатку перевіряємо ADMIN_CHAT_ID
        admin_chat = Config.ADMIN_CHAT_ID
        if admin_chat:
            return admin_chat
            
        # Якщо не вказано, можна взяти перший з дозволених груп
        allowed_groups = Config.get_allowed_group_ids()
        if allowed_groups:
            return str(allowed_groups[0])
            
        return None
        
    async def send_test_report(self):
        """Надіслати тестовий звіт (для перевірки)"""
        logger.info("🧪 Відправка тестового звіту...")
        await self._send_daily_report()


async def setup_scheduler(application: Application) -> DailyReportScheduler:
    """
    Налаштувати та запустити scheduler
    
    Args:
        application: Telegram Application
        
    Returns:
        Екземпляр DailyReportScheduler
    """
    scheduler = DailyReportScheduler(application)
    await scheduler.start()
    return scheduler
