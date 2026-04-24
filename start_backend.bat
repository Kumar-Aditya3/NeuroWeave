@echo off
setlocal

REM Start NeuroWeave backend from repo root.
cd /d "%~dp0backend"

if "%NEUROWEAVE_API_KEYS%"=="" (
  set "NEUROWEAVE_API_KEYS=dev-local-key"
)

echo Starting NeuroWeave backend on http://127.0.0.1:8000
echo Using API key(s): %NEUROWEAVE_API_KEYS%
echo.

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
) else (
  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
)

endlocal
