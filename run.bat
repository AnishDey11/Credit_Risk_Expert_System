
@echo off
title Credit Risk Assessment System
cd /d "%~dp0"

echo ==========================================
echo      CREDIT RISK ASSESSMENT SYSTEM
echo ==========================================

REM Create virtual environment if missing
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install dependencies silently
echo Checking and installing dependencies...
python -m pip install --quiet --disable-pip-version-check --upgrade pip >nul 2>&1
python -m pip install --quiet --disable-pip-version-check -r requirements.txt >nul 2>&1

REM Start FastAPI server
echo.
echo Starting FastAPI server...
@REM  echo PC: http://127.0.0.1:8000
@REM  echo Mobile: http://192.168.29.79:8000
echo ==========================================

REM Automatically open browser after 3 seconds
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://127.0.0.1:8000/"

@REM  python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
python -m uvicorn app:app --reload

pause
