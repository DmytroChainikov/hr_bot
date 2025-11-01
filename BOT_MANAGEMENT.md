# 🤖 HR Analytics Bot - Управління

## Швидкий старт

### Windows:
```bash
# Запуск
start_bot.bat

# Зупинка
stop_bot.bat

# Перезапуск
restart_bot.bat
```

### Linux/Mac:
```bash
# Запуск
./start_bot.sh

# Зупинка
./stop_bot.sh
```

---

## Скрипти управління

### `start_bot.bat` / `start_bot.sh`
Запускає бота у фоновому режимі.
- Windows: відкриває окреме вікно
- Linux/Mac: запускає як фоновий процес

### `stop_bot.bat` / `stop_bot.sh`
Зупиняє ВСІ запущені копії бота.
- Безпечна зупинка всіх процесів
- Автоматична перевірка результату

### `restart_bot.bat`
Перезапускає бота (Windows):
1. Зупиняє старі копії
2. Чекає 3 секунди
3. Запускає нову копію

---

## Логи

Логи зберігаються у файлі: `logs/bot.log`

Переглянути останні записи:
```bash
# Windows (Git Bash)
tail -f logs/bot.log

# Windows (PowerShell)
Get-Content logs/bot.log -Tail 50 -Wait

# Linux/Mac
tail -f logs/bot.log
```

---

## Troubleshooting

### Помилка: "Conflict: terminated by other getUpdates"

**Причина:** Запущено кілька копій бота одночасно.

**Рішення:**
```bash
# Windows
stop_bot.bat

# Linux/Mac
./stop_bot.sh

# Перевірити чи всі зупинені
ps aux | grep "python.*main.py"
```

### Бот не стартує

1. Перевірте `.env` файл - всі ключі налаштовані?
2. Перевірте логи: `tail -n 50 logs/bot.log`
3. Запустіть вручну для діагностики:
   ```bash
   python main.py
   ```

### Schedulers не спрацьовують

Перевірте часовий пояс системи:
```bash
# Linux/Mac
date

# Windows
echo %date% %time%
```

Schedulers налаштовані на:
- **10:00** - Щоденні звіти по вакансіях
- **16:00** - Перевірка активності вакансій + неактивних топіків
- **18:00** - Денний звіт
- **19:00** - Перевірка звітів HR

---

## Структура системи

```
5 Schedulers активні:
├── Daily Vacancy Report (10:00)
├── Vacancy Activity Check (16:00)
├── Inactive Topics Check (16:00)
├── Daily Report (18:00)
└── HR Report Check (19:00)

Основні команди:
├── /vacancy_activity - Моніторинг активності
├── /inactive_vacancies - Неактивні вакансії
├── /vacancies_no_calls - Вакансії без дзвінків (кросс-аналіз)
├── /funnel_health - Здоров'я воронки
├── /track_changes - Зміни в етапах
└── + стандартні команди (/start, /help, тощо)
```

---

## Оновлення системи

```bash
# 1. Зупинити бота
stop_bot.bat

# 2. Оновити код
git pull

# 3. Встановити залежності (якщо потрібно)
pip install -r requirements.txt

# 4. Запустити знову
start_bot.bat
```

---

## Контакти підтримки

При проблемах перевірте:
1. Логи: `logs/bot.log`
2. Конфігурацію: `.env`
3. Статус API: Hurma, Binotel, Telegram

**Важливо:** Завжди використовуйте `stop_bot` перед запуском нової копії!
