"""
Function Calling інтеграція для Gemini AI
Дозволяє AI викликати API функції для точного аналізу
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, date, timedelta
import google.generativeai as genai

from core.logger_settings import create_logger

logger = create_logger(__name__)


# Визначення функцій доступних для Gemini
# Використовуємо формат OpenAPI Schema для сумісності
GEMINI_FUNCTIONS = [
    {
        "name": "get_active_vacancies",
        "description": "Отримати список всіх активних вакансій з Hurma. Використовуй коли користувач питає про вакансії, їх кількість, статус.",
        "parameters": {
            "type_": "OBJECT",  # Використовуємо type_ замість type
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_vacancy_details",
        "description": "Отримати детальну інформацію про конкретну вакансію: назва, статус, кількість кандидатів, відповідальний HR.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "vacancy_id": {
                    "type_": "INTEGER",
                    "description": "ID вакансії в Hurma"
                }
            },
            "required": ["vacancy_id"]
        }
    },
    {
        "name": "get_vacancy_candidates",
        "description": "Отримати список кандидатів для вакансії з їх етапами. Використовуй для аналізу прогресу по вакансії.",
        "parameters": {
            "type": "object",
            "properties": {
                "vacancy_id": {
                    "type": "integer",
                    "description": "ID вакансії"
                }
            },
            "required": ["vacancy_id"]
        }
    },
    {
        "name": "get_vacancy_activity",
        "description": "Отримати аналіз активності по вакансії: кількість дзвінків, нові кандидати, рух по етапах за останні N днів.",
        "parameters": {
            "type": "object",
            "properties": {
                "vacancy_id": {
                    "type": "integer",
                    "description": "ID вакансії"
                },
                "days": {
                    "type": "integer",
                    "description": "Кількість днів для аналізу (за замовчуванням 7)",
                    "default": 7
                }
            },
            "required": ["vacancy_id"]
        }
    },
    {
        "name": "get_funnel_health",
        "description": "Отримати статус здоров'я воронки вакансії: healthy/warning/critical з деталями по застійним кандидатам.",
        "parameters": {
            "type": "object",
            "properties": {
                "vacancy_id": {
                    "type": "integer",
                    "description": "ID вакансії"
                }
            },
            "required": ["vacancy_id"]
        }
    },
    {
        "name": "get_stagnant_candidates",
        "description": "Знайти кандидатів які застряли на етапах (без руху 3+ дні).",
        "parameters": {
            "type": "object",
            "properties": {
                "vacancy_id": {
                    "type": "integer",
                    "description": "ID вакансії (опціонально, якщо не вказано - по всіх вакансіях)"
                },
                "days_threshold": {
                    "type": "integer",
                    "description": "Кількість днів без руху (за замовчуванням 3)",
                    "default": 3
                }
            },
            "required": []
        }
    },
    {
        "name": "get_hr_calls_today",
        "description": "Отримати кількість та деталі дзвінків HR за сьогодні з Binotel.",
        "parameters": {
            "type": "object",
            "properties": {
                "hr_internal_number": {
                    "type": "string",
                    "description": "Внутрішній номер HR в Binotel (наприклад '961')"
                }
            },
            "required": ["hr_internal_number"]
        }
    },
    {
        "name": "get_hr_calls_period",
        "description": "Отримати статистику дзвінків HR за період (вхідні, вихідні, тривалість).",
        "parameters": {
            "type": "object",
            "properties": {
                "hr_internal_number": {
                    "type": "string",
                    "description": "Внутрішній номер HR"
                },
                "days_back": {
                    "type": "integer",
                    "description": "Кількість днів назад (за замовчуванням 7)",
                    "default": 7
                }
            },
            "required": ["hr_internal_number"]
        }
    },
    {
        "name": "get_inactive_vacancies",
        "description": "Знайти вакансії без активності (дзвінків, кандидатів, руху) за N днів.",
        "parameters": {
            "type": "object",
            "properties": {
                "days_threshold": {
                    "type": "integer",
                    "description": "Кількість днів без активності (за замовчуванням 3)",
                    "default": 3
                }
            },
            "required": []
        }
    },
    {
        "name": "get_vacancies_without_calls",
        "description": "Знайти вакансії де є кандидати, але немає дзвінків (кросс-аналіз Hurma + Binotel).",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "compare_hr_report_with_system",
        "description": "Порівняти звіт HR з реальними даними системи (Hurma + Binotel) і знайти розбіжності.",
        "parameters": {
            "type": "object",
            "properties": {
                "hr_name": {
                    "type": "string",
                    "description": "Ім'я HR для перевірки"
                },
                "report_date": {
                    "type": "string",
                    "description": "Дата звіту у форматі YYYY-MM-DD (за замовчуванням сьогодні)",
                    "default": None
                }
            },
            "required": ["hr_name"]
        }
    },
    {
        "name": "get_candidate_stage_changes",
        "description": "Отримати історію змін етапів кандидата (рух вперед/назад по воронці).",
        "parameters": {
            "type": "object",
            "properties": {
                "vacancy_id": {
                    "type": "integer",
                    "description": "ID вакансії"
                }
            },
            "required": ["vacancy_id"]
        }
    }
]


def get_function_declarations():
    """
    Отримати декларації функцій для Gemini у правильному форматі
    
    Returns:
        List of function declarations
    """
    declarations = []
    
    for func in GEMINI_FUNCTIONS:
        # Використовуємо простий dict формат для Gemini
        declaration = {
            "name": func["name"],
            "description": func["description"],
            "parameters": func["parameters"]
        }
        declarations.append(declaration)
    
    return declarations


async def execute_function_call(
    function_name: str,
    function_args: Dict[str, Any],
    hurma_service,
    binotel_service,
    analytics,
    vacancy_activity_monitor,
    candidate_flow_tracker
) -> Dict[str, Any]:
    """
    Виконати виклик функції і повернути результат
    
    Args:
        function_name: Назва функції
        function_args: Аргументи функції
        hurma_service: HurmaService instance
        binotel_service: BinotelService instance
        analytics: Analytics instance
        vacancy_activity_monitor: VacancyActivityMonitor instance
        candidate_flow_tracker: CandidateFlowTracker instance
        
    Returns:
        Результат виконання функції
    """
    try:
        logger.info(f"Gemini викликає функцію: {function_name} з аргументами: {function_args}")
        
        # Маршрутизація викликів
        if function_name == "get_active_vacancies":
            result = await _get_active_vacancies(hurma_service)
            
        elif function_name == "get_vacancy_details":
            vacancy_id = function_args.get("vacancy_id")
            result = await _get_vacancy_details(hurma_service, vacancy_id)
            
        elif function_name == "get_vacancy_candidates":
            vacancy_id = function_args.get("vacancy_id")
            result = await _get_vacancy_candidates(hurma_service, vacancy_id)
            
        elif function_name == "get_vacancy_activity":
            vacancy_id = function_args.get("vacancy_id")
            days = function_args.get("days", 7)
            result = _get_vacancy_activity(vacancy_activity_monitor, vacancy_id, days)
            
        elif function_name == "get_funnel_health":
            vacancy_id = function_args.get("vacancy_id")
            result = _get_funnel_health(candidate_flow_tracker, vacancy_id)
            
        elif function_name == "get_stagnant_candidates":
            vacancy_id = function_args.get("vacancy_id")
            days_threshold = function_args.get("days_threshold", 3)
            result = _get_stagnant_candidates(candidate_flow_tracker, vacancy_id, days_threshold)
            
        elif function_name == "get_hr_calls_today":
            internal_number = function_args.get("hr_internal_number")
            result = await _get_hr_calls_today(binotel_service, internal_number)
            
        elif function_name == "get_hr_calls_period":
            internal_number = function_args.get("hr_internal_number")
            days_back = function_args.get("days_back", 7)
            result = await _get_hr_calls_period(binotel_service, internal_number, days_back)
            
        elif function_name == "get_inactive_vacancies":
            days_threshold = function_args.get("days_threshold", 3)
            result = _get_inactive_vacancies(vacancy_activity_monitor, days_threshold)
            
        elif function_name == "get_vacancies_without_calls":
            result = _get_vacancies_without_calls(vacancy_activity_monitor)
            
        elif function_name == "compare_hr_report_with_system":
            hr_name = function_args.get("hr_name")
            report_date = function_args.get("report_date")
            result = await _compare_hr_report(analytics, hr_name, report_date)
            
        elif function_name == "get_candidate_stage_changes":
            vacancy_id = function_args.get("vacancy_id")
            result = _get_candidate_stage_changes(candidate_flow_tracker, vacancy_id)
            
        else:
            result = {"error": f"Невідома функція: {function_name}"}
        
        logger.info(f"Функція {function_name} виконана успішно")
        return result
        
    except Exception as e:
        logger.error(f"Помилка виконання функції {function_name}: {e}")
        return {"error": str(e)}


# ============= Імплементація функцій =============

async def _get_active_vacancies(hurma_service) -> Dict[str, Any]:
    """Отримати активні вакансії"""
    vacancies = hurma_service.get_job_openings()
    if vacancies and 'data' in vacancies:
        active = [v for v in vacancies['data'] if v.get('status') == 'active']
        return {
            "total": len(active),
            "vacancies": [
                {
                    "id": v.get('id'),
                    "title": v.get('title'),
                    "status": v.get('status'),
                    "candidates_count": v.get('candidates_count', 0)
                }
                for v in active[:20]  # Перші 20 для оптимізації
            ]
        }
    return {"total": 0, "vacancies": []}


async def _get_vacancy_details(hurma_service, vacancy_id: int) -> Dict[str, Any]:
    """Отримати деталі вакансії"""
    vacancies = hurma_service.get_job_openings()
    if vacancies and 'data' in vacancies:
        for v in vacancies['data']:
            if v.get('id') == vacancy_id:
                return {
                    "id": v.get('id'),
                    "title": v.get('title'),
                    "status": v.get('status'),
                    "candidates_count": v.get('candidates_count', 0),
                    "created_at": v.get('created_at'),
                    "updated_at": v.get('updated_at')
                }
    return {"error": f"Вакансію {vacancy_id} не знайдено"}


async def _get_vacancy_candidates(hurma_service, vacancy_id: int) -> Dict[str, Any]:
    """Отримати кандидатів вакансії"""
    candidates = hurma_service.get_candidates(vacancy_id=vacancy_id, per_page=100)
    if candidates and 'data' in candidates:
        return {
            "total": len(candidates['data']),
            "candidates": [
                {
                    "id": c.get('id'),
                    "name": c.get('name'),
                    "stage_id": c.get('stage_id'),
                    "created_at": c.get('created_at')
                }
                for c in candidates['data'][:50]  # Перші 50
            ]
        }
    return {"total": 0, "candidates": []}


def _get_vacancy_activity(monitor, vacancy_id: int, days: int) -> Dict[str, Any]:
    """Отримати активність вакансії"""
    activity = monitor.get_vacancy_activity(vacancy_id, days)
    return activity


def _get_funnel_health(tracker, vacancy_id: int) -> Dict[str, Any]:
    """Отримати здоров'я воронки"""
    health = tracker.get_vacancy_funnel_health(vacancy_id)
    return health


