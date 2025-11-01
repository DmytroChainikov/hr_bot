"""Scheduler для перевірки звітів HR"""
import asyncio
from datetime import datetime, time, date, timedelta
from typing import TYPE_CHECKING, Dict, Set
import json
from pathlib import Path

from telegram import Bot
from telegram.ext import Application

from core.logger_settings import create_logger
from core.config import Config

if TYPE_CHECKING:
    from telegram.ext import Application

logger = create_logger(__name__)


class HRReportCheckScheduler:
    """Планувальник для перевірки чи HR надіслали звіти"""
    
    def __init__(self, application: Application):
        """
        Ініціалізація scheduler
        
        Args:
            application: Telegram Application
        """
        self.application = application
        self.is_running = False
        self._task = None
        self.reports_file = Path("hr_reports_log.json")
        self.hr_reports_today: Dict[str, bool] = {}  # {hr_name: has_reported}
        
    async def start(self):
        """Запустити scheduler"""
        if self.is_running:
            logger.warning("HR Report Check Scheduler вже запущено")
            return
            
        self.is_running = True
        self._task = asyncio.create_task(self._run_scheduler())
        logger.info("📋 HR Report Check Scheduler запущено")
        
    async def stop(self):
        """Зупинити scheduler"""
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("📋 HR Report Check Scheduler зупинено")
        
    async def _run_scheduler(self):
        """Основний цикл scheduler"""
        while self.is_running:
            try:
                # Визначаємо наступний час перевірки (19:00 - годину після робочого дня)
                now = datetime.now()
                next_check_time = self._get_next_check_time(now)
                
                # Рахуємо скільки часу чекати
                wait_seconds = (next_check_time - now).total_seconds()
                
                logger.info(
                    f"⏰ Наступна перевірка звітів HR заплановано на {next_check_time.strftime('%Y-%m-%d %H:%M:%S')} "
                    f"(через {wait_seconds / 3600:.1f} годин)"
                )
                
                # Чекаємо до наступного часу перевірки
                await asyncio.sleep(wait_seconds)
                
                # Перевіряємо звіти
                if self.is_running:
                    await self._check_hr_reports()
                    # Скидаємо лічильник на новий день
                    self._reset_daily_reports()
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Помилка в HR Report Check Scheduler: {e}")
                # Чекаємо 5 хвилин перед повторною спробою
                await asyncio.sleep(300)
                
    def _get_next_check_time(self, current_time: datetime) -> datetime:
        """
        Визначити наступний час перевірки звітів
        
        Args:
            current_time: Поточний час
            
        Returns:
            Наступний час перевірки
        """
        # Час перевірки звітів - 19:00 (після робочого дня)
        check_time = time(19, 0, 0)
        
        # Пробуємо сьогодні
        next_time = datetime.combine(current_time.date(), check_time)
        
        # Якщо час вже пройшов сьогодні, беремо завтра
        if next_time <= current_time:
            next_time = datetime.combine(
                current_time.date() + timedelta(days=1),
                check_time
            )
        
        # Перевіряємо чи це робочий день (Пн-Пт)
        # Якщо ні - переносимо на наступний робочий день
        while next_time.weekday() >= 5:  # 5 = Субота, 6 = Неділя
            next_time += timedelta(days=1)
            
        return next_time
        
    async def _check_hr_reports(self):
        """Перевірити чи всі HR надіслали звіти"""
        try:
            logger.info("🔍 Перевіряю звіти HR за сьогодні...")
            
            # Отримуємо список HR
            hrs = Config.get_hrs()
            
            if not hrs:
                logger.warning("❌ Список HR порожній")
                return
            
            # Отримуємо ID чату для відправки
            chat_id = self._get_report_chat_id()
            if not chat_id:
                logger.error("❌ ADMIN_CHAT_ID не налаштовано - не можу відправити нагадування")
                return
            
            # Завантажуємо записи про звіти за сьогодні
            today_reports = self._load_today_reports()
            
            # Перевіряємо кожного HR
            missing_reports = []
            bot: Bot = self.application.bot
            
            for hr in hrs:
                hr_name = hr.name
                has_reported = today_reports.get(hr_name, False)
                
                if not has_reported:
                    missing_reports.append(hr)
                    logger.warning(f"⚠️ {hr_name} не надіслав звіт за сьогодні")
            
            # Якщо є HR без звітів - надсилаємо нагадування
            if missing_reports:
                message = self._format_reminder_message(missing_reports)
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML'
                )
                logger.info(f"✅ Надіслано нагадування для {len(missing_reports)} HR")
            else:
                logger.info("✅ Всі HR надіслали звіти")
                # Можна надіслати позитивне повідомлення
                await bot.send_message(
                    chat_id=chat_id,
                    text="✅ <b>Відмінно!</b> Всі HR надіслали звіти за сьогодні 👏",
                    parse_mode='HTML'
                )
            
        except Exception as e:
            logger.error(f"❌ Помилка при перевірці звітів HR: {e}")
            
    def _format_reminder_message(self, missing_hrs: list) -> str:
        """
        Форматувати нагадування для HR
        
        Args:
            missing_hrs: Список HR, які не надіслали звіт
            
        Returns:
            Форматоване повідомлення
        """
        today = date.today().strftime('%d.%m.%Y')
        
        message = (
            f"⚠️ <b>Нагадування про звіт за {today}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        if len(missing_hrs) == 1:
            hr = missing_hrs[0]
            message += f"❓ <b>{hr.name}</b>, де звіт за день?\n\n"
            if hr.telegram_id:
                message += f"👤 "
                # Тегаємо HR
                message += f'<a href="tg://user?id={hr.telegram_id}">{hr.name}</a>\n\n'
        else:
            message += f"❓ Не отримано звітів від:\n\n"
            for hr in missing_hrs:
                if hr.telegram_id:
                    message += f"  • "
                    message += f'<a href="tg://user?id={hr.telegram_id}">{hr.name}</a>\n'
                else:
                    message += f"  • {hr.name}\n"
            message += "\n"
        
        message += (
            f"📝 <b>Будь ласка, надішліть звіт:</b>\n"
            f"  • Кількість дзвінків\n"
            f"  • Створені кандидати\n"
            f"  • Оновлені кандидати\n"
            f"  • Основні досягнення\n\n"
            f"💡 Звіт буде автоматично проаналізовано системою"
        )
        
        return message
        
    def _get_report_chat_id(self) -> str:
        """
        Отримати ID чату для відправки нагадувань
        
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
        
    def _reset_daily_reports(self):
        """Скинути лічильник звітів на новий день"""
        self.hr_reports_today = {}
        logger.info("Лічильник звітів скинуто на новий день")
        # Видаляємо файл зі звітами за вчора
        if self.reports_file.exists():
            try:
                self.reports_file.unlink()
                logger.info("🔄 Лічильник звітів скинуто на новий день")
            except Exception as e:
                logger.error(f"Помилка видалення файлу звітів: {e}")
                
    def _load_today_reports(self) -> Dict[str, bool]:
        """
        Завантажити інформацію про звіти за сьогодні з bot_data
        
        Returns:
            Словник {hr_name: has_reported}
        """
        try:
            # Отримуємо дані з bot_data
            if hasattr(self.application, 'bot_data') and 'hr_reports' in self.application.bot_data:
                today_key = date.today().strftime('%Y-%m-%d')
                today_reports_data = self.application.bot_data['hr_reports'].get(today_key, {})
                
                # Конвертуємо user_id: report_data в hr_name: True
                reported_hrs = {}
                for user_id, report_data in today_reports_data.items():
                    hr_name = report_data.get('hr_name')
                    if hr_name:
                        reported_hrs[hr_name] = True
                
                logger.info(f"Завантажено інформацію про {len(reported_hrs)} звітів за сьогодні")
                return reported_hrs
            
            return {}
            
        except Exception as e:
            logger.error(f"Помилка завантаження звітів: {e}")
            return {}
        
    def _save_today_reports(self):
        """Зберегти записи про звіти - тепер використовується bot_data"""
        # Не потрібно окреме збереження, дані вже в bot_data
        pass


async def setup_hr_report_check_scheduler(application: Application) -> HRReportCheckScheduler:
    """
    Налаштувати та запустити scheduler перевірки звітів HR
    
    Args:
        application: Telegram Application
        
    Returns:
        Екземпляр HRReportCheckScheduler
    """
    scheduler = HRReportCheckScheduler(application)
    await scheduler.start()
    return scheduler
