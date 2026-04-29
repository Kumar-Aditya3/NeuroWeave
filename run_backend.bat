@echo off
REM NeuroWeave Backend Launcher (Portable)
REM This script starts the backend using the portable virtual environment

setlocal enabledelayedexpansion

REM Check if venv exists
if not exist "backend\.venv" (
  echo ERROR: Virtual environment not found at backend\.venv
  echo Please run setup_portable.bat first
  pause
  exit /b 1
)

cd /d "%~dp0backend"

REM Activate virtual environment
call .venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
  echo ERROR: Failed to activate virtual environment
  pause
  exit /b 1
)

REM Set API key if not already set
if "%NEUROWEAVE_API_KEYS%"=="" (
  set "NEUROWEAVE_API_KEYS=dev-local-key"
)

echo.
echo ============================================================
echo  NeuroWeave Backend Server
echo ============================================================
echo.
echo Starting backend server...
echo.
echo Backend URL: http://127.0.0.1:8000
echo API Docs:   http://127.0.0.1:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.
echo ============================================================
echo.

REM Start the server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

endlocal
