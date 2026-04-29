@echo off
REM NeuroWeave All-in-One Launcher
REM This script starts both backend and desktop app together

setlocal enabledelayedexpansion

echo.
echo ============================================================
echo  NeuroWeave - Starting All Services
echo ============================================================
echo.

REM Check if venv exists
if not exist "backend\.venv" (
  echo ERROR: Virtual environment not found
  echo Please run setup_portable.bat first to initialize
  pause
  exit /b 1
)

REM Check if desktop exists
if not exist "desktop\dist\NeuroWeave.exe" (
  if not exist "desktop\dist\NeuroWeave Setup 0.1.0.exe" (
    echo ERROR: Desktop application not found
    echo Expected: desktop\dist\NeuroWeave.exe
    pause
    exit /b 1
  )
)

echo Starting services...
echo.

REM Start backend in a new window
echo [1/2] Starting backend server...
start "NeuroWeave Backend" cmd /k "%~dp0run_backend.bat"
timeout /t 3 /nobreak

REM Start desktop app
echo [2/2] Starting desktop application...
call "%~dp0run_desktop.bat"

echo.
echo ============================================================
echo  All services started!
echo ============================================================
echo.
echo Backend server is running in a separate window
echo Backend API: http://127.0.0.1:8000
echo API Docs:   http://127.0.0.1:8000/docs
echo.
echo Close the backend window to stop the server
echo.

endlocal
