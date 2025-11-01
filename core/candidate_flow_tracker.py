"""
Трекер руху кандидатів по воронці вакансій.

Оскільки Hurma API не надає прямого доступу до історії змін етапів,
цей модуль використовує альтернативний підхід на базі updated_at та stage_id.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
import json
import os

from services.hurma_service import HurmaService
from core.logger_settings import create_logger

logger = create_logger(__name__)


class CandidateFlowTracker:
    """Відстежує рух кандидатів по етапах вакансій"""

    def __init__(self, hurma_service: HurmaService, storage_path: str = "candidate_snapshots"):
        """
        Ініціалізація трекера.
        
        Args:
            hurma_service: Сервіс Hurma API
            storage_path: Шлях до директорії для збереження snapshot'ів
        """
        self.hurma = hurma_service
        self.storage_path = storage_path
        
        # Створюємо директорію якщо не існує
        if not os.path.exists(storage_path):
            os.makedirs(storage_path)
            logger.info(f"Створено директорію для snapshot'ів: {storage_path}")

    def _get_snapshot_filename(self, vacancy_id: int) -> str:
        """Повертає ім'я файлу для snapshot конкретної вакансії"""
        return os.path.join(self.storage_path, f"vacancy_{vacancy_id}_snapshot.json")

    def _load_snapshot(self, vacancy_id: int) -> Optional[Dict]:
        """
        Завантажує збережений snapshot вакансії.
        
        Returns:
            Словник з даними або None якщо snapshot не існує
        """
        filename = self._get_snapshot_filename(vacancy_id)
        if not os.path.exists(filename):
            return None
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Помилка завантаження snapshot для вакансії {vacancy_id}: {e}")
            return None

    def _save_snapshot(self, vacancy_id: int, snapshot: Dict) -> None:
        """Зберігає snapshot вакансії"""
        filename = self._get_snapshot_filename(vacancy_id)
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(snapshot, f, ensure_ascii=False, indent=2)
            logger.debug(f"Збережено snapshot для вакансії {vacancy_id}")
        except Exception as e:
            logger.error(f"Помилка збереження snapshot для вакансії {vacancy_id}: {e}")

    def get_current_vacancy_state(self, vacancy_id: int) -> Dict[str, Any]:
        """
        Отримує поточний стан вакансії з кандидатами.
        
        Returns:
            Словник вигляду:
            {
                'timestamp': '2025-10-31T14:00:00',
                'vacancy_id': 84,
                'candidates': [
                    {
                        'id': 'abc123',
                        'name': 'Іван Петров',
                        'stage_id': 1,
                        'updated_at': '2025-10-30T12:00:00'
                    },
                    ...
                ]
            }
        """
        logger.info(f"Отримуємо поточний стан вакансії {vacancy_id}")
        
        try:
            # Отримуємо всіх кандидатів цієї вакансії
            response = self.hurma.get_candidates(
                vacancy_id=vacancy_id,
                per_page=100  # Збільшуємо ліміт
            )
            
            candidates = []
            if response and 'data' in response:
                # Використовуємо дані безпосередньо з короткої версії
                # Немає потреби робити додаткові запити get_candidate_by_id
                for candidate_data in response['data']:
                    # Знаходимо stage_id для цієї вакансії
                    stage_id = None
                    for job_opening in candidate_data.get('job_openings', []):
                        if job_opening.get('jobopening_id') == vacancy_id:
                            stage_id = job_opening.get('stage_id')
                            break
                    
                    if stage_id is not None:
                        candidates.append({
                            'id': candidate_data['id'],
                            'name': candidate_data.get('name', 'Без імені'),
                            'stage_id': stage_id,
                            'updated_at': candidate_data.get('updated_at', '')
                        })
            
            state = {
                'timestamp': datetime.now().isoformat(),
                'vacancy_id': vacancy_id,
                'candidates': candidates
            }
            
            logger.info(f"Вакансія {vacancy_id}: знайдено {len(candidates)} кандидатів")
            return state
            
        except Exception as e:
            logger.error(f"Помилка отримання стану вакансії {vacancy_id}: {e}")
            return {
                'timestamp': datetime.now().isoformat(),
                'vacancy_id': vacancy_id,
                'candidates': []
            }

    def detect_stagnant_candidates(
        self, 
        vacancy_id: int, 
        days_threshold: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Виявляє кандидатів, які не рухаються більше N днів.
        
        Args:
            vacancy_id: ID вакансії
            days_threshold: Кількість днів неактивності
            
        Returns:
            Список кандидатів у форматі:
            [
                {
                    'id': 'abc123',
                    'name': 'Іван Петров',
                    'stage_id': 1,
                    'days_stagnant': 5,
                    'last_update': '2025-10-26T12:00:00'
                },
                ...
            ]
        """
        logger.info(f"Шукаємо застійних кандидатів для вакансії {vacancy_id} (поріг: {days_threshold} днів)")
        
        current_state = self.get_current_vacancy_state(vacancy_id)
        stagnant = []
        
        now = datetime.now()
        threshold = timedelta(days=days_threshold)
        
        for candidate in current_state['candidates']:
            try:
                # Парсимо дату оновлення
                updated_at_str = candidate['updated_at']
                if not updated_at_str:
                    continue
                
                # Видаляємо timezone якщо є
                if '+' in updated_at_str:
                    updated_at_str = updated_at_str.split('+')[0]
                elif 'Z' in updated_at_str:
                    updated_at_str = updated_at_str.replace('Z', '')
                
                updated_at = datetime.fromisoformat(updated_at_str)
                days_stagnant = (now - updated_at).days
                
                if days_stagnant >= days_threshold:
                    stagnant.append({
                        'id': candidate['id'],
                        'name': candidate['name'],
                        'stage_id': candidate['stage_id'],
                        'days_stagnant': days_stagnant,
                        'last_update': candidate['updated_at']
                    })
                    
            except Exception as e:
                logger.warning(f"Помилка обробки кандидата {candidate['id']}: {e}")
                continue
        
        logger.info(f"Знайдено {len(stagnant)} застійних кандидатів для вакансії {vacancy_id}")
        return stagnant

    def track_stage_changes(self, vacancy_id: int) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Відстежує зміни етапів порівнюючи з попереднім snapshot.
        
        Returns:
            Tuple з трьох списків:
            - moved_forward: кандидати що просунулися вперед
            - moved_backward: кандидати що відкотилися назад  
            - new_candidates: нові кандидати
        """
        logger.info(f"Відстежуємо зміни етапів для вакансії {vacancy_id}")
        
        # Завантажуємо попередній snapshot
        previous_snapshot = self._load_snapshot(vacancy_id)
        
        # Отримуємо поточний стан
        current_state = self.get_current_vacancy_state(vacancy_id)
        
        # Зберігаємо новий snapshot
        self._save_snapshot(vacancy_id, current_state)
        
        # Якщо немає попереднього snapshot - це перший запуск
        if not previous_snapshot:
            logger.info(f"Перший snapshot для вакансії {vacancy_id}, зміни не відстежуються")
            return [], [], current_state['candidates']
        
        # Створюємо словники для швидкого пошуку
        previous_candidates = {c['id']: c for c in previous_snapshot.get('candidates', [])}
        current_candidates = {c['id']: c for c in current_state['candidates']}
        
        moved_forward = []
        moved_backward = []
        new_candidates = []
        
        for candidate_id, current_data in current_candidates.items():
            if candidate_id not in previous_candidates:
                # Новий кандидат
                new_candidates.append(current_data)
            else:
                # Перевіряємо чи змінився етап
                prev_stage = previous_candidates[candidate_id]['stage_id']
                curr_stage = current_data['stage_id']
                
                if curr_stage > prev_stage:
                    moved_forward.append({
                        **current_data,
                        'previous_stage': prev_stage,
                        'current_stage': curr_stage
                    })
                elif curr_stage < prev_stage:
                    moved_backward.append({
                        **current_data,
                        'previous_stage': prev_stage,
                        'current_stage': curr_stage
                    })
        
        logger.info(
            f"Вакансія {vacancy_id}: "
            f"вперед={len(moved_forward)}, "
            f"назад={len(moved_backward)}, "
            f"нові={len(new_candidates)}"
        )
        
        return moved_forward, moved_backward, new_candidates

    def get_vacancy_funnel_health(self, vacancy_id: int) -> Dict[str, Any]:
        """
        Оцінює здоров'я воронки вакансії.
        
        Returns:
            Словник з метриками:
            {
                'total_candidates': 10,
                'stagnant_candidates': 3,
                'stagnant_percentage': 30.0,
                'average_days_stagnant': 5.2,
                'health_status': 'warning',  # 'healthy', 'warning', 'critical'
                'issues': ['3 кандидати застрягли на етапі 1']
            }
        """
        logger.info(f"Аналізуємо здоров'я воронки вакансії {vacancy_id}")
        
        current_state = self.get_current_vacancy_state(vacancy_id)
        stagnant = self.detect_stagnant_candidates(vacancy_id, days_threshold=3)
        
        total = len(current_state['candidates'])
        stagnant_count = len(stagnant)
        
        result = {
            'vacancy_id': vacancy_id,
            'total_candidates': total,
            'stagnant_candidates': stagnant_count,
            'stagnant_percentage': round((stagnant_count / total * 100) if total > 0 else 0, 1),
            'average_days_stagnant': 0,
            'health_status': 'healthy',
            'issues': []
        }
        
        if stagnant:
            result['average_days_stagnant'] = round(
                sum(c['days_stagnant'] for c in stagnant) / len(stagnant), 1
            )
        
        # Визначаємо статус здоров'я
        if stagnant_count == 0:
            result['health_status'] = 'healthy'
        elif stagnant_count < total * 0.3:  # Менше 30%
            result['health_status'] = 'warning'
            result['issues'].append(f"{stagnant_count} кандидатів не рухаються {result['average_days_stagnant']}+ днів")
        else:
            result['health_status'] = 'critical'
            result['issues'].append(f"{stagnant_count} кандидатів застрягли ({result['stagnant_percentage']}%)")
        
        # Перевіряємо розподіл по етапах
        stage_distribution = {}
        for candidate in current_state['candidates']:
            stage_id = candidate['stage_id']
            stage_distribution[stage_id] = stage_distribution.get(stage_id, 0) + 1
        
        # Якщо більше 70% на першому етапі - це проблема
        if stage_distribution.get(1, 0) > total * 0.7 and total >= 3:
            result['health_status'] = 'warning'
            result['issues'].append(f"Більшість кандидатів ({stage_distribution[1]}) застрягли на першому етапі")
        
        logger.info(f"Вакансія {vacancy_id}: статус здоров'я = {result['health_status']}")
        return result
