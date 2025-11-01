# 🤖 Gemini Function Calling - Документація

## Огляд

Gemini AI тепер може **безпосередньо викликати API функції** для отримання точних даних з Hurma та Binotel замість здогадок!

## ✨ Можливості

### Доступні функції (13 штук):

#### 📊 Вакансії
1. **get_active_vacancies** - Список всіх активних вакансій
2. **get_vacancy_details** - Детальна інформація про вакансію
3. **get_vacancy_candidates** - Кандидати вакансії з етапами
4. **get_vacancy_activity** - Активність вакансії (дзвінки + кандидати за N днів)

#### 🎯 Воронка та прогрес
5. **get_funnel_health** - Статус здоров'я воронки (healthy/warning/critical)
6. **get_stagnant_candidates** - Застійні кандидати (без руху 3+ дні)
7. **get_candidate_stage_changes** - Історія змін етапів

#### 📞 Дзвінки (Binotel)
8. **get_hr_calls_today** - Дзвінки HR за сьогодні
9. **get_hr_calls_period** - Статистика дзвінків за період

#### 🔍 Аналітика
10. **get_inactive_vacancies** - Вакансії без активності
11. **get_vacancies_without_calls** - Вакансії з кандидатами але без дзвінків (кросс-аналіз)
12. **compare_hr_report_with_system** - Порівняння звіту HR з реальними даними
13. **get_candidate_stage_changes** - Рух кандидатів по етапах

---

## 🎯 Приклади використання

### Користувач питає → AI викликає функцію

```
Користувач: "Скільки у нас активних вакансій?"
AI викликає: get_active_vacancies()
AI отримує: {"total": 10, "vacancies": [...]}
AI відповідає: "Зараз у нас 10 активних вакансій: [список]"
```

```
Користувач: "Як справи з вакансією 84?"
AI викликає: get_vacancy_activity(vacancy_id=84, days=7)
AI отримує: {"calls_count": 5, "new_candidates": 3, "is_active": true}
AI відповідає: "По вакансії 84 за тиждень: 5 дзвінків, 3 нові кандидати. Вакансія активна! 👍"
```

```
Користувач: "Скільки я дзвонив цього тижня?"
AI викликає: get_hr_calls_period(hr_internal_number="961", days_back=7)
AI отримує: {"total_calls": 45, "incoming": 20, "outgoing": 25}
AI відповідає: "За тиждень ти зробив 45 дзвінків: 25 вихідних та 20 вхідних 📞"
```

```
Користувач: "Є вакансії які застояли?"
AI викликає: get_inactive_vacancies(days_threshold=3)
AI отримує: {"inactive_vacancies": [{"id": 82, "days_since_activity": 5}, ...]}
AI відповідає: "Так, є 2 вакансії без активності 3+ дні: вакансія 82 (5 днів)..."
```

---

## 🔧 Технічна імплементація

### Архітектура

```
User Message
    ↓
Gemini AI (з Function Calling)
    ↓
Аналізує запит
    ↓
Визначає потрібну функцію
    ↓
Викликає: get_vacancy_activity(vacancy_id=84)
    ↓
services/gemini_function_calling.py
    ↓
execute_function_call()
    ↓
Викликає реальний API (Hurma/Binotel)
    ↓
Повертає результат → Gemini
    ↓
Gemini генерує природну відповідь
    ↓
User отримує точну відповідь
```

### Файли

1. **services/gemini_function_calling.py** (500+ рядків)
   - Декларації всіх функцій
   - execute_function_call() - маршрутизація
   - Імплементація кожної функції

2. **services/gemini_service.py** (оновлено)
   - Ініціалізація з tools
   - Обробка function_call в chat()
   - Ітеративне виконання (до 3 викликів)

3. **main.py** (оновлено)
   - Створення всіх сервісів
   - Передача до GeminiService

---

## 🚀 Переваги

### До Function Calling:
```
Користувач: "Скільки вакансій?"
AI: "У нас багато вакансій, продовжуй працювати! 👍"
❌ Неточна відповідь
```

### З Function Calling:
```
Користувач: "Скільки вакансій?"
AI викликає API → отримує 10
AI: "Зараз у нас 10 активних вакансій"
✅ Точна відповідь з реальних даних!
```

