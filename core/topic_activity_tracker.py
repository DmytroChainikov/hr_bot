"""
Трекер активності в Telegram топіках вакансій.

Відстежує коли останній раз був activity в топіку кожної вакансії
та виявляє неактивні топіки для нагадування HR.
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import os

from core.logger_settings import create_logger

logger = create_logger(__name__)


class TopicActivityTracker:
    """Відстежує активність в топіках вакансій"""

    def __init__(self, storage_path: str = "topic_activity.json"):
        """
        Ініціалізація трекера.
        
        Args:
            storage_path: Шлях до файлу для збереження даних
        """
        self.storage_path = storage_path
        self.data = self._load_data()
        logger.info(f"TopicActivityTracker ініціалізовано. Відстежується {len(self.data)} топіків")

    def _load_data(self) -> Dict[str, Any]:
        """
        Завантажує дані про активність топіків.
        
        Returns:
            Словник вигляду:
            {
                'thread_123': {
                    'vacancy_id': 84,
                    'vacancy_name': 'Python Developer',
                    'last_message_time': '2025-10-31T14:00:00',
                    'last_message_from_user_id': 123456,
                    'last_message_from_username': 'ivan_hr',
                    'total_messages': 42
                },
                ...
            }
        """
        if not os.path.exists(self.storage_path):
            logger.info("Файл з даними топіків не знайдено, створюємо новий")
            return {}
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Завантажено дані про {len(data)} топіків")
            return data
        except Exception as e:
            logger.error(f"Помилка завантаження даних топіків: {e}")
            return {}

    def _save_data(self) -> None:
        """Зберігає дані про активність топіків"""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.debug("Дані топіків збережено")
        except Exception as e:
            logger.error(f"Помилка збереження даних топіків: {e}")

    def register_topic(
        self, 
        thread_id: int, 
        vacancy_id: int, 
        vacancy_name: str
    ) -> None:
        """
        Реєструє топік вакансії в системі.
        
        Args:
            thread_id: ID топіка в Telegram
            vacancy_id: ID вакансії в Hurma
            vacancy_name: Назва вакансії
        """
        thread_key = f"thread_{thread_id}"
        
        if thread_key not in self.data:
            self.data[thread_key] = {
                'vacancy_id': vacancy_id,
                'vacancy_name': vacancy_name,
                'last_message_time': None,
                'last_message_from_user_id': None,
                'last_message_from_username': None,
                'total_messages': 0
            }
            logger.info(f"Зареєстровано новий топік {thread_id} для вакансії {vacancy_name}")
            self._save_data()
        else:
            # Оновлюємо назву вакансії якщо змінилася
            if self.data[thread_key]['vacancy_name'] != vacancy_name:
                self.data[thread_key]['vacancy_name'] = vacancy_name
                logger.info(f"Оновлено назву вакансії для топіка {thread_id}: {vacancy_name}")
                self._save_data()

    def update_activity(
        self, 
        thread_id: int, 
        user_id: int, 
        username: Optional[str] = None
    ) -> None:
        """
        Оновлює час останньої активності в топіку.
        
        Args:
            thread_id: ID топіка
            user_id: ID користувача який написав
            username: Username користувача (опціонально)
        """
        thread_key = f"thread_{thread_id}"
        
        if thread_key not in self.data:
            logger.warning(f"Топік {thread_id} не зареєстрований, пропускаємо оновлення")
            return
        
        now = datetime.now()
        self.data[thread_key]['last_message_time'] = now.isoformat()
        self.data[thread_key]['last_message_from_user_id'] = user_id
        self.data[thread_key]['last_message_from_username'] = username
        self.data[thread_key]['total_messages'] = self.data[thread_key].get('total_messages', 0) + 1
        
        logger.debug(f"Оновлено активність топіка {thread_id}: {now.isoformat()}")
        self._save_data()

    def get_inactive_topics(self, days_threshold: int = 3) -> List[Dict[str, Any]]:
        """
        Знаходить топіки без активності більше N днів.
        
        Args:
            days_threshold: Поріг неактивності в днях
            
        Returns:
            Список топіків вигляду:
            [
                {
                    'thread_id': 123,
                    'vacancy_id': 84,
                    'vacancy_name': 'Python Developer',
                    'days_inactive': 5,
                    'last_activity': '2025-10-26T14:00:00',
                    'last_user_id': 123456,
                    'last_username': 'ivan_hr'
                },
                ...
            ]
        """
        logger.info(f"Шукаємо неактивні топіки (поріг: {days_threshold} днів)")
        
        inactive = []
        now = datetime.now()
        threshold = timedelta(days=days_threshold)
        
        for thread_key, topic_data in self.data.items():
            # Пропускаємо якщо ніколи не було повідомлень
            if not topic_data.get('last_message_time'):
                continue
            
            try:
                last_time = datetime.fromisoformat(topic_data['last_message_time'])
                days_inactive = (now - last_time).days
                
                if days_inactive >= days_threshold:
                    thread_id = int(thread_key.replace('thread_', ''))
                    inactive.append({
                        'thread_id': thread_id,
                        'vacancy_id': topic_data['vacancy_id'],
                        'vacancy_name': topic_data['vacancy_name'],
                        'days_inactive': days_inactive,
                        'last_activity': topic_data['last_message_time'],
                        'last_user_id': topic_data.get('last_message_from_user_id'),
                        'last_username': topic_data.get('last_message_from_username')
                    })
                    
            except Exception as e:
                logger.warning(f"Помилка обробки топіка {thread_key}: {e}")
                continue
        
        logger.info(f"Знайдено {len(inactive)} неактивних топіків")
        return inactive

    def get_topic_info(self, thread_id: int) -> Optional[Dict[str, Any]]:
        """
        Повертає інформацію про конкретний топік.
        
        Args:
            thread_id: ID топіка
            
        Returns:
            Словник з інформацією або None якщо не знайдено
        """
        thread_key = f"thread_{thread_id}"
        return self.data.get(thread_key)

    def get_vacancy_topic(self, vacancy_id: int) -> Optional[Dict[str, Any]]:
        """
        Знаходить топік за ID вакансії.
        
        Args:
            vacancy_id: ID вакансії
            
        Returns:
            Словник з інформацією про топік або None
        """
        for thread_key, topic_data in self.data.items():
            if topic_data['vacancy_id'] == vacancy_id:
                thread_id = int(thread_key.replace('thread_', ''))
                return {
                    'thread_id': thread_id,
                    **topic_data
                }
        return None

    def get_all_topics(self) -> List[Dict[str, Any]]:
        """
        Повертає список всіх відстежуваних топіків.
        
        Returns:
            Список топіків з інформацією
        """
        topics = []
        for thread_key, topic_data in self.data.items():
            thread_id = int(thread_key.replace('thread_', ''))
            topics.append({
                'thread_id': thread_id,
                **topic_data
            })
        return topics

    def remove_topic(self, thread_id: int) -> bool:
        """
        Видаляє топік з відстеження.
        
        Args:
            thread_id: ID топіка
            
        Returns:
            True якщо видалено, False якщо не знайдено
        """
        thread_key = f"thread_{thread_id}"
        if thread_key in self.data:
            del self.data[thread_key]
            logger.info(f"Видалено топік {thread_id} з відстеження")
            self._save_data()
            return True
        return False

    def get_statistics(self) -> Dict[str, Any]:
        """
        Повертає статистику по всіх топіках.
        
        Returns:
            Словник зі статистикою
        """
        now = datetime.now()
        total = len(self.data)
        active_today = 0
        active_week = 0
        inactive = 0
        never_active = 0
        
        for topic_data in self.data.values():
            if not topic_data.get('last_message_time'):
                never_active += 1
                continue
            
            try:
                last_time = datetime.fromisoformat(topic_data['last_message_time'])
                days_diff = (now - last_time).days
                
                if days_diff == 0:
                    active_today += 1
                if days_diff <= 7:
                    active_week += 1
                if days_diff >= 3:
                    inactive += 1
                    
            except Exception:
                continue
        
        return {
            'total_topics': total,
            'active_today': active_today,
            'active_this_week': active_week,
            'inactive_3_plus_days': inactive,
            'never_active': never_active
        }
