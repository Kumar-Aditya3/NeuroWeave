@echo off
setlocal

cd /d "%~dp0.."

echo Building NeuroWeave portable agent executable...

python -m pip install --upgrade pip >nul
python -m pip install pyinstaller psutil >nul

pyinstaller --noconfirm --clean --onefile --name neuroweave_portable_agent portable_agent\portable_agent.py

if %ERRORLEVEL% neq 0 (
  echo Build failed.
  exit /b 1
)

echo.
echo Build complete.
echo EXE: dist\neuroweave_portable_agent.exe
echo Copy these files together to keep it portable:
echo - dist\neuroweave_portable_agent.exe
echo - portable_agent\portable_agent.config.json (generated on first run)

endlocal
