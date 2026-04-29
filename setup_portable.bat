@echo off
REM NeuroWeave Portable Setup Script
REM Run this once on the target machine to initialize the environment
REM After this, use run_backend.bat and run_desktop.bat

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo  NeuroWeave Portable Installation
echo ============================================================
echo.

REM Check if Python is available
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
  echo ERROR: Python 3.9+ not found in PATH
  echo Please install Python from https://www.python.org
  echo Make sure to check "Add Python to PATH" during installation
  pause
  exit /b 1
)

REM Get Python version
for /f "tokens=2" %%I in ('python --version') do set PYTHON_VERSION=%%I
echo [OK] Python %PYTHON_VERSION% found

REM Create virtual environment in backend folder
echo.
echo Creating virtual environment in backend\.venv...
cd /d "%~dp0backend"
if exist .venv (
  echo [SKIP] Virtual environment already exists at backend\.venv
) else (
  python -m venv .venv
  if %ERRORLEVEL% neq 0 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
  )
  echo [OK] Virtual environment created
)

REM Activate venv and install dependencies
echo.
echo Installing dependencies...
call .venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
  echo ERROR: Failed to activate virtual environment
  pause
  exit /b 1
)

python -m pip install --upgrade pip -q
python -m pip install -r requirements.txt
if %ERRORLEVEL% neq 0 (
  echo ERROR: Failed to install dependencies
  pause
  exit /b 1
)
echo [OK] Dependencies installed

REM Initialize database if needed
echo.
echo Checking database initialization...
if not exist "data.db" (
  echo Creating SQLite database...
  python -c "import sqlite3; sqlite3.connect('data.db').executescript(open('sql/schema.sql').read())"
  if %ERRORLEVEL% neq 0 (
    echo [WARN] Database initialization may have issues, but backend can create it dynamically
  ) else (
    echo [OK] Database initialized
  )
)

echo.
echo ============================================================
echo  Setup Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Double-click run_backend.bat to start the backend server
echo   2. Double-click run_desktop.bat to launch the desktop app
echo   3. Backend will be available at http://127.0.0.1:8000
echo.
pause
endlocal
