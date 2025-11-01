@echo off
REM Скрипт для зупинки всіх копій HR бота

echo Пошук запущених копій бота...

REM Зупинка через taskkill
echo Зупинка процесів Python з main.py...
taskkill /F /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq *main.py*" 2>nul

REM Зупинка через wmic (більш надійно)
for /f "tokens=2" %%a in ('wmic process where "commandline like '%%main.py%%' and name='python.exe'" get processid ^| findstr [0-9]') do (
    echo Зупинка процесу %%a...
    taskkill /F /PID %%a 2>nul
)

echo.
echo Чекаємо 2 секунди...
timeout /t 2 /nobreak >nul

echo.
echo Готово! Всі копії бота зупинено.

