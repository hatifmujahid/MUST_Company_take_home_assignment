@echo off
cd /d "%~dp0"

if not exist ".venv" (
    echo Setup hasn't been run yet. Double-click setup.bat first.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"
set "PYTHONPATH=%~dp0src;%PYTHONPATH%"

python -m ap_os run
echo.
pause
