"""Аналітика по вакансіям та їх прогресу"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, date
from collections import defaultdict

from services.hurma_service import HurmaService
from services.binotel_service import BinotelService
from core.logger_settings import create_logger

logger = create_logger(__name__)


class VacancyAnalytics:
    """Сервіс для аналізу прогресу по вакансіям"""
    
    # Статуси вакансій в Hurma
    STATUS_ACTIVE = 1
    STATUS_CLOSED = 2
    STATUS_ARCHIVED = 3
    
    def __init__(self, hurma_service: HurmaService, binotel_service: BinotelService):
        """
        Ініціалізація сервісу аналітики вакансій
        
        Args:
            hurma_service: Сервіс для роботи з Hurma API
            binotel_service: Сервіс для роботи з Binotel API
        """
        self.hurma = hurma_service
        self.binotel = binotel_service
        
        # Кеш для оптимізації
        self._vacancies_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = timedelta(minutes=10)
    
    def get_active_vacancies(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Отримати всі активні вакансії
        
        Args:
            force_refresh: Примусово оновити кеш
            
        Returns:
            Список активних вакансій з повною інформацією
        """
        # Перевіряємо кеш
        if (
            not force_refresh
            and self._cache_timestamp
            and datetime.now() - self._cache_timestamp < self._cache_ttl
            and self._vacancies_cache
        ):
            logger.info(f"Використовуємо кешовані вакансії ({len(self._vacancies_cache)} шт.)")
            return list(self._vacancies_cache.values())
        
        logger.info("Завантажуємо активні вакансії з Hurma...")
        
        try:
            # Отримуємо тільки активні вакансії (status=1)
            response = self.hurma.get_job_openings(
                filter_status=[self.STATUS_ACTIVE],
                page=1,
                per_page=100
            )
            
            vacancies = response.get('data', [])
            logger.info(f"Завантажено {len(vacancies)} активних вакансій")
            
            # Оновлюємо кеш
            self._vacancies_cache = {v['id']: v for v in vacancies}
            self._cache_timestamp = datetime.now()
            
            return vacancies
            
        except Exception as e:
            logger.error(f"Помилка при завантаженні вакансій: {e}")
            # Повертаємо кеш якщо є
            if self._vacancies_cache:
                logger.warning("Використовуємо застарілий кеш через помилку")
                return list(self._vacancies_cache.values())
            return []
    
    def get_vacancy_candidates_count(self, vacancy_id: int) -> Dict[str, int]:
        """
        Отримати кількість кандидатів по етапах для вакансії
        
        Args:
            vacancy_id: ID вакансії
            
        Returns:
            Словник: {stage_name: count}
        """
        try:
            # Отримуємо етапи вакансії
            stages_response = self.hurma.get_job_stages(vacancy_id)
            
            # Перевіряємо тип відповіді
            if isinstance(stages_response, str):
                logger.error(f"Отримано str замість dict для вакансії {vacancy_id}")
                logger.debug(f"Відповідь: {stages_response[:200]}")
                # Спробуємо розпарсити як JSON
                try:
                    import json
                    stages_response = json.loads(stages_response)
                except:
                    logger.error(f"Не вдалося розпарсити як JSON")
                    return {'__total__': 0}
            
            if not isinstance(stages_response, dict):
                logger.error(f"Неочікуваний тип відповіді для вакансії {vacancy_id}: {type(stages_response)}")
                return {'__total__': 0}
            
            stages = stages_response.get('data', [])
            
            result = {}
            total = 0
            
            for stage in stages:
                if not isinstance(stage, dict):
                    logger.warning(f"Stage не є dict: {type(stage)}")
                    continue
                    
                stage_name = stage.get('name', 'Unknown')
                candidates_count = stage.get('candidates_count', 0)
                result[stage_name] = candidates_count
                total += candidates_count
                total += candidates_count
            
            result['__total__'] = total
            logger.info(f"Вакансія ID {vacancy_id}: {total} кандидатів у воронці")
            
            return result
            
        except Exception as e:
            logger.error(f"Помилка при отриманні кандидатів для вакансії {vacancy_id}: {e}")
            return {'__total__': 0}
    
    def analyze_vacancy_activity(
        self,
        vacancy_id: int,
        days_back: int = 3
    ) -> Dict[str, Any]:
        """
        Аналіз активності по вакансії за останні N днів
        
        Args:
            vacancy_id: ID вакансії
            days_back: Кількість днів для аналізу
            
        Returns:
            Словник з аналітикою:
            - candidates_count: кількість кандидатів по етапах
            - has_activity: чи є активність
            - days_without_activity: скільки днів без змін
            - calls_count: кількість дзвінків за період
        """
        result = {
            'vacancy_id': vacancy_id,
            'candidates_count': {},
            'has_activity': False,
            'days_without_activity': 0,
            'calls_count': 0
        }
        
        # Отримуємо кількість кандидатів
        result['candidates_count'] = self.get_vacancy_candidates_count(vacancy_id)
        
        # TODO: Додати аналіз змін у воронці (потрібен History API від Hurma)
        # Поки що просто перевіряємо чи є кандидати
        total_candidates = result['candidates_count'].get('__total__', 0)
        result['has_activity'] = total_candidates > 0
        
        return result
    
    def find_stagnant_vacancies(
        self,
        min_candidates: int = 1,
        days_threshold: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Знайти вакансії з застоєм (є кандидати але немає руху)
        
        Args:
            min_candidates: Мінімальна кількість кандидатів для перевірки
            days_threshold: Скільки днів без активності вважається застоєм
            
        Returns:
            Список вакансій з проблемами
        """
        logger.info(f"Шукаємо вакансії з застоєм (мін. {min_candidates} кандидатів, {days_threshold}+ днів без руху)")
        
        active_vacancies = self.get_active_vacancies()
        stagnant = []
        
        for vacancy in active_vacancies:
            vacancy_id = vacancy['id']
            vacancy_name = vacancy.get('name', 'Unknown')
            
            # Отримуємо кількість кандидатів
            candidates = self.get_vacancy_candidates_count(vacancy_id)
            total = candidates.get('__total__', 0)
            
            if total >= min_candidates:
                # TODO: Перевірка реального руху через History API
                # Поки що просто додаємо всі з кандидатами як потенційно проблемні
                stagnant.append({
                    'id': vacancy_id,
                    'name': vacancy_name,
                    'candidates_count': total,
                    'candidates_by_stage': {k: v for k, v in candidates.items() if k != '__total__'},
                    'warning': 'Є кандидати - перевірте активність'
                })
        
        logger.info(f"Знайдено {len(stagnant)} вакансій з кандидатами")
        return stagnant
    
    def compare_vacancies_with_calls(
        self,
        hr_id: int,
        target_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Порівняти активні вакансії з дзвінками HR
        
        Args:
            hr_id: ID рекрутера в Binotel
            target_date: Дата для аналізу (YYYY-MM-DD), за замовчуванням - сьогодні
            
        Returns:
            Аналітика: які вакансії мають дзвінки, які ні
        """
        if not target_date:
            target_date = date.today().strftime('%Y-%m-%d')
        
        logger.info(f"Порівнюємо вакансії з дзвінками HR {hr_id} за {target_date}")
        
        # Отримуємо активні вакансії
        active_vacancies = self.get_active_vacancies()
        
        # Отримуємо дзвінки HR за день
        try:
            from datetime import datetime
            date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
            calls = self.binotel.get_calls_for_date(date_obj)
            hr_calls = [call for call in calls if call.get('internalNumber') == str(hr_id)]
        except Exception as e:
            logger.error(f"Помилка при отриманні дзвінків: {e}")
            hr_calls = []
        
        result = {
            'total_active_vacancies': len(active_vacancies),
            'total_calls': len(hr_calls),
            'vacancies_with_calls': [],
            'vacancies_without_calls': [],
            'vacancies_with_candidates_no_calls': []  # Критично!
        }
        
        # Для кожної вакансії перевіряємо чи були дзвінки
        # TODO: Покращити логіку - зараз просто перевіряємо чи є дзвінки взагалі
        # Потрібно зв'язати дзвінки з конкретними вакансіями через кандидатів
        
        for vacancy in active_vacancies:
            vacancy_id = vacancy['id']
            vacancy_name = vacancy.get('name', 'Unknown')
            
            # Отримуємо кількість кандидатів
            candidates = self.get_vacancy_candidates_count(vacancy_id)
            total_candidates = candidates.get('__total__', 0)
            
            vacancy_info = {
                'id': vacancy_id,
                'name': vacancy_name,
                'candidates_count': total_candidates,
                'responsible': vacancy.get('responsible', [])
            }
            
            # Якщо є кандидати але немає дзвінків - це проблема
            if total_candidates > 0 and len(hr_calls) == 0:
                result['vacancies_with_candidates_no_calls'].append(vacancy_info)
            elif total_candidates == 0:
                result['vacancies_without_calls'].append(vacancy_info)
        
        logger.info(
            f"Результат: {len(result['vacancies_with_candidates_no_calls'])} "
            f"вакансій з кандидатами без дзвінків"
        )
        
        return result
    
    def get_vacancy_summary(self, vacancy_id: int) -> str:
        """
        Отримати текстовий summary по вакансії
        
        Args:
            vacancy_id: ID вакансії
            
        Returns:
            Форматований текст з інформацією
        """
        try:
            # Знаходимо вакансію в кеші
            vacancy = self._vacancies_cache.get(vacancy_id)
            if not vacancy:
                # Якщо немає в кеші - оновлюємо
                self.get_active_vacancies(force_refresh=True)
                vacancy = self._vacancies_cache.get(vacancy_id)
            
            if not vacancy:
                return f"❌ Вакансія ID {vacancy_id} не знайдена"
            
            name = vacancy.get('name', 'Unknown')
            candidates = self.get_vacancy_candidates_count(vacancy_id)
            total = candidates.get('__total__', 0)
            
            summary = f"📋 **{name}** (ID: {vacancy_id})\n"
            summary += f"👥 Кандидатів у воронці: {total}\n"
            
            if total > 0:
                summary += "\nПо етапах:\n"
                for stage, count in candidates.items():
                    if stage != '__total__' and count > 0:
                        summary += f"  • {stage}: {count}\n"
            
            return summary
            
        except Exception as e:
            logger.error(f"Помилка при генерації summary для вакансії {vacancy_id}: {e}")
            return f"❌ Помилка: {e}"
    
    def check_missed_vacancies_in_report(
        self,
        hr_report: str,
        hr_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Перевірити чи згадує HR всі активні вакансії у звіті
        
        Args:
            hr_report: Текст звіту від HR
            hr_name: Ім'я HR (опціонально)
            
        Returns:
            Словник з аналізом:
            - total_active: загальна кількість активних вакансій
            - mentioned_vacancies: список згаданих вакансій
            - missed_vacancies: список пропущених вакансій
            - critical_missed: вакансії з кандидатами які не згадані
        """
        result = {
            'total_active': 0,
            'mentioned_vacancies': [],
            'missed_vacancies': [],
            'critical_missed': []  # Вакансії з кандидатами але не згадані
        }
        
        # Отримуємо всі активні вакансії
        active_vacancies = self.get_active_vacancies()
        result['total_active'] = len(active_vacancies)
        
        if not active_vacancies:
            return result
        
        # Нормалізуємо звіт для пошуку
        report_lower = hr_report.lower()
        
        for vacancy in active_vacancies:
            vacancy_id = vacancy['id']
            vacancy_name = vacancy.get('name', 'Unknown')
            
            # Отримуємо кількість кандидатів
            candidates = self.get_vacancy_candidates_count(vacancy_id)
            total_candidates = candidates.get('__total__', 0)
            
            # Перевіряємо чи згадується вакансія у звіті
            # Шукаємо по назві або ID
            is_mentioned = False
            
            # Варіанти пошуку
            search_variants = [
                vacancy_name.lower(),
                str(vacancy_id),
                f"#{vacancy_id}",
                f"id {vacancy_id}",
                f"вакансія {vacancy_id}"
            ]
            
            for variant in search_variants:
                if variant in report_lower:
                    is_mentioned = True
                    break
            
            vacancy_info = {
                'id': vacancy_id,
                'name': vacancy_name,
                'candidates_count': total_candidates,
                'responsible': vacancy.get('responsible', [])
            }
            
            if is_mentioned:
                result['mentioned_vacancies'].append(vacancy_info)
            else:
                result['missed_vacancies'].append(vacancy_info)
                
                # Якщо є кандидати але не згадана - це критично
                if total_candidates > 0:
                    result['critical_missed'].append(vacancy_info)
        
        logger.info(
            f"Перевірка звіту: {len(result['mentioned_vacancies'])}/{result['total_active']} "
            f"вакансій згадано, {len(result['critical_missed'])} критичних пропусків"
        )
        
        return result
