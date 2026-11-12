@echo off
title QSPARK Smart Parking System (Flask + SQLite)
cd /d "%~dp0"

echo ========================================================
echo   Starting QSPARK Smart Parking System...
echo ========================================================

:: Check if virtual environment exists
if not exist ".venv\Scripts\python.exe" (
    echo Virtual environment not found. Creating one...
    python -m venv .venv
)

:: Install dependencies
.\.venv\Scripts\python.exe -m pip install -r requirements.txt >nul 2>&1

:: Set environment for development
set APP_ENV=development
set SECRET_KEY=change_me_in_production

:: Launch default browser after 2 seconds
start /b "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:5000/login'"

:: Run the Flask application using the project's virtual environment
:: For production, run: .\.venv\Scripts\waitress-serve.exe --listen=0.0.0.0:8000 --call app:create_app
.\.venv\Scripts\python.exe run.py

pause