def _get_stagnant_candidates(tracker, vacancy_id: Optional[int], days_threshold: int) -> Dict[str, Any]:
    """Отримати застійних кандидатів"""
    stagnant = tracker.detect_stagnant_candidates(vacancy_id, days_threshold)
    return {"stagnant_candidates": stagnant, "threshold_days": days_threshold}


async def _get_hr_calls_today(binotel_service, internal_number: str) -> Dict[str, Any]:
    """Отримати дзвінки HR за сьогодні"""
    from datetime import datetime, timedelta
    now = datetime.now()
    date_from = now.replace(hour=0, minute=0, second=0)
    date_to = now
    
    result = binotel_service.get_calls_by_internal_number(internal_number, date_from, date_to)
    if result and 'callDetails' in result:
        calls = list(result['callDetails'].values())
        return {
            "total_calls": len(calls),
            "date": now.strftime("%Y-%m-%d"),
            "internal_number": internal_number
        }
    return {"total_calls": 0, "date": now.strftime("%Y-%m-%d")}


async def _get_hr_calls_period(binotel_service, internal_number: str, days_back: int) -> Dict[str, Any]:
    """Отримати дзвінки HR за період"""
    from datetime import datetime, timedelta
    now = datetime.now()
    date_from = now - timedelta(days=days_back)
    
    result = binotel_service.get_calls_by_internal_number(internal_number, date_from, now)
    if result and 'callDetails' in result:
        calls = list(result['callDetails'].values())
        incoming = sum(1 for c in calls if c.get('disposition') == 'ANSWERED')
        outgoing = len(calls) - incoming
        
        return {
            "total_calls": len(calls),
            "incoming": incoming,
            "outgoing": outgoing,
            "period_days": days_back,
            "internal_number": internal_number
        }
    return {"total_calls": 0, "period_days": days_back}


