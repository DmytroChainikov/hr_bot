# Оновлення: Робота з job_openings

## Що змінилось?

### ❌ Раніше (неправильно)
```python
# Намагались отримати дані з полів vacancy та stage
vacancy = candidate.get('vacancy', {})
vacancy_id = vacancy.get('id')
vacancy_name = vacancy.get('name')

stage = candidate.get('stage', {})
stage_id = stage.get('id')
stage_name = stage.get('name')
```

**Проблема:** Ці поля можуть бути пустими або некоректними, бо реальна інформація зберігається в `job_openings`.

### ✅ Зараз (правильно)
```python
# Отримуємо дані з job_openings
job_openings = candidate.get('job_openings', [])

for job in job_openings:
    vacancy_id = job.get('jobopening_id')  # ID вакансії
    stage_id = job.get('stage_id')         # ID етапу
```

**Переваги:** 
- Точна інформація про вакансію та етап
- Підтримка кількох вакансій для одного кандидата
- Відповідає реальній структурі API

## Структура job_openings

```json
{
  "id": 123,
  "name": "Іван Петренко",
  "job_openings": [
    {
      "jobopening_id": 84,
      "stage_id": 1
    }
  ],
  "responsible_recruiter": {
    "id": 456,
    "name": "Олена Іваненко"
  }
}
```

### Опис полів:
- `jobopening_id` - ID вакансії (відповідає ID з `get_job_openings`)
- `stage_id` - ID етапу (відповідає ID з `get_job_stages`)

## Зміни в коді

### 1. Додана допоміжна функція

```python
def _get_vacancy_info_from_job_openings(
    self,
    candidate: Dict[str, Any],
    vacancy_id: Optional[int] = None,
    vacancies_with_stages: Optional[Dict[int, Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Отримати інформацію про вакансію та етап з job_openings
    
    Returns:
        {
            'vacancy_id': int,
            'vacancy_name': str,
            'stage_id': int,
            'stage_name': str
        }
    """
```

**Використання:**
```python
vacancy_info = self._get_vacancy_info_from_job_openings(
    candidate,
    vacancy_id=84,
    vacancies_with_stages=vacancies_with_stages
)

print(vacancy_info['vacancy_name'])  # "Python Developer (Middle)"
print(vacancy_info['stage_name'])    # "Нові кандидати"
```

### 2. Оновлено метод get_vacancy_statistics

**Фільтрація кандидатів:**
```python
# Старий код
if candidate_vacancy_id == vacancy_id:
    all_candidates.append(candidate)

# Новий код
job_openings = candidate.get('job_openings', [])
for job_opening in job_openings:
    if job_opening.get('jobopening_id') == vacancy_id:
        all_candidates.append(candidate)
        break
```

**Отримання етапу:**
```python
# Старий код
stage = candidate.get('stage', {})
stage_name = stage.get('name', 'Не вказано')

# Новий код
job_openings = candidate.get('job_openings', [])
for job_opening in job_openings:
    if job_opening.get('jobopening_id') == vacancy_id:
        stage_id = job_opening.get('stage_id')
        break

# Знаходимо назву етапу
for stage in stages:
    if stage.get('id') == stage_id:
        stage_name = stage.get('name', 'Не вказано')
        break
```

### 3. Оновлено методи форматування

Всі методи, що працюють з кандидатами, тепер використовують `_get_vacancy_info_from_job_openings`:

- ✅ `get_hr_personal_report` - персональні звіти HR
- ✅ `_format_candidates_details` - детальна інформація
- ✅ `_format_candidates_by_vacancy_and_stage` - розподіл по вакансіях та етапах
- ✅ `get_vacancy_statistics` - статистика вакансії

## Приклади використання

### Кандидат з однією вакансією
```python
candidate = {
    'id': 123,
    'name': 'Іван Петренко',
    'job_openings': [
        {'jobopening_id': 84, 'stage_id': 1}
    ]
}

# Результат:
# Вакансія: Python Developer (Middle)
# Етап: Нові кандидати
```

### Кандидат з кількома вакансіями
```python
candidate = {
    'id': 456,
    'name': 'Марія Коваль',
    'job_openings': [
        {'jobopening_id': 84, 'stage_id': 2},
        {'jobopening_id': 91, 'stage_id': 1}
    ]
}

# Отримуємо інформацію для конкретної вакансії
info = _get_vacancy_info_from_job_openings(candidate, vacancy_id=84)
# Вакансія: Python Developer (Middle)
# Етап: Первинна співбесіда

info = _get_vacancy_info_from_job_openings(candidate, vacancy_id=91)
# Вакансія: Frontend Developer
# Етап: Нові кандидати
```

### Кандидат без вакансій
```python
candidate = {
    'id': 789,
    'name': 'Петро Сидоренко',
    'job_openings': []
}

info = _get_vacancy_info_from_job_openings(candidate)
# Вакансія: Не вказано
# Етап: Не вказано
```

## Переваги нового підходу

### ✅ Точність
- Використовуємо реальну структуру даних з API
- Немає проблем з пустими полями `vacancy` та `stage`

### ✅ Гнучкість
- Підтримка кандидатів з кількома вакансіями
- Можливість фільтрації по конкретній вакансії

### ✅ Надійність
- Завжди отримуємо коректні дані
- Обробка випадків відсутності даних

## Тестування

Створено тести для перевірки:
- ✅ Парсинг `job_openings`
- ✅ Кандидати з кількома вакансіями
- ✅ Фільтрація по вакансії

```bash
python test_job_openings.py
```

Всі тести пройдено успішно! ✅

## Міграція

Всі методи оновлено автоматично. Потрібно лише:

1. Перезапустити бота
2. Очистити кеш командою `/clear_cache`
3. Перевірити звіти командами:
   - `/today` - денний звіт
   - `/vacancy_analytics` - аналітика вакансій

Всі дані тепер будуть відображатись коректно!
