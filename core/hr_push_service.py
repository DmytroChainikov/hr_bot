"""Модуль для роботи з push-повідомленнями для HR"""
from typing import Dict, List, Any, Optional
from datetime import datetime, date

from services.gemini_service import GeminiService
from core.vacancy_analytics import VacancyAnalytics
from core.logger_settings import create_logger

logger = create_logger(__name__)


class HRPushService:
    """Сервіс для генерації та відправки push-повідомлень HR"""
    
    def __init__(self, gemini_service: GeminiService, vacancy_analytics: VacancyAnalytics):
        """
        Ініціалізація сервісу push-повідомлень
        
        Args:
            gemini_service: Сервіс для AI генерації текстів
            vacancy_analytics: Сервіс аналітики вакансій
        """
        self.gemini = gemini_service
        self.vacancy_analytics = vacancy_analytics
    
    async def create_missing_report_push(self, hr_name: str) -> str:
        """
        Створити push про відсутній звіт
        
        Args:
            hr_name: Ім'я HR
            
        Returns:
            Текст повідомлення
        """
        details = {
            'date': date.today().strftime('%d.%m.%Y'),
            'time': datetime.now().strftime('%H:%M')
        }
        
        return await self.gemini.generate_motivational_push(
            hr_name=hr_name,
            issue_type='missing_report',
            details=details
        )
    
    async def create_missed_vacancies_push(
        self,
        hr_name: str,
        missed_vacancies: List[Dict[str, Any]]
    ) -> str:
        """
        Створити push про пропущені вакансії у звіті
        
        Args:
            hr_name: Ім'я HR
            missed_vacancies: Список пропущених вакансій
            
        Returns:
            Текст повідомлення
        """
        # Беремо тільки найважливіші (з кандидатами)
        critical = [v for v in missed_vacancies if v.get('candidates_count', 0) > 0]
        
        details = {
            'total_missed': len(missed_vacancies),
            'critical_missed': len(critical),
            'examples': [
                {
                    'name': v['name'],
                    'candidates': v.get('candidates_count', 0)
                }
                for v in critical[:3]  # Перші 3
            ]
        }
        
        return await self.gemini.generate_motivational_push(
            hr_name=hr_name,
            issue_type='missed_vacancies',
            details=details
        )
    
    async def create_low_calls_push(
        self,
        hr_name: str,
        actual_calls: int,
        expected_calls: int,
        active_vacancies_count: int
    ) -> str:
        """
        Створити push про малу кількість дзвінків
        
        Args:
            hr_name: Ім'я HR
            actual_calls: Фактична кількість дзвінків
            expected_calls: Очікувана кількість
            active_vacancies_count: Кількість активних вакансій
            
        Returns:
            Текст повідомлення
        """
        details = {
            'actual_calls': actual_calls,
            'expected_calls': expected_calls,
            'active_vacancies': active_vacancies_count,
            'difference': expected_calls - actual_calls
        }
        
        return await self.gemini.generate_motivational_push(
            hr_name=hr_name,
            issue_type='low_calls',
            details=details
        )
    
    async def create_stagnant_vacancies_push(
        self,
        hr_name: str,
        stagnant_vacancies: List[Dict[str, Any]]
    ) -> str:
        """
        Створити push про вакансії з застоєм
        
        Args:
            hr_name: Ім'я HR
            stagnant_vacancies: Список вакансій з застоєм
            
        Returns:
            Текст повідомлення
        """
        details = {
            'total_stagnant': len(stagnant_vacancies),
            'examples': [
                {
                    'name': v['name'],
                    'candidates_count': v.get('candidates_count', 0),
                    'warning': v.get('warning', 'Немає прогресу')
                }
                for v in stagnant_vacancies[:3]  # Перші 3
            ]
        }
        
        return await self.gemini.generate_motivational_push(
            hr_name=hr_name,
            issue_type='stagnant',
            details=details
        )
    
    async def create_inactive_topic_push(
        self,
        hr_name: str,
        vacancy_name: str,
        days_inactive: int
    ) -> str:
        """
        Створити push про неактивний топік вакансії
        
        Args:
            hr_name: Ім'я HR
            vacancy_name: Назва вакансії
            days_inactive: Кількість днів без активності
            
        Returns:
            Текст повідомлення
        """
        details = {
            'vacancy_name': vacancy_name,
            'days_inactive': days_inactive
        }
        
        return await self.gemini.generate_motivational_push(
            hr_name=hr_name,
            issue_type='inactive_topic',
            details=details
        )
    
    def format_push_with_tag(
        self,
        message: str,
        hr_telegram_id: Optional[int] = None,
        hr_username: Optional[str] = None
    ) -> str:
        """
        Форматувати повідомлення з тегом HR
        
        Args:
            message: Текст повідомлення
            hr_telegram_id: Telegram ID HR для тега
            hr_username: Username HR для тега
            
        Returns:
            Форматоване повідомлення з тегом
        """
        # Додаємо тег на початку
        if hr_telegram_id:
            tag = f'<a href="tg://user?id={hr_telegram_id}">HR</a>'
        elif hr_username:
            tag = f'@{hr_username}'
        else:
            return message
        
        return f"{tag} {message}"
    
    async def analyze_and_create_pushes(
        self,
        hr_name: str,
        hr_telegram_id: Optional[int] = None,
        hr_username: Optional[str] = None,
        check_report: bool = True,
        check_vacancies: bool = True,
        check_calls: bool = True,
        check_stagnant: bool = True
    ) -> List[str]:
        """
        Проаналізувати всі можливі проблеми та створити push-повідомлення
        
        Args:
            hr_name: Ім'я HR
            hr_telegram_id: Telegram ID для тега
            hr_username: Username для тега
            check_report: Перевіряти відсутність звіту
            check_vacancies: Перевіряти пропущені вакансії
            check_calls: Перевіряти кількість дзвінків
            check_stagnant: Перевіряти застійні вакансії
            
        Returns:
            Список згенерованих повідомлень
        """
        messages = []
        
        try:
            # TODO: Реалізувати перевірки на основі даних
            # Поки що заглушка для демонстрації
            
            logger.info(f"Аналіз для {hr_name}: report={check_report}, vacancies={check_vacancies}, calls={check_calls}, stagnant={check_stagnant}")
            
        except Exception as e:
            logger.error(f"Помилка аналізу для {hr_name}: {e}")
        
        return messages