def _get_inactive_vacancies(monitor, days_threshold: int) -> Dict[str, Any]:
    """Отримати неактивні вакансії"""
    inactive = monitor.get_inactive_vacancies(days_threshold)
    return {"inactive_vacancies": inactive, "threshold_days": days_threshold}


def _get_vacancies_without_calls(monitor) -> Dict[str, Any]:
    """Отримати вакансії без дзвінків"""
    no_calls = monitor.get_vacancies_without_calls()
    return {"vacancies_without_calls": no_calls}


async def _compare_hr_report(analytics, hr_name: str, report_date: Optional[str]) -> Dict[str, Any]:
    """Порівняти звіт HR з системою"""
    if not report_date:
        report_date = date.today().isoformat()
    
    # Тут можна додати логіку порівняння
    return {
        "hr_name": hr_name,
        "report_date": report_date,
        "note": "Функція порівняння звітів у розробці"
    }


def _get_candidate_stage_changes(tracker, vacancy_id: int) -> Dict[str, Any]:
    """Отримати зміни етапів кандидатів"""
    changes = tracker.track_stage_changes(vacancy_id)
    moved_forward, moved_backward, new_candidates = changes
    
    return {
        "vacancy_id": vacancy_id,
        "moved_forward": len(moved_forward),
        "moved_backward": len(moved_backward),
        "new_candidates": len(new_candidates),
        "details": {
            "forward": [{"candidate_id": c.get('id'), "from": c.get('from_stage'), "to": c.get('to_stage')} for c in moved_forward],
            "backward": [{"candidate_id": c.get('id'), "from": c.get('from_stage'), "to": c.get('to_stage')} for c in moved_backward],
            "new": [{"candidate_id": c.get('id'), "stage": c.get('stage')} for c in new_candidates]
        }
    }
