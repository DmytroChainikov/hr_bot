"""Модуль аналітики для HR бота"""
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json
import os

from core.logger_settings import create_logger
from core.config import Config
from services.hurma_service import HurmaService
from services.binotel_service import BinotelService

logger = create_logger(__name__)


class AnalyticsService:
    """Сервіс для формування аналітичних звітів"""
    
    def __init__(self, hurma_service: HurmaService, binotel_service: BinotelService):
        """
        Ініціалізація сервісу аналітики
        
        Args:
            hurma_service: Сервіс для роботи з Hurma API
            binotel_service: Сервіс для роботи з Binotel API
        """
        self.hurma = hurma_service
        self.binotel = binotel_service
        self._candidates_cache = None
        self._cache_date = None
        self._vacancies_cache = None
        self._vacancies_cache_date = None
        self._stage_translations = self._load_stage_translations()
    
    def _load_stage_translations(self) -> Dict[int, str]:
        """
        Завантажити переклади назв етапів з stage.json
        
        Returns:
            Словник {stage_id: ukrainian_name}
        """
        try:
            stage_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'stage.json')
            
            if os.path.exists(stage_file):
                with open(stage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    stages = data.get('data', [])
                    
                    translations = {}
                    for stage in stages:
                        stage_id = stage.get('id')
                        stage_name = stage.get('name')
                        if stage_id and stage_name:
                            translations[stage_id] = stage_name
                    
                    logger.info(f"Завантажено {len(translations)} перекладів етапів")
                    return translations
            else:
                logger.warning(f"Файл stage.json не знайдено: {stage_file}")
                return {}
        except Exception as e:
            logger.error(f"Помилка завантаження stage.json: {e}")
            return {}
    
    def _get_stage_name(self, stage_id: int, default_name: str = 'Не вказано') -> str:
        """
        Отримати українську назву етапу за ID
        
        Args:
            stage_id: ID етапу
            default_name: Назва за замовчуванням
            
        Returns:
            Українська назва етапу
        """
        return self._stage_translations.get(stage_id, default_name)
        
    def clear_cache(self):
        """Очистити кеш кандидатів та вакансій"""
        self._candidates_cache = None
        self._cache_date = None
        self._vacancies_cache = None
        self._vacancies_cache_date = None
        logger.info("Кеш кандидатів та вакансій очищено")
        
    def get_cache_info(self) -> Dict[str, Any]:
        """
        Отримати інформацію про кеш
        
        Returns:
            Dict з інформацією про кеш
        """
        info = {
            'candidates': {
                'cached': self._candidates_cache is not None,
                'count': len(self._candidates_cache) if self._candidates_cache else 0,
                'date': self._cache_date.strftime("%Y-%m-%d %H:%M:%S") if self._cache_date else None
            },
            'vacancies': {
                'cached': self._vacancies_cache is not None,
                'count': len(self._vacancies_cache) if self._vacancies_cache else 0,
                'date': self._vacancies_cache_date.strftime("%Y-%m-%d %H:%M:%S") if self._vacancies_cache_date else None
            }
        }
        return info
        
    def _get_all_candidates(self, force_reload: bool = False) -> List[Dict[str, Any]]:
        """
        Отримати всіх кандидатів з кешуванням
        
        Args:
            force_reload: Примусово перезавантажити дані
            
        Returns:
            Список кандидатів
        """
        if not force_reload and self._candidates_cache is not None:
            logger.info(f"Використовуємо кеш кандидатів ({len(self._candidates_cache)} записів)")
            return self._candidates_cache
        
        logger.info("Завантаження всіх кандидатів з Hurma...")
        all_candidates = []
        
        # Отримуємо список відстежуваних вакансій
        vacancy_ids = Config.get_vacancy_ids()
        
        # Якщо є конкретні вакансії - фільтруємо тільки по них
        if vacancy_ids:
            logger.info(f"Фільтрація по {len(vacancy_ids)} вакансіях: {vacancy_ids}")
            page = 1
            while True:
                response = self.hurma.get_candidates(
                    filter_job_openings=vacancy_ids,
                    page=page,
                    per_page=100
                )
                
                candidates = response.get('data', [])
                if not candidates:
                    break
                    
                all_candidates.extend(candidates)
                
                # Перевіряємо чи є ще сторінки
                pagination = response.get('meta', {}).get('pagination', {})
                if page >= pagination.get('total_pages', 1):
                    break
                    
                page += 1
        else:
            # Якщо список вакансій порожній - завантажуємо ВСІ кандидати
            logger.info("Список вакансій порожній - завантаження ВСІХ кандидатів")
            page = 1
            while True:
                response = self.hurma.get_candidates(page=page, per_page=100)
                
                candidates = response.get('data', [])
                if not candidates:
                    break
                    
                all_candidates.extend(candidates)
                
                # Перевіряємо чи є ще сторінки
                pagination = response.get('meta', {}).get('pagination', {})
                if page >= pagination.get('total_pages', 1):
                    break
                    
                page += 1
        
        self._candidates_cache = all_candidates
        self._cache_date = datetime.now()
        logger.info(f"Завантажено {len(all_candidates)} кандидатів")
        
        return all_candidates
    
    def _get_active_vacancies_with_stages(self, force_reload: bool = False) -> Dict[int, Dict[str, Any]]:
        """
        Отримати активні вакансії з їх етапами (з кешуванням)
        
        Args:
            force_reload: Примусово перезавантажити дані
        
        Returns:
            Словник {vacancy_id: {'info': vacancy_data, 'stages': [stages]}}
        """
        # Перевіряємо кеш
        if not force_reload and self._vacancies_cache is not None:
            logger.info(f"Використовуємо кеш вакансій ({len(self._vacancies_cache)} записів)")
            return self._vacancies_cache
        
        logger.info("Завантаження активних вакансій та їх етапів...")
        
        # Отримуємо активні вакансії (filter_status=1)
        vacancies_response = self.hurma.get_job_openings(filter_status=[1])
        vacancies_data = vacancies_response.get('data', [])
        print(vacancies_data)
        vacancy_ids = Config.get_vacancy_ids()
        
        vacancies_with_stages = {}
        
        for vacancy in vacancies_data:
            vacancy_id = vacancy.get('id')
            
            # Якщо є список відстежуваних вакансій - фільтруємо
            if vacancy_ids and vacancy_id not in vacancy_ids:
                continue
            
            try:
                # Отримуємо етапи для вакансії
                stages_response = self.hurma.get_job_stages(vacancy_id)
                stages = stages_response.get('data', [])
                
                vacancies_with_stages[vacancy_id] = {
                    'info': vacancy,
                    'stages': stages
                }
                
                logger.info(f"Вакансія '{vacancy.get('title')}' (ID: {vacancy_id}): {len(stages)} етапів")
                
            except Exception as e:
                logger.error(f"Помилка отримання етапів для вакансії {vacancy_id}: {e}")
                vacancies_with_stages[vacancy_id] = {
                    'info': vacancy,
                    'stages': []
                }
        
        # Зберігаємо в кеш
        self._vacancies_cache = vacancies_with_stages
        self._vacancies_cache_date = datetime.now()
        
        logger.info(f"Завантажено {len(vacancies_with_stages)} активних вакансій з етапами")
        return vacancies_with_stages
        
    def _filter_candidates_by_date(
        self, 
        candidates: List[Dict[str, Any]], 
        target_date: date,
        date_field: str = 'updated_at'
    ) -> List[Dict[str, Any]]:
        """
        Фільтрувати кандидатів за датою
        
        Args:
            candidates: Список кандидатів
            target_date: Дата для фільтрації
            date_field: Поле дати ('created_at' або 'updated_at')
            
        Returns:
            Відфільтрований список кандидатів
        """
        filtered = []
        
        for candidate in candidates:
            date_str = candidate.get(date_field)
            if not date_str:
                continue
                
            try:
                # Парсимо дату у форматі ISO 8601
                candidate_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                if candidate_date.date() == target_date:
                    filtered.append(candidate)
            except (ValueError, AttributeError) as e:
                logger.warning(f"Не вдалося розпарсити дату '{date_str}': {e}")
                continue
        
        return filtered
    
    def _get_vacancy_info_from_job_openings(
        self,
        candidate: Dict[str, Any],
        vacancy_id: Optional[int] = None,
        vacancies_with_stages: Optional[Dict[int, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Отримати інформацію про вакансію та етап з job_openings кандидата
        
        Args:
            candidate: Словник з даними кандидата
            vacancy_id: ID конкретної вакансії (якщо потрібна тільки одна)
            vacancies_with_stages: Словник вакансій з етапами
            
        Returns:
            Словник з інформацією: {'vacancy_id', 'vacancy_name', 'stage_id', 'stage_name'}
        """
        job_openings = candidate.get('job_openings', [])
        
        if not job_openings:
            return {
                'vacancy_id': None,
                'vacancy_name': 'Не вказано',
                'stage_id': None,
                'stage_name': 'Не вказано'
            }
        
        # Якщо вказано конкретну вакансію - шукаємо її
        if vacancy_id:
            for job_opening in job_openings:
                if job_opening.get('jobopening_id') == vacancy_id:
                    stage_id = job_opening.get('stage_id')
                    stage_name = self._get_stage_name(stage_id) if stage_id else 'Не вказано'
                    vacancy_name = f'Вакансія {vacancy_id}'
                    
                    # Знаходимо назву вакансії
                    if vacancies_with_stages and vacancy_id in vacancies_with_stages:
                        vacancy_data = vacancies_with_stages[vacancy_id]
                        vacancy_name = vacancy_data['info'].get('title', vacancy_name)
                    
                    return {
                        'vacancy_id': vacancy_id,
                        'vacancy_name': vacancy_name,
                        'stage_id': stage_id,
                        'stage_name': stage_name
                    }
        
        # Якщо не вказано вакансію - беремо першу з job_openings
        first_job = job_openings[0]
        vacancy_id = first_job.get('jobopening_id')
        stage_id = first_job.get('stage_id')
        stage_name = self._get_stage_name(stage_id) if stage_id else 'Не вказано'
        vacancy_name = f'Вакансія {vacancy_id}' if vacancy_id else 'Не вказано'
        
        # Знаходимо назву вакансії
        if vacancies_with_stages and vacancy_id in vacancies_with_stages:
            vacancy_data = vacancies_with_stages[vacancy_id]
            vacancy_name = vacancy_data['info'].get('title', vacancy_name)
        
        return {
            'vacancy_id': vacancy_id,
            'vacancy_name': vacancy_name,
            'stage_id': stage_id,
            'stage_name': stage_name
        }
        
    def get_daily_hr_report(self, report_date: date) -> List[str]:
        """
        Формування денного звіту по всіх HR з розподілом по вакансіях та етапах
        
        Args:
            report_date: Дата звіту
            
        Returns:
            Список повідомлень для відправки
        """
        try:
            # Завантажуємо активні вакансії з етапами
            vacancies_with_stages = self._get_active_vacancies_with_stages()
            
            # Завантажуємо кандидатів
            all_candidates = self._get_all_candidates()
            
            # Фільтруємо кандидатів створених за день
            created_candidates = self._filter_candidates_by_date(
                all_candidates, 
                report_date,
                'created_at'
            )
            
            # Фільтруємо кандидатів оновлених за день
            updated_candidates = self._filter_candidates_by_date(
                all_candidates, 
                report_date,
                'updated_at'
            )
            
            # Отримуємо дзвінки за день
            calls_data = self._get_calls_for_date(report_date)
            
            # Групуємо по HR
            hrs = Config.get_hrs()
            created_hr_stats = self._group_candidates_by_hr(created_candidates, hrs)
            updated_hr_stats = self._group_candidates_by_hr(updated_candidates, hrs)
            
            # Формуємо звіти
            reports = []
            
            # Загальний заголовок
            header = (
                f"📊 <b>Звіт за {report_date.strftime('%d.%m.%Y')}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
            )
            
            # Загальна статистика
            total_created = len(created_candidates)
            total_updated = len(updated_candidates)
            total_calls = calls_data['total_calls']
            
            summary = (
                f"{header}"
                f"📞 <b>Дзвінки:</b> {total_calls}\n"
                f"✨ <b>Створено кандидатів:</b> {total_created}\n"
                f"� <b>Оновлено кандидатів:</b> {total_updated}\n\n"
            )
            
            # Якщо немає даних
            if total_created == 0 and total_updated == 0 and total_calls == 0:
                reports.append(summary + "ℹ️ За цей день немає активності")
                return reports
            
            # Додаємо дані по кожному HR
            if created_hr_stats or updated_hr_stats:
                summary += "<b>📋 По рекрутерах:</b>\n"
                all_hr_names = set(created_hr_stats.keys()) | set(updated_hr_stats.keys())
                
                for hr_name in sorted(all_hr_names):
                    created_count = created_hr_stats.get(hr_name, {}).get('count', 0)
                    updated_count = updated_hr_stats.get(hr_name, {}).get('count', 0)
                    hr_calls = calls_data['hr_calls'].get(hr_name, 0)
                    
                    summary += (
                        f"  • {hr_name}: "
                        f"✨{created_count} створено, "
                        f"🔄{updated_count} оновлено, "
                        f"📞{hr_calls} дзвінків\n"
                    )
            
            reports.append(summary)
            
            # Детальна інформація по створених кандидатах
            if created_candidates:
                created_details = self._format_candidates_by_vacancy_and_stage(
                    created_candidates, 
                    vacancies_with_stages,
                    report_date,
                    "Створені кандидати"
                )
                if created_details:
                    reports.append(created_details)
            
            # Детальна інформація по оновлених кандидатах
            if updated_candidates:
                updated_details = self._format_candidates_by_vacancy_and_stage(
                    updated_candidates, 
                    vacancies_with_stages,
                    report_date,
                    "Оновлені кандидати"
                )
                if updated_details:
                    reports.append(updated_details)
            
            return reports
            
        except Exception as e:
            logger.error(f"Помилка формування денного звіту: {e}")
            raise
            
    def get_hr_personal_report(self, hr_name: str, report_date: date) -> str:
        """
        Формування персонального звіту для конкретного HR з розподілом по вакансіях
        
        Args:
            hr_name: Ім'я HR
            report_date: Дата звіту
            
        Returns:
            Текст звіту
        """
        try:
            # Знаходимо HR
            hr = Config.get_hr_by_name(hr_name)
            if not hr:
                return f"❌ HR з ім'ям '{hr_name}' не знайдено"
            
            # Завантажуємо вакансії з етапами
            vacancies_with_stages = self._get_active_vacancies_with_stages()
            
            # Завантажуємо кандидатів
            all_candidates = self._get_all_candidates()
            
            # Фільтруємо створених за дату та HR
            created_daily = self._filter_candidates_by_date(
                all_candidates,
                report_date,
                'created_at'
            )
            hr_created = [
                c for c in created_daily 
                if c.get('responsible_recruiter', {}).get('id') == hr.hurma_id
            ]
            
            # Фільтруємо оновлених за дату та HR
            updated_daily = self._filter_candidates_by_date(
                all_candidates,
                report_date,
                'updated_at'
            )
            hr_updated = [
                c for c in updated_daily 
                if c.get('responsible_recruiter', {}).get('id') == hr.hurma_id
            ]
            
            # Отримуємо дзвінки
            calls_data = self._get_calls_for_date(report_date)
            hr_calls = calls_data['hr_calls'].get(hr_name, 0)
            
            # Формуємо звіт
            report = (
                f"👤 <b>Персональний звіт: {hr_name}</b>\n"
                f"📅 Дата: {report_date.strftime('%d.%m.%Y')}\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📞 <b>Дзвінки:</b> {hr_calls}\n"
                f"✨ <b>Створено кандидатів:</b> {len(hr_created)}\n"
                f"� <b>Оновлено кандидатів:</b> {len(hr_updated)}\n\n"
            )
            
            # Детальна інформація по створених
            if hr_created:
                report += "<b>✨ Створені кандидати:</b>\n\n"
                vacancy_groups = defaultdict(list)
                
                for candidate in hr_created:
                    vacancy_info = self._get_vacancy_info_from_job_openings(
                        candidate, 
                        vacancies_with_stages=vacancies_with_stages
                    )
                    vacancy_name = vacancy_info['vacancy_name']
                    vacancy_groups[vacancy_name].append({
                        'candidate': candidate,
                        'stage_name': vacancy_info['stage_name']
                    })
                
                for vacancy_name, items in sorted(vacancy_groups.items()):
                    report += f"  <b>🎯 {vacancy_name}</b> ({len(items)})\n"
                    for item in items[:5]:
                        candidate = item['candidate']
                        name = candidate.get('name') or candidate.get('specialization') or 'Без імені'
                        stage = item['stage_name']
                        report += f"    • {name} - {stage}\n"
                    if len(items) > 5:
                        report += f"    ... та ще {len(items) - 5}\n"
                    report += "\n"
            
            # Детальна інформація по оновлених
            if hr_updated:
                report += "<b>🔄 Оновлені кандидати:</b>\n\n"
                vacancy_groups = defaultdict(list)
                
                for candidate in hr_updated:
                    vacancy_info = self._get_vacancy_info_from_job_openings(
                        candidate, 
                        vacancies_with_stages=vacancies_with_stages
                    )
                    vacancy_name = vacancy_info['vacancy_name']
                    vacancy_groups[vacancy_name].append({
                        'candidate': candidate,
                        'stage_name': vacancy_info['stage_name']
                    })
                
                for vacancy_name, items in sorted(vacancy_groups.items()):
                    report += f"  <b>🎯 {vacancy_name}</b> ({len(items)})\n"
                    for item in items[:5]:
                        candidate = item['candidate']
                        name = candidate.get('name') or candidate.get('specialization') or 'Без імені'
                        stage = item['stage_name']
                        report += f"    • {name} - {stage}\n"
                    if len(items) > 5:
                        report += f"    ... та ще {len(items) - 5}\n"
                    report += "\n"
            
            if not hr_created and not hr_updated:
                report += "ℹ️ За цей день кандидати не створювались та не оновлювались"
            
            return report
            
        except Exception as e:
            logger.error(f"Помилка формування персонального звіту для {hr_name}: {e}")
            raise
    
    def get_candidates_created_today(self, target_date: date = None) -> List[Dict[str, Any]]:
        """
        Отримати кандидатів створених за вказаний день
        
        Args:
            target_date: Дата для пошуку (за замовчуванням - сьогодні)
            
        Returns:
            Список кандидатів
        """
        if target_date is None:
            target_date = date.today()
            
        all_candidates = self._get_all_candidates()
        return self._filter_candidates_by_date(all_candidates, target_date, 'created_at')
    
    def get_candidates_updated_today(self, target_date: date = None) -> List[Dict[str, Any]]:
        """
        Отримати кандидатів оновлених за вказаний день
        
        Args:
            target_date: Дата для пошуку (за замовчуванням - сьогодні)
            
        Returns:
            Список кандидатів
        """
        if target_date is None:
            target_date = date.today()
            
        all_candidates = self._get_all_candidates()
        return self._filter_candidates_by_date(all_candidates, target_date, 'updated_at')
    
    def get_vacancy_stats(self, vacancy_id: int) -> str:
        """
        Отримати детальну статистику по конкретній вакансії
        
        Args:
            vacancy_id: ID вакансії
            
        Returns:
            Форматований текст зі статистикою
        """
        try:
            # Отримуємо вакансії з етапами
            vacancies_with_stages = self._get_active_vacancies_with_stages()
            
            vacancy_data = vacancies_with_stages.get(vacancy_id)
            if not vacancy_data:
                return f"❌ Вакансія з ID {vacancy_id} не знайдена або неактивна"
            
            vacancy_info = vacancy_data['info']
            vacancy_name = vacancy_info.get('title', f'Вакансія {vacancy_id}')
            stages = vacancy_data.get('stages', [])
            
            # Переконуємось що stages - це список
            if not isinstance(stages, list):
                logger.warning(f"Stages для вакансії {vacancy_id} не є списком: {type(stages)}")
                stages = []
            
            # Отримуємо всіх кандидатів
            all_candidates = self._get_all_candidates()
            
            # Фільтруємо кандидатів по вакансії через job_openings
            vacancy_candidates = []
            for candidate in all_candidates:
                job_openings = candidate.get('job_openings', [])
                for job_opening in job_openings:
                    if job_opening.get('jobopening_id') == vacancy_id:
                        vacancy_candidates.append(candidate)
                        break
            
            # Групуємо по етапах
            stage_stats = defaultdict(lambda: {'count': 0, 'candidates': []})
            
            for candidate in vacancy_candidates:
                vacancy_info_data = self._get_vacancy_info_from_job_openings(
                    candidate,
                    vacancy_id=vacancy_id,
                    vacancies_with_stages=vacancies_with_stages
                )
                stage_name = vacancy_info_data['stage_name']
                stage_stats[stage_name]['count'] += 1
                stage_stats[stage_name]['candidates'].append(candidate)
            
            # Групуємо по HR
            hr_stats = defaultdict(int)
            for candidate in vacancy_candidates:
                recruiter = candidate.get('responsible_recruiter', {})
                recruiter_name = recruiter.get('name', 'Не вказано')
                hr_stats[recruiter_name] += 1
            
            # Формуємо звіт
            report = (
                f"📋 <b>{vacancy_name}</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"👥 <b>Всього кандидатів:</b> {len(vacancy_candidates)}\n"
                f"📊 <b>Етапів:</b> {len(stages)}\n\n"
            )
            
            # Статистика по етапах
            if stage_stats:
                report += "<b>📌 Розподіл по етапах:</b>\n\n"
                
                # Сортуємо етапи по кількості кандидатів (від більшого до меншого)
                sorted_stages = sorted(stage_stats.items(), key=lambda x: x[1]['count'], reverse=True)
                
                for stage_name, stats in sorted_stages:
                    count = stats['count']
                    percentage = (count / len(vacancy_candidates) * 100) if vacancy_candidates else 0
                    
                    # Візуальна шкала
                    bar_length = int(percentage / 5)  # Максимум 20 символів
                    bar = '█' * bar_length + '░' * (20 - bar_length)
                    
                    report += f"  <b>{stage_name}</b>\n"
                    report += f"  {bar} {count} ({percentage:.1f}%)\n\n"
                
            # Статистика по HR
            if hr_stats:
                report += "<b>👤 Розподіл по HR:</b>\n"
                sorted_hr = sorted(hr_stats.items(), key=lambda x: x[1], reverse=True)
                
                for hr_name, count in sorted_hr:
                    percentage = (count / len(vacancy_candidates) * 100) if vacancy_candidates else 0
                    report += f"  • {hr_name}: {count} ({percentage:.1f}%)\n"
                
                report += "\n"
            
            # Топ-5 останніх оновлених кандидатів
            recent_candidates = sorted(
                vacancy_candidates,
                key=lambda x: x.get('updated_at', ''),
                reverse=True
            )[:5]
            
            if recent_candidates:
                report += "<b>🕐 Останні оновлення:</b>\n"
                for candidate in recent_candidates:
                    name = candidate.get('name') or candidate.get('specialization') or 'Без імені'
                    
                    # Отримуємо етап через job_openings
                    vacancy_info = self._get_vacancy_info_from_job_openings(
                        candidate,
                        vacancies_with_stages=vacancies_with_stages
                    )
                    stage = vacancy_info['stage_name']
                    updated = candidate.get('updated_at', '')
                    
                    # Парсимо дату
                    try:
                        updated_dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                        updated_str = updated_dt.strftime('%d.%m.%Y %H:%M')
                    except:
                        updated_str = 'Невідомо'
                    
                    report += f"  • {name} - {stage}\n    ({updated_str})\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Помилка отримання статистики вакансії {vacancy_id}: {e}")
            return f"❌ Помилка: {str(e)}"
    
    def get_all_vacancies_stats(self) -> str:
        """
        Отримати загальну статистику по всіх вакансіях
        
        Returns:
            Форматований текст зі статистикою
        """
        try:
            # Отримуємо вакансії з етапами
            vacancies_with_stages = self._get_active_vacancies_with_stages()
            
            if not vacancies_with_stages:
                return "⚠️ Немає активних вакансій"
            
            # Отримуємо всіх кандидатів
            all_candidates = self._get_all_candidates()
            
            # Збираємо статистику по кожній вакансії
            vacancy_stats = []
            total_candidates = 0
            
            for vacancy_id, vacancy_data in vacancies_with_stages.items():
                vacancy_info = vacancy_data['info']
                vacancy_name = vacancy_info.get('title', f'Вакансія {vacancy_id}')
                
                # Кандидати по вакансії через job_openings
                vacancy_candidates = []
                for candidate in all_candidates:
                    job_openings = candidate.get('job_openings', [])
                    for job_opening in job_openings:
                        if job_opening.get('jobopening_id') == vacancy_id:
                            vacancy_candidates.append(candidate)
                            break
                
                count = len(vacancy_candidates)
                total_candidates += count
                
                vacancy_stats.append({
                    'name': vacancy_name,
                    'count': count,
                    'id': vacancy_id
                })
            
            # Сортуємо по кількості кандидатів
            vacancy_stats.sort(key=lambda x: x['count'], reverse=True)
            
            # Формуємо звіт
            report = (
                f"📊 <b>Загальна статистика по вакансіях</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📋 <b>Активних вакансій:</b> {len(vacancies_with_stages)}\n"
                f"👥 <b>Всього кандидатів:</b> {total_candidates}\n\n"
            )
            
            if vacancy_stats:
                report += "<b>🎯 Топ вакансій по кількості кандидатів:</b>\n\n"
                
                for i, vacancy in enumerate(vacancy_stats[:10], 1):
                    name = vacancy['name']
                    count = vacancy['count']
                    percentage = (count / total_candidates * 100) if total_candidates > 0 else 0
                    
                    # Скорочуємо назву якщо занадто довга
                    display_name = name[:45] + '...' if len(name) > 45 else name
                    
                    # Візуальна шкала
                    bar_length = int(percentage / 5)  # Максимум 20 символів
                    bar = '█' * bar_length + '░' * (20 - bar_length)
                    
                    report += f"{i}. <b>{display_name}</b>\n"
                    report += f"   {bar} {count} ({percentage:.1f}%)\n\n"
                
                if len(vacancy_stats) > 10:
                    report += f"... та ще {len(vacancy_stats) - 10} вакансій\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Помилка отримання загальної статистики: {e}")
            return f"❌ Помилка: {str(e)}"
            
    def _get_calls_for_date(self, target_date: date) -> Dict[str, Any]:
        """
        Отримати дзвінки за дату
        
        Args:
            target_date: Дата
            
        Returns:
            Словник з даними про дзвінки
        """
        try:
            # Отримуємо дзвінки з Binotel
            calls = self.binotel.get_calls_for_date(target_date)
            
            # Рахуємо по HR
            hr_calls = defaultdict(int)
            hrs = Config.get_hrs()
            
            for call in calls:
                internal_number = call.get('internalNumber', '')
                
                # Знаходимо HR по внутрішньому номеру
                for hr in hrs:
                    if hr.binotel_internal == internal_number:
                        hr_calls[hr.name] += 1
                        break
            
            return {
                'total_calls': len(calls),
                'hr_calls': dict(hr_calls)
            }
        except Exception as e:
            logger.error(f"Помилка отримання дзвінків: {e}")
            return {'total_calls': 0, 'hr_calls': {}}
            
    def _group_candidates_by_hr(
        self, 
        candidates: List[Dict[str, Any]], 
        hrs: List[Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Групування кандидатів по HR
        
        Args:
            candidates: Список кандидатів
            hrs: Список HR
            
        Returns:
            Словник з даними по кожному HR
        """
        hr_stats = defaultdict(lambda: {'count': 0, 'candidates': []})
        
        for candidate in candidates:
            recruiter = candidate.get('responsible_recruiter', {})
            recruiter_id = recruiter.get('id')
            
            # Знаходимо HR
            for hr in hrs:
                if hr.hurma_id == recruiter_id:
                    hr_stats[hr.name]['count'] += 1
                    hr_stats[hr.name]['candidates'].append(candidate)
                    break
        
        return dict(hr_stats)
        
    def _format_candidates_details(
        self, 
        candidates: List[Dict[str, Any]], 
        report_date: date,
        vacancies_with_stages: Optional[Dict[int, Dict[str, Any]]] = None
    ) -> str:
        """
        Форматування детальної інформації про кандидатів
        
        Args:
            candidates: Список кандидатів
            report_date: Дата звіту
            vacancies_with_stages: Словник вакансій з етапами
            
        Returns:
            Форматований текст
        """
        if not candidates:
            return ""
        
        # Групуємо по вакансіях
        vacancy_groups = defaultdict(list)
        
        for candidate in candidates:
            vacancy_info = self._get_vacancy_info_from_job_openings(
                candidate,
                vacancies_with_stages=vacancies_with_stages
            )
            vacancy_name = vacancy_info['vacancy_name']
            vacancy_groups[vacancy_name].append(candidate)
        
        # Формуємо звіт
        report = (
            f"📋 <b>Детальна інформація по кандидатах</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        for vacancy_name, vacancy_candidates in sorted(vacancy_groups.items()):
            report += f"<b>🎯 {vacancy_name}</b> ({len(vacancy_candidates)})\n"
            
            # Показуємо перших 10 кандидатів по вакансії
            for candidate in vacancy_candidates[:10]:
                name = candidate.get('name') or candidate.get('specialization') or 'Без імені'
                
                # Отримуємо етап з job_openings
                vacancy_info = self._get_vacancy_info_from_job_openings(
                    candidate,
                    vacancies_with_stages=vacancies_with_stages
                )
                stage = vacancy_info['stage_name']
                recruiter = candidate.get('responsible_recruiter', {}).get('name', 'Не вказано')
                
                report += f"  • {name}\n"
                report += f"    Етап: {stage}\n"
                report += f"    HR: {recruiter}\n"
            
            if len(vacancy_candidates) > 10:
                report += f"  ... та ще {len(vacancy_candidates) - 10} кандидатів\n"
            
            report += "\n"
        
        return report
    
    def _format_candidates_by_vacancy_and_stage(
        self, 
        candidates: List[Dict[str, Any]], 
        vacancies_with_stages: Dict[int, Dict[str, Any]],
        report_date: date,
        title: str
    ) -> str:
        """
        Форматування детальної інформації про кандидатів з розподілом по вакансіях та етапах
        
        Args:
            candidates: Список кандидатів
            vacancies_with_stages: Словник вакансій з етапами
            report_date: Дата звіту
            title: Заголовок секції
            
        Returns:
            Форматований текст
        """
        if not candidates:
            return ""
        
        # Групуємо по вакансіях
        vacancy_groups = defaultdict(lambda: defaultdict(list))
        
        for candidate in candidates:
            # Отримуємо інформацію з job_openings
            vacancy_info = self._get_vacancy_info_from_job_openings(
                candidate,
                vacancies_with_stages=vacancies_with_stages
            )
            
            vacancy_id = vacancy_info['vacancy_id']
            vacancy_name = vacancy_info['vacancy_name']
            stage_name = vacancy_info['stage_name']
            
            # Використовуємо назву вакансії як ключ (щоб уникнути проблем з None)
            vacancy_key = f"{vacancy_id}_{vacancy_name}" if vacancy_id else vacancy_name
            vacancy_groups[vacancy_key][stage_name].append({
                'candidate': candidate,
                'vacancy_id': vacancy_id,
                'vacancy_name': vacancy_name
            })
        
        # Формуємо звіт
        report = (
            f"📋 <b>{title}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
        )
        
        for vacancy_key, stage_groups in vacancy_groups.items():
            # Отримуємо назву вакансії з першого елемента
            first_item = next(iter(next(iter(stage_groups.values()))))
            vacancy_name = first_item['vacancy_name']
            
            total_for_vacancy = sum(len(items) for items in stage_groups.values())
            
            report += f"<b>🎯 {vacancy_name}</b> (Всього: {total_for_vacancy})\n\n"
            
            # Групуємо по етапах
            for stage_name, stage_items in sorted(stage_groups.items()):
                report += f"  <b>📌 {stage_name}</b> ({len(stage_items)})\n"
                
                # Показуємо перших 5 кандидатів на етапі
                for item in stage_items[:5]:
                    candidate = item['candidate']
                    name = candidate.get('name') or candidate.get('specialization') or 'Без імені'
                    recruiter = candidate.get('responsible_recruiter', {}).get('name', 'Не вказано')
                    
                    report += f"    • {name} (HR: {recruiter})\n"
                
                if len(stage_items) > 5:
                    report += f"    ... та ще {len(stage_items) - 5}\n"
                
                report += "\n"
            
            report += "─────────────────────\n\n"
        
        return report
    
    def get_vacancy_statistics(
        self, 
        vacancy_id: int, 
        report_date: Optional[date] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Отримати повну статистику по вакансії за весь час + за конкретний день
        
        Args:
            vacancy_id: ID вакансії
            report_date: Дата для денного звіту (якщо None - використовується сьогодні)
            
        Returns:
            Словник зі статистикою або None якщо вакансію не знайдено
        """
        try:
            if report_date is None:
                report_date = date.today()
            
            # Завантажуємо вакансії з кешем
            vacancies = self._get_active_vacancies_with_stages()
            
            vacancy_data = vacancies.get(vacancy_id)
            if not vacancy_data:
                logger.warning(f"Вакансію {vacancy_id} не знайдено серед активних")
                return None
            print(vacancy_data)
            vacancy_info = vacancy_data['info']
            vacancy_name = vacancy_info.get('title', f'Вакансія {vacancy_id}')
            stages = vacancy_data.get('stages', [])
            
            # Переконуємось що stages - це список
            if not isinstance(stages, list):
                logger.warning(f"Stages для вакансії {vacancy_id} не є списком: {type(stages)}")
                stages = []
            
            # Завантажуємо всіх кандидатів для цієї вакансії
            all_candidates = []
            page = 1
            
            while True:
                response = self.hurma.get_candidates(
                    vacancy_id=vacancy_id,
                    page=page,
                    per_page=100
                )
                
                candidates = response.get('data', [])
                if not candidates:
                    break
                    
                # Фільтруємо кандидатів - перевіряємо job_openings
                for candidate in candidates:
                    job_openings = candidate.get('job_openings', [])
                    
                    # Перевіряємо чи є ця вакансія в job_openings кандидата
                    for job_opening in job_openings:
                        if job_opening.get('jobopening_id') == vacancy_id:
                            all_candidates.append(candidate)
                            break  # Кандидат вже доданий, переходимо до наступного
                
                pagination = response.get('meta', {}).get('pagination', {})
                if page >= pagination.get('total_pages', 1):
                    break
                    
                page += 1
            
            logger.info(f"Вакансія {vacancy_id} ({vacancy_name}): отримано {len(all_candidates)} кандидатів")
            
            # Розділяємо кандидатів на групи
            created_today = []  # Створені сьогодні
            updated_today = []  # Оновлені сьогодні (але не створені)
            
            for candidate in all_candidates:
                created_at = candidate.get('created_at')
                updated_at = candidate.get('updated_at')
                
                # Перевіряємо чи створений сьогодні
                if created_at:
                    try:
                        created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                        if created_date.date() == report_date:
                            created_today.append(candidate)
                            continue  # Якщо створений сьогодні - не рахуємо як оновлений
                    except (ValueError, AttributeError):
                        pass
                
                # Перевіряємо чи оновлений сьогодні
                if updated_at:
                    try:
                        updated_date = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        if updated_date.date() == report_date:
                            updated_today.append(candidate)
                    except (ValueError, AttributeError):
                        pass
            
            # Статистика за весь час (по етапах)
            all_time_stage_stats = defaultdict(lambda: {'count': 0, 'candidates': []})
            
            # Переконуємось що stages - це список
            if not isinstance(stages, list):
                logger.warning(f"Stages для вакансії {vacancy_id} не є списком: {type(stages)}")
                stages = []
            
            for candidate in all_candidates:
                # Знаходимо stage_id для цієї вакансії з job_openings
                stage_id = None
                stage_name = 'Не вказано'
                
                job_openings = candidate.get('job_openings', [])
                for job_opening in job_openings:
                    if job_opening.get('jobopening_id') == vacancy_id:
                        stage_id = job_opening.get('stage_id')
                        break
                
                # Знаходимо назву етапу за stage_id
                if stage_id and stages:
                    for stage in stages:
                        if isinstance(stage, dict) and stage.get('id') == stage_id:
                            stage_name = stage.get('name', 'Не вказано')
                            break
                
                all_time_stage_stats[stage_name]['count'] += 1
                all_time_stage_stats[stage_name]['stage_id'] = stage_id
                all_time_stage_stats[stage_name]['candidates'].append({
                    'name': candidate.get('name') or candidate.get('specialization') or 'Без імені',
                    'id': candidate.get('id'),
                    'recruiter': candidate.get('responsible_recruiter', {}).get('name', 'Не вказано'),
                    'created_at': candidate.get('created_at'),
                    'updated_at': candidate.get('updated_at')
                })
            
            # Статистика за день (створені)
            daily_created_stage_stats = defaultdict(lambda: {'count': 0, 'candidates': []})
            
            for candidate in created_today:
                # Знаходимо stage_id для цієї вакансії з job_openings
                stage_id = None
                stage_name = 'Не вказано'
                
                job_openings = candidate.get('job_openings', [])
                for job_opening in job_openings:
                    if job_opening.get('jobopening_id') == vacancy_id:
                        stage_id = job_opening.get('stage_id')
                        break
                
                # Знаходимо назву етапу за stage_id
                if stage_id and stages:
                    for stage in stages:
                        if isinstance(stage, dict) and stage.get('id') == stage_id:
                            stage_name = stage.get('name', 'Не вказано')
                            break
                
                daily_created_stage_stats[stage_name]['count'] += 1
                daily_created_stage_stats[stage_name]['candidates'].append({
                    'name': candidate.get('name') or candidate.get('specialization') or 'Без імені',
                    'recruiter': candidate.get('responsible_recruiter', {}).get('name', 'Не вказано'),
                    'created_at': candidate.get('created_at')
                })
            
            # Статистика за день (оновлені)
            daily_updated_stage_stats = defaultdict(lambda: {'count': 0, 'candidates': []})
            
            for candidate in updated_today:
                # Знаходимо stage_id для цієї вакансії з job_openings
                stage_id = None
                stage_name = 'Не вказано'
                
                job_openings = candidate.get('job_openings', [])
                for job_opening in job_openings:
                    if job_opening.get('jobopening_id') == vacancy_id:
                        stage_id = job_opening.get('stage_id')
                        break
                
                # Знаходимо назву етапу за stage_id
                if stage_id and stages:
                    for stage in stages:
                        if isinstance(stage, dict) and stage.get('id') == stage_id:
                            stage_name = stage.get('name', 'Не вказано')
                            break
                
                daily_updated_stage_stats[stage_name]['count'] += 1
                daily_updated_stage_stats[stage_name]['candidates'].append({
                    'name': candidate.get('name') or candidate.get('specialization') or 'Без імені',
                    'recruiter': candidate.get('responsible_recruiter', {}).get('name', 'Не вказано'),
                    'updated_at': candidate.get('updated_at')
                })
            
            logger.info(
                f"Вакансія {vacancy_id}: всього {len(all_candidates)}, "
                f"створено за {report_date}: {len(created_today)}, "
                f"оновлено за {report_date}: {len(updated_today)}"
            )
            
            return {
                'vacancy_id': vacancy_id,
                'vacancy_name': vacancy_name,
                'vacancy_info': vacancy_info,
                'report_date': report_date,
                
                # За весь час
                'all_time': {
                    'total_candidates': len(all_candidates),
                    'stages': dict(all_time_stage_stats)
                },
                
                # За день
                'daily': {
                    'created_count': len(created_today),
                    'updated_count': len(updated_today),
                    'created_stages': dict(daily_created_stage_stats),
                    'updated_stages': dict(daily_updated_stage_stats)
                },
                
                'all_stages': stages  # Всі можливі етапи з get_job_stages
            }
            
        except Exception as e:
            logger.error(f"Помилка отримання статистики для вакансії {vacancy_id}: {e}")
            raise
    
    def get_all_active_vacancies(self) -> List[Dict[str, Any]]:
        """
        Отримати список всіх активних вакансій
        
        Returns:
            Список вакансій з базовою інформацією
        """
        vacancies = self._get_active_vacancies_with_stages()
        
        result = []
        for vacancy_id, data in vacancies.items():
            info = data['info']
            result.append({
                'id': vacancy_id,
                'name': info.get('title', f'Вакансія {vacancy_id}'),
                'status': info.get('status'),
                'created_at': info.get('created_at')
            })
        
        return sorted(result, key=lambda x: x['name'])
