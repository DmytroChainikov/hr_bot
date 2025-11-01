"""
Відстеження загальної активності по вакансіях.

Аналізує всі типи активності: дзвінки, нові кандидати, рух по етапах.
Виявляє вакансії без активності для своєчасного реагування.
"""
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
import json
import os

from services.hurma_service import HurmaService
from services.binotel_service import BinotelService
from core.candidate_flow_tracker import CandidateFlowTracker
from core.logger_settings import create_logger

logger = create_logger(__name__)


class VacancyActivityMonitor:
    """Моніторинг активності по вакансіях"""

    def __init__(
        self, 
        hurma: HurmaService,
        binotel: BinotelService,
        storage_path: str = "vacancy_activity.json"
    ):
        """
        Ініціалізація монітора.
        
        Args:
            hurma: Сервіс Hurma API
            binotel: Сервіс Binotel API
            storage_path: Шлях до файлу для збереження даних
        """
        self.hurma = hurma
        self.binotel = binotel
        self.storage_path = storage_path
        self.flow_tracker = CandidateFlowTracker(hurma)
        self.data = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """Завантажує історичні дані про активність"""
        if not os.path.exists(self.storage_path):
            logger.info("Файл з даними активності не знайдено, створюємо новий")
            return {}
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Помилка завантаження даних активності: {e}")
            return {}

    def _save_data(self) -> None:
        """Зберігає дані про активність"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Помилка збереження даних активності: {e}")

    def get_vacancy_activity(self, vacancy_id: int, days: int = 7) -> Dict[str, Any]:
        """
        Отримує всю активність по вакансії за останні N днів.
        
        Returns:
            {
                'vacancy_id': 84,
                'vacancy_name': 'Python Developer',
                'period_days': 7,
                'calls_count': 15,
                'new_candidates': 3,
                'candidates_moved_forward': 2,
                'candidates_moved_backward': 0,
                'last_activity_date': '2025-10-31',
                'days_since_activity': 0,
                'is_active': True
            }
        """
        logger.info(f"Аналізуємо активність вакансії {vacancy_id} за {days} днів")
        
        # Отримуємо інфо про вакансію
        vacancies = self.hurma.get_job_openings(per_page=100)
        vacancy_name = None
        vacancy_data = None
        
        if vacancies and 'data' in vacancies:
            for vac in vacancies['data']:
                if vac['id'] == vacancy_id:
                    vacancy_name = vac.get('title', f'Вакансія #{vacancy_id}')
                    vacancy_data = vac
                    break
        
        if not vacancy_name:
            logger.warning(f"Вакансію {vacancy_id} не знайдено")
            vacancy_name = f"Вакансія #{vacancy_id}"
        
        # 1. Дзвінки за період
        calls_count = 0
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        try:
            # Отримуємо кандидатів вакансії для фільтрації дзвінків
            candidates_response = self.hurma.get_candidates(vacancy_id=vacancy_id, per_page=100)
            candidate_phones = set()
            
            if candidates_response and 'data' in candidates_response:
                for candidate in candidates_response['data']:
                    phones = candidate.get('phone_numbers', [])
                    for phone in phones:
                        # Очищаємо номер від форматування
                        clean_phone = ''.join(filter(str.isdigit, str(phone)))
                        if clean_phone:
                            candidate_phones.add(clean_phone)
            
            logger.info(f"Вакансія {vacancy_id}: {len(candidate_phones)} унікальних телефонів")
            
            # Отримуємо всі дзвінки за період ОДНИМ запитом
            if candidate_phones:
                try:
                    from datetime import time
                    # Конвертуємо в datetime для API
                    date_from = datetime.combine(start_date, time(0, 0, 0))
                    date_to = datetime.combine(end_date, time(23, 59, 59))
                    
                    # ОДИН запит замість багатьох!
                    all_calls = self.binotel.get_calls_from_to(date_from, date_to)
                    call_details = all_calls.get('callDetails', {})
                    
                    # Перевіряємо кожен дзвінок
                    for call_id, call in call_details.items():
                        call_number = call.get('externalNumber', '')
                        clean_call = ''.join(filter(str.isdigit, str(call_number)))
                        if clean_call in candidate_phones:
                            calls_count += 1
                    
                    logger.info(f"Вакансія {vacancy_id}: знайдено {calls_count} дзвінків")
                except Exception as e:
                    logger.error(f"Помилка отримання дзвінків: {e}")
                

        except Exception as e:
            logger.error(f"Помилка аналізу дзвінків для вакансії {vacancy_id}: {e}")
        
        # 2. Рух кандидатів
        moved_forward, moved_backward, new_candidates = self.flow_tracker.track_stage_changes(vacancy_id)
        
        # 3. Визначаємо дату останньої активності
        last_activity = None
        activities = []
        
        # Дзвінки
        if calls_count > 0:
            activities.append(('calls', end_date))  # Спрощено - беремо сьогодні якщо є дзвінки
        
        # Нові кандидати або рух
        if new_candidates or moved_forward or moved_backward:
            activities.append(('candidates', datetime.now().date()))
        
        # Оновлення вакансії
        if vacancy_data and vacancy_data.get('updated_at'):
            try:
                updated = vacancy_data['updated_at']
                if '+' in updated:
                    updated = updated.split('+')[0]
                update_date = datetime.fromisoformat(updated).date()
                activities.append(('vacancy_update', update_date))
            except Exception:
                pass
        
        # Знаходимо найсвіжішу активність
        if activities:
            activities.sort(key=lambda x: x[1], reverse=True)
            last_activity = activities[0][1]
        
        # Обчислюємо днів без активності
        days_since_activity = None
        is_active = False
        
        if last_activity:
            days_since_activity = (date.today() - last_activity).days
            is_active = days_since_activity < 3
        
        result = {
            'vacancy_id': vacancy_id,
            'vacancy_name': vacancy_name,
            'period_days': days,
            'calls_count': calls_count,
            'new_candidates': len(new_candidates),
            'candidates_moved_forward': len(moved_forward),
            'candidates_moved_backward': len(moved_backward),
            'last_activity_date': last_activity.isoformat() if last_activity else None,
            'days_since_activity': days_since_activity,
            'is_active': is_active
        }
        
        logger.info(
            f"Вакансія {vacancy_id}: дзвінків={calls_count}, "
            f"нових={len(new_candidates)}, активна={is_active}"
        )
        
        return result

    def get_inactive_vacancies(self, days_threshold: int = 3) -> List[Dict[str, Any]]:
        """
        Знаходить вакансії без активності більше N днів.
        
        Args:
            days_threshold: Поріг неактивності в днях
            
        Returns:
            Список вакансій з інформацією про активність
        """
        logger.info(f"Шукаємо неактивні вакансії (поріг: {days_threshold} днів)")
        
        # Отримуємо всі активні вакансії
        vacancies = self.hurma.get_job_openings(per_page=100)
        
        if not vacancies or 'data' not in vacancies:
            logger.warning("Не вдалося отримати список вакансій")
            return []
        
        active_vacancies = [v for v in vacancies['data'] if v.get('status') == 1]
        
        inactive = []
        
        for vacancy in active_vacancies:
            vacancy_id = vacancy['id']
            
            try:
                activity = self.get_vacancy_activity(vacancy_id, days=days_threshold + 1)
                
                # Якщо немає активності або активність була давно
                if (activity['days_since_activity'] is None or 
                    activity['days_since_activity'] >= days_threshold):
                    
                    # Додаємо інформацію про відповідального HR
                    assigned_recruiters = vacancy.get('assigned_recruiters', [])
                    
                    inactive.append({
                        **activity,
                        'assigned_recruiters': assigned_recruiters
                    })
                    
            except Exception as e:
                logger.error(f"Помилка аналізу вакансії {vacancy_id}: {e}")
                continue
        
        logger.info(f"Знайдено {len(inactive)} неактивних вакансій")
        return inactive

    def get_vacancies_without_calls(self) -> List[Dict[str, Any]]:
        """
        Знаходить вакансії з кандидатами, але без дзвінків за останні 7 днів.
        
        Returns:
            Список вакансій з деталями
        """
        logger.info("Шукаємо вакансії з кандидатами але без дзвінків")
        
        vacancies = self.hurma.get_job_openings(per_page=100)
        
        if not vacancies or 'data' not in vacancies:
            return []
        
        active_vacancies = [v for v in vacancies['data'] if v.get('status') == 1]
        
        without_calls = []
        
        for vacancy in active_vacancies:
            vacancy_id = vacancy['id']
            vacancy_name = vacancy.get('title', f'Вакансія #{vacancy_id}')
            
            try:
                # Отримуємо кандидатів
                candidates_response = self.hurma.get_candidates(vacancy_id=vacancy_id, per_page=100)
                
                if not candidates_response or 'data' not in candidates_response:
                    continue
                
                candidates_count = len(candidates_response['data'])
                
                # Якщо немає кандидатів - пропускаємо
                if candidates_count == 0:
                    continue
                
                # Перевіряємо активність
                activity = self.get_vacancy_activity(vacancy_id, days=7)
                
                # Якщо є кандидати, але немає дзвінків
                if activity['calls_count'] == 0:
                    without_calls.append({
                        'vacancy_id': vacancy_id,
                        'vacancy_name': vacancy_name,
                        'candidates_count': candidates_count,
                        'new_candidates_week': activity['new_candidates'],
                        'assigned_recruiters': vacancy.get('assigned_recruiters', [])
                    })
                    
            except Exception as e:
                logger.error(f"Помилка аналізу вакансії {vacancy_id}: {e}")
                continue
        
        logger.info(f"Знайдено {len(without_calls)} вакансій без дзвінків")
        return without_calls

    def get_activity_summary(self) -> Dict[str, Any]:
        """
        Повертає загальну статистику по активності всіх вакансій.
        
        Returns:
            {
                'total_active_vacancies': 10,
                'active_vacancies': 7,  # з активністю < 3 дні
                'inactive_vacancies': 3,  # без активності 3+ дні
                'vacancies_without_calls': 5,
                'total_calls_week': 150,
                'total_new_candidates_week': 25
            }
        """
        logger.info("Формуємо загальну статистику активності")
        
        vacancies = self.hurma.get_job_openings(per_page=100)
        
        if not vacancies or 'data' not in vacancies:
            return {
                'total_active_vacancies': 0,
                'active_vacancies': 0,
                'inactive_vacancies': 0,
                'vacancies_without_calls': 0,
                'total_calls_week': 0,
                'total_new_candidates_week': 0
            }
        
        active_vacancies = [v for v in vacancies['data'] if v.get('status') == 1]
        
        active_count = 0
        inactive_count = 0
        without_calls_count = 0
        total_calls = 0
        total_new_candidates = 0
        
        for vacancy in active_vacancies:
            vacancy_id = vacancy['id']
            
            try:
                activity = self.get_vacancy_activity(vacancy_id, days=7)
                
                # Рахуємо статистику
                if activity['is_active']:
                    active_count += 1
                else:
                    inactive_count += 1
                
                if activity['calls_count'] == 0:
                    # Перевіряємо чи є кандидати
                    candidates = self.hurma.get_candidates(vacancy_id=vacancy_id, per_page=1)
                    if candidates and 'data' in candidates and len(candidates['data']) > 0:
                        without_calls_count += 1
                
                total_calls += activity['calls_count']
                total_new_candidates += activity['new_candidates']
                
            except Exception as e:
                logger.warning(f"Помилка аналізу вакансії {vacancy_id}: {e}")
                continue
        
        return {
            'total_active_vacancies': len(active_vacancies),
            'active_vacancies': active_count,
            'inactive_vacancies': inactive_count,
            'vacancies_without_calls': without_calls_count,
            'total_calls_week': total_calls,
            'total_new_candidates_week': total_new_candidates
        }
