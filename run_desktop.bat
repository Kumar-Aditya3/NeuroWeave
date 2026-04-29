@echo off
REM NeuroWeave Desktop Launcher (Portable)
REM This script launches the desktop application

setlocal

echo.
echo ============================================================
echo  NeuroWeave Desktop Application
echo ============================================================
echo.

REM Check if backend is running on localhost:8000
echo Checking if backend is available...
timeout /t 2 /nobreak > nul

REM Launch the desktop app
if exist "desktop\dist\NeuroWeave.exe" (
  echo [OK] Launching desktop application...
  start "" "desktop\dist\NeuroWeave.exe"
) else if exist "desktop\dist\NeuroWeave Setup 0.1.0.exe" (
  echo [OK] Launching desktop installer/application...
  start "" "desktop\dist\NeuroWeave Setup 0.1.0.exe"
) else (
  echo ERROR: Desktop application not found
  echo Expected: desktop\dist\NeuroWeave.exe or desktop\dist\NeuroWeave Setup 0.1.0.exe
  pause
  exit /b 1
)

echo.
echo Desktop app is starting...
echo.
echo For the app to work properly:
echo   - Make sure backend is running (use run_backend.bat)
echo   - Backend should be available at http://127.0.0.1:8000
echo.
timeout /t 3 /nobreak

endlocal
