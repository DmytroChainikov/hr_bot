@echo off
echo Starting HR Bot...
echo.

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

REM Check if .env exists
if not exist .env (
    echo .env file not found!
    echo Please copy .env.example to .env and configure it
    pause
    exit /b 1
)

REM Run the bot
python main.py

pause
