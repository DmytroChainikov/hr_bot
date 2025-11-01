#!/bin/bash
# Скрипт для зупинки всіх копій бота

echo "Пошук запущених копій бота..."

# Для Windows (Git Bash/MinGW)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Використовуємо taskkill для Windows
    echo "Зупинка через taskkill..."
    taskkill //F //IM python.exe //FI "WINDOWTITLE eq *main.py*" 2>/dev/null
    
    # Альтернативно - через wmic
    for pid in $(wmic process where "commandline like '%main.py%' and name='python.exe'" get processid 2>/dev/null | grep -o '[0-9]\+'); do
        if [ ! -z "$pid" ]; then
            echo "Зупинка процесу $pid..."
            taskkill //F //PID $pid 2>/dev/null
        fi
    done
else
    # Для Linux/Mac
    pkill -f "python.*main.py" 2>/dev/null
fi

echo "Готово! Чекаємо 2 секунди..."
sleep 2

# Перевірка
if ps aux 2>/dev/null | grep -q "[p]ython.*main.py"; then
    echo "⚠️  Деякі процеси все ще працюють:"
    ps aux | grep "[p]ython.*main.py"
else
    echo "✅ Всі копії бота зупинено"
fi