### Основні переваги:
- ✅ **Точність**: Реальні дані замість здогадок
- ✅ **Актуальність**: Завжди свіжі дані з API
- ✅ **Глибина**: Може робити кросс-аналіз (Hurma + Binotel)
- ✅ **Природність**: AI сам розуміє коли викликати функції
- ✅ **Ланцюжки**: Може викликати кілька функцій підряд

---

## 📝 Тестування

Запустіть тест:

```bash
python test_function_calling.py
```

Тест виконає 4 запити:
1. "Скільки активних вакансій?"
2. "Скільки дзвінків на номері 961?"
3. "Є вакансії без активності?"
4. "Як справи з вакансією 84?"

Ви побачите як AI:
1. Аналізує запит
2. Викликає потрібну функцію
3. Отримує реальні дані
4. Формує природну відповідь

---

## ⚙️ Налаштування

### В main.py (вже зроблено):

```python
# Створення сервісів
candidate_flow_tracker = CandidateFlowTracker(hurma_service)
vacancy_activity_monitor = VacancyActivityMonitor(hurma_service, binotel_service)

# Ініціалізація Gemini з Function Calling
gemini_service = GeminiService(
    hurma_service=hurma_service,
    binotel_service=binotel_service,
    analytics=analytics_service,
    vacancy_activity_monitor=vacancy_activity_monitor,
    candidate_flow_tracker=candidate_flow_tracker
)
```

### Системний промпт (оновлено):

```
ДОСТУПНІ ФУНКЦІЇ ДЛЯ ТОЧНОГО АНАЛІЗУ:
- Коли користувач питає про вакансії, кандидатів, дзвінки або прогрес - 
  ВИКОРИСТОВУЙ доступні функції
- Функції дають РЕАЛЬНІ ДАНІ з Hurma та Binotel, а не здогадки
```

---

## 🔍 Приклади реальних діалогів

### Діалог 1: Аналіз вакансії
```
User: Розкажи як справи з вакансією "Менеджер з продажу"?

AI: [викликає get_active_vacancies() → знаходить ID]
    [викликає get_vacancy_activity(vacancy_id=84)]
    [отримує: calls=15, new_candidates=5, moved_forward=3]

AI: "По вакансії 'Менеджер з продажу':
     📞 15 дзвінків за тиждень
     🆕 5 нових кандидатів
     ⬆️ 3 кандидати просунулись вперед
     Вакансія активна, продовжуй у тому ж дусі! 💪"
```

### Діалог 2: Пошук проблем
```
User: Що у нас не так з вакансіями?

AI: [викликає get_inactive_vacancies()]
    [викликає get_vacancies_without_calls()]
    [отримує списки проблемних вакансій]

AI: "Знайшов пару моментів:
     🔴 2 вакансії без активності 5+ днів
     📞 3 вакансії мають кандидатів але немає дзвінків
     
     Рекомендую звернути увагу на вакансії 82, 70, 71"
```

### Діалог 3: Персональна статистика
```
User: Як моя продуктивність цього тижня?

AI: [викликає get_hr_calls_period(hr_internal_number="961", days=7)]
    [отримує: total=45, incoming=20, outgoing=25]

AI: "Твоя продуктивність за тиждень:
     📞 45 дзвінків (25 вихідних + 20 вхідних)
     Це солідний результат! Продовжуй тримати темп 💪"
```

---

## 🎓 Розширення функцій

Щоб додати нову функцію:

1. **Додати декларацію** в `gemini_function_calling.py`:
```python
{
    "name": "my_new_function",
    "description": "Що робить функція",
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."}
        },
        "required": ["param1"]
    }
}
```

2. **Додати обробник** в `execute_function_call()`:
```python
elif function_name == "my_new_function":
    param1 = function_args.get("param1")
    result = _my_new_function(param1)
```

3. **Імплементувати логіку**:
```python
def _my_new_function(param1: str) -> Dict[str, Any]:
    # Ваша логіка
    return {"result": "..."}
```

---

## ✅ Готово!

Gemini тепер розуміє запити та автоматично викликає потрібні функції для точних відповідей! 🚀
