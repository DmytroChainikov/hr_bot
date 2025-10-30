"""Утиліти для роботи з етапами (stages) Hurma"""
from typing import Dict, Optional, Tuple


# Мапінг ID етапів на їх назви та батьківські етапи (з stage.json)
STAGE_INFO = {
    1: {"name": "Новий", "parent_id": None},
    2: {"name": "Інтервʼю", "parent_id": None},
    3: {"name": "Тестове завдання", "parent_id": None},
    4: {"name": "Фінальне інтервʼю", "parent_id": None},
    5: {"name": "Відмова компанії", "parent_id": None},
    6: {"name": "Резерв", "parent_id": None},
    10: {"name": "Відправлено офер", "parent_id": None},
    11: {"name": "Дзвінок", "parent_id": None},
    13: {"name": "Відмова кандидата", "parent_id": None},
    15: {"name": "Немає відповіді", "parent_id": None},
    16: {"name": "Перше повідомлення", "parent_id": None},
    17: {"name": "Відповідь кандидата", "parent_id": None},
    18: {"name": "Технічна співбесіда", "parent_id": None},
    19: {"name": "Технічне інтервʼю", "parent_id": None},
    20: {"name": "Прийнято офер", "parent_id": None},
    23: {"name": "Надіслано LinkedIn invite", "parent_id": None},
    24: {"name": "Надіслано Email", "parent_id": None},
    25: {"name": "Відхилив офер", "parent_id": None},
    26: {"name": "Запізнився на співбесіду", "parent_id": None},
    27: {"name": "Не влаштовує розташування офісу", "parent_id": None},
    28: {"name": "Не сподобався HR", "parent_id": None},
    29: {"name": "Не влаштовує рівень ЗП", "parent_id": None},
    30: {"name": "Не достатньо досвіду", "parent_id": None},
    31: {"name": "Провалив тестове завдання", "parent_id": None},
    32: {"name": "Не вибрано", "parent_id": 5},
    33: {"name": "За нашою ініціативою", "parent_id": 5},
    34: {"name": "Немає відповіді", "parent_id": 5},
    35: {"name": "Тестове", "parent_id": 5},
    36: {"name": "Не вибрано", "parent_id": 13},
    37: {"name": "Відхилив офер", "parent_id": 13},
    38: {"name": "Інше", "parent_id": 13},
    39: {"name": "Відправлено на філіал", "parent_id": None},
    40: {"name": "На стажуванні", "parent_id": None},
    41: {"name": "Співбесіда", "parent_id": None},
    42: {"name": "Заробітна плата", "parent_id": 13},
    43: {"name": "Не актуально", "parent_id": 13},
    44: {"name": "без відповіді", "parent_id": 5},
    45: {"name": "графік роботи", "parent_id": 5},
    46: {"name": "Без відповіді", "parent_id": None},
    47: {"name": "Графік", "parent_id": 13},
    48: {"name": "Співбесіда з керівником", "parent_id": None},
}

# Для зворотної сумісності
STAGE_NAMES = {stage_id: info["name"] for stage_id, info in STAGE_INFO.items()}

def get_stage_name(stage_id: int) -> str:
    """
    Отримати назву етапу по ID.
    
    Args:
        stage_id: ID етапу
        
    Returns:
        Назва етапу або 'Unknown Stage'
    """
    return STAGE_NAMES.get(stage_id, f"Unknown Stage ({stage_id})")


def get_full_stage_name(stage_id: int) -> str:
    """
    Отримати повну назву етапу з батьківським статусом (якщо є).
    Наприклад: "Відмова компанії (Не вибрано)" або "Новий"
    
    Args:
        stage_id: ID етапу
        
    Returns:
        Повна назва етапу з батьківським (якщо є) або просто назва
    """
    stage_info = STAGE_INFO.get(stage_id)
    
    if not stage_info:
        return f"Unknown Stage ({stage_id})"
    
    stage_name = stage_info["name"]
    parent_id = stage_info["parent_id"]
    
    # Якщо є батьківський етап
    if parent_id is not None:
        parent_info = STAGE_INFO.get(parent_id)
        if parent_info:
            parent_name = parent_info["name"]
            return f"{parent_name} ({stage_name})"
    
    # Якщо батьківського немає - просто назва
    return stage_name


def get_stage_emoji(stage_id: int) -> str:
    """
    Отримати emoji для етапу.
    Якщо етап має батьківський - використовує emoji батьківського.
    
    Args:
        stage_id: ID етапу
        
    Returns:
        Emoji відповідний етапу
    """
    # Перевіряємо чи є батьківський етап
    stage_info = STAGE_INFO.get(stage_id)
    if stage_info and stage_info["parent_id"] is not None:
        # Використовуємо emoji батьківського етапу
        return get_stage_emoji(stage_info["parent_id"])
    
    # Позитивні етапи
    if stage_id in [1, 2, 11, 16, 17, 41, 48]:  # Нові, інтервʼю, дзвінки
        return "🔵"
    elif stage_id in [3, 18, 19]:  # Тестові завдання, технічні інтервʼю
        return "🟡"
    elif stage_id in [4]:  # Фінальне інтервʼю
        return "🟠"
    elif stage_id in [10, 20]:  # Офери прийняті
        return "🟢"
    elif stage_id in [40]:  # На стажуванні
        return "✨"
    # Негативні етапи
    elif stage_id in [5, 13, 25, 31]:  # Відмови
        return "🔴"
    elif stage_id in [15, 34, 44, 46]:  # Без відповіді
        return "⚪"
    # Нейтральні
    elif stage_id in [6]:  # Резерв
        return "🟣"
    else:
        return "⚫"


def format_stage_info(stage_id: int, count: int = None) -> str:
    """
    Форматувати інформацію про етап.
    
    Args:
        stage_id: ID етапу
        count: Кількість кандидатів (опціонально)
        
    Returns:
        Форматований рядок з інформацією про етап
    """
    emoji = get_stage_emoji(stage_id)
    name = get_full_stage_name(stage_id)  # Використовуємо повну назву з батьківським
    
    if count is not None:
        return f"{emoji} {name}: {count}"
    else:
        return f"{emoji} {name}"


# Групи етапів для аналітики
STAGE_GROUPS = {
    'new': [1, 16, 23, 24],  # Нові кандидати
    'interview': [2, 11, 17, 41, 48],  # Інтервʼю
    'testing': [3, 18, 19],  # Тестування
    'final': [4],  # Фінальний етап
    'offer': [10, 20],  # Офери
    'internship': [40],  # Стажування
    'rejection': [5, 13, 25, 31],  # Відмови
    'no_answer': [15, 34, 44, 46],  # Немає відповіді
    'reserve': [6],  # Резерв
}


def get_stage_group(stage_id: int) -> Optional[str]:
    """
    Визначити групу етапу.
    
    Args:
        stage_id: ID етапу
        
    Returns:
        Назва групи або None
    """
    for group_name, stage_ids in STAGE_GROUPS.items():
        if stage_id in stage_ids:
            return group_name
    return None


def get_group_emoji(group_name: str) -> str:
    """
    Отримати emoji для групи етапів.
    
    Args:
        group_name: Назва групи
        
    Returns:
        Emoji
    """
    emojis = {
        'new': '🆕',
        'interview': '💼',
        'testing': '📝',
        'final': '🎯',
        'offer': '🎁',
        'internship': '🎓',
        'rejection': '❌',
        'no_answer': '❓',
        'reserve': '💾',
    }
    return emojis.get(group_name, '📊')
