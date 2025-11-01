"""Конфігурація проекту"""
import os
import json
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()


class HRInfo:
    """Інформація про HR"""
    def __init__(self, name: str, username: str, telegram_id: Optional[int], hurma_id: int, binotel_internal: str):
        self.name = name
        self.username = username
        self.telegram_id = telegram_id
        self.hurma_id = hurma_id
        self.binotel_internal = binotel_internal
    
    def __repr__(self):
        return f"HRInfo(name={self.name}, telegram_id={self.telegram_id}, hurma_id={self.hurma_id}, binotel={self.binotel_internal})"


class Config:
    """Клас конфігурації"""
    
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
    
    # Allowed Groups (comma-separated chat IDs)
    ALLOWED_GROUP_IDS_RAW = os.getenv("ALLOWED_GROUP_IDS", "")
    
    # Allowed Topic IDs (comma-separated topic IDs)
    ALLOWED_TOPIC_IDS_RAW = os.getenv("ALLOWED_TOPIC_IDS", "")
    
    # Binotel
    BINOTEL_KEY = os.getenv("BINOTEL_KEY")
    BINOTEL_SECRET = os.getenv("BINOTEL_SECRET")
    
    # Hurma
    HURMA_API_KEY = os.getenv("HURMA_API_KEY")
    HURMA_CLIENT_ID = os.getenv("HURMA_CLIENT_ID")
    HURMA_CLIENT_SECRET = os.getenv("HURMA_CLIENT_SECRET")
    HURMA_USERNAME = os.getenv("HURMA_USERNAME")
    HURMA_PASSWORD = os.getenv("HURMA_PASSWORD")
    HURMA_COMPANY = os.getenv("HURMA_COMPANY", "yourcompany")
    
    # Gemini AI
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # HRs
    HRS_RAW = os.getenv("HRS", "")
    
    # Файл для зберігання вакансій з назвами
    VACANCIES_FILE = "vacancies.json"
    
    @classmethod
    def get_allowed_group_ids(cls) -> List[int]:
        """Парсинг дозволених ID груп"""
        if not cls.ALLOWED_GROUP_IDS_RAW:
            return []
        
        group_ids = []
        for gid in cls.ALLOWED_GROUP_IDS_RAW.split(","):
            gid = gid.strip()
            if gid:
                try:
                    group_ids.append(int(gid))
                except ValueError:
                    pass
        return group_ids
    
    @classmethod
    def get_allowed_topic_ids(cls) -> List[int]:
        """Парсинг дозволених ID топіків"""
        if not cls.ALLOWED_TOPIC_IDS_RAW:
            return []
        
        topic_ids = []
        for tid in cls.ALLOWED_TOPIC_IDS_RAW.split(","):
            tid = tid.strip()
            if tid:
                try:
                    topic_ids.append(int(tid))
                except ValueError:
                    pass
        return topic_ids
    
    @classmethod
    def get_hrs(cls) -> List[HRInfo]:
        """Парсинг списку HR з конфігурації"""
        hrs = []
        if cls.HRS_RAW:
            for hr_str in cls.HRS_RAW.split(","):
                parts = hr_str.strip().split("/")
                if len(parts) == 5:  # Name/username/telegram_id/HURMA_USER_ID/BINOTEL_INTERNAL_NUMBER
                    name, username, telegram_id, hurma_id, binotel_internal = parts
                    
                    # Парсимо telegram_id (може бути пустим або 'none')
                    tg_id = None
                    if telegram_id and telegram_id.lower() not in ['none', '']:
                        try:
                            tg_id = int(telegram_id.strip())
                        except ValueError:
                            pass
                    
                    hrs.append(HRInfo(
                        name=name.strip(),
                        username=username.strip(),
                        telegram_id=tg_id,
                        hurma_id=int(hurma_id.strip()),
                        binotel_internal=binotel_internal.strip()
                    ))
                elif len(parts) == 4:  # Старий формат без telegram_id
                    name, username, hurma_id, binotel_internal = parts
                    hrs.append(HRInfo(
                        name=name.strip(),
                        username=username.strip(),
                        telegram_id=None,
                        hurma_id=int(hurma_id.strip()),
                        binotel_internal=binotel_internal.strip()
                    ))
        return hrs
    
    @classmethod
    def get_hr_by_hurma_id(cls, hurma_id: int) -> Optional[HRInfo]:
        """Отримання HR за ID в Hurma"""
        for hr in cls.get_hrs():
            if hr.hurma_id == hurma_id:
                return hr
        return None
    
    @classmethod
    def get_hr_by_telegram_id(cls, telegram_id: int) -> Optional[HRInfo]:
        """Отримання HR за Telegram ID"""
        for hr in cls.get_hrs():
            if hr.telegram_id == telegram_id:
                return hr
        return None
    
    @classmethod
    def get_hr_by_name(cls, name: str) -> Optional[HRInfo]:
        """Отримання HR за ім'ям"""
        for hr in cls.get_hrs():
            if hr.name.lower() == name.lower():
                return hr
        return None
    
    @classmethod
    def _load_vacancies(cls) -> Dict[str, str]:
        """Завантажити вакансії з JSON файлу"""
        try:
            if os.path.exists(cls.VACANCIES_FILE):
                with open(cls.VACANCIES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('vacancies', {})
        except Exception as e:
            print(f"Помилка завантаження вакансій: {e}")
        return {}
    
    @classmethod
    def _save_vacancies(cls, vacancies: Dict[str, str]):
        """Зберегти вакансії в JSON файл"""
        try:
            with open(cls.VACANCIES_FILE, 'w', encoding='utf-8') as f:
                json.dump({'vacancies': vacancies}, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Помилка збереження вакансій: {e}")
    
    @classmethod
    def get_vacancy_ids(cls) -> List[int]:
        """Отримання списку ID вакансій для відстеження"""
        vacancies = cls._load_vacancies()
        vacancy_ids = [int(vid) for vid in vacancies.keys()]
        return sorted(vacancy_ids)
    
    @classmethod
    def get_vacancies(cls) -> Dict[int, str]:
        """
        Отримання словника вакансій {id: назва}.
        
        Returns:
            Dict[int, str]: Словник де ключ - ID вакансії, значення - назва
        """
        vacancies = cls._load_vacancies()
        return {int(vid): name for vid, name in vacancies.items()}
    
    @classmethod
    def get_vacancy_name(cls, vacancy_id: int) -> Optional[str]:
        """Отримати назву вакансії по ID"""
        vacancies = cls.get_vacancies()
        return vacancies.get(vacancy_id)
    
    @classmethod
    def add_vacancy(cls, vacancy_id: int, vacancy_name: str) -> bool:
        """
        Додати вакансію до списку відстеження.
        
        Args:
            vacancy_id: ID вакансії
            vacancy_name: Назва вакансії
            
        Returns:
            bool: True якщо додано, False якщо вже існує
        """
        vacancies = cls._load_vacancies()
        vacancy_key = str(vacancy_id)
        
        if vacancy_key in vacancies:
            return False  # Вже існує
        
        vacancies[vacancy_key] = vacancy_name
        cls._save_vacancies(vacancies)
        return True
    
    @classmethod
    def remove_vacancy(cls, vacancy_id: int) -> Tuple[bool, Optional[str]]:
        """
        Видалити вакансію зі списку відстеження.
        
        Args:
            vacancy_id: ID вакансії
            
        Returns:
            Tuple[bool, Optional[str]]: (True/False, назва видаленої вакансії або None)
        """
        vacancies = cls._load_vacancies()
        vacancy_key = str(vacancy_id)
        
        if vacancy_key not in vacancies:
            return False, None  # Не існує
        
        vacancy_name = vacancies.pop(vacancy_key)
        cls._save_vacancies(vacancies)
        return True, vacancy_name
    
    @classmethod
    def validate(cls):
        """Перевірка наявності всіх необхідних змінних"""
        required = [
            "TELEGRAM_BOT_TOKEN",
            "BINOTEL_KEY",
            "BINOTEL_SECRET",
            "HURMA_API_KEY",
        ]
        
        missing = []
        for var in required:
            if not getattr(cls, var):
                missing.append(var)
        
        if missing:
            raise ValueError(f"Відсутні обов'язкові змінні оточення: {', '.join(missing)}")
