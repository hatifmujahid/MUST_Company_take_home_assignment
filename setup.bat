@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo === AP Exception Autopilot - one-time setup ===
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python was not found on this computer.
    echo Please install Python 3.10+ from https://www.python.org/downloads/ and run this again.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Creating a local virtual environment...
    python -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo Installing dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

if not exist ".env" (
    echo.
    set /p APIKEY="Paste your Anthropic API key (from console.anthropic.com) and press Enter: "
    echo ANTHROPIC_API_KEY=!APIKEY!> .env
    echo Saved to .env
)

if not exist "config.yaml" (
    copy /y "config.example.yaml" "config.yaml" >nul
)

for %%F in (pos receipts approvers chart_of_accounts) do (
    if not exist "data\%%F.csv" (
        if exist "data\%%F.example.csv" copy /y "data\%%F.example.csv" "data\%%F.csv" >nul
    )
)

echo.
echo Setup complete. Drop invoice files into the "inbox" folder, then double-click run.bat.
pause
