@echo off
REM Скрипт для перезапуску HR бота

echo ========================================
echo HR Analytics Bot - RESTART
echo ========================================
echo.

REM 1. Зупинка старих копій
echo [1/3] Зупинка старих копій бота...
call stop_bot.bat

echo.
echo [2/3] Чекаємо 3 секунди...
timeout /t 3 /nobreak >nul

REM 2. Запуск нової копії
echo.
echo [3/3] Запуск бота...
echo.
start "HR Analytics Bot" python main.py

echo.
echo ========================================
echo Бот запущено в окремому вікні!
echo ========================================
pause
