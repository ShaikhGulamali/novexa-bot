@echo off
title GULAMALI ULTIMATE BOT - Localhost Live Server
color 0b
echo ========================================================
echo        STARTING GULAMALI ULTIMATE BOT (LOCAL HOST)
echo ========================================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

:: Change to script directory
cd /d "%~dp0"

echo [1/3] Terminating any old zombie bot instances...
powershell -Command "Get-WmiObject Win32_Process -Filter \"name = 'python.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' -and $_.ProcessId -ne $PID } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo [2/3] Checking dependencies...
python -m pip install -r requirements.txt --quiet

echo [3/3] Starting Bot and Localhost Dashboard (http://localhost:8080)...
echo.
echo ========================================================
echo  * Localhost Live Dashboard: http://localhost:8080
echo  * Press Ctrl+C in this window anytime to stop the bot
echo ========================================================
echo.

:: Launch browser in 3 seconds to open dashboard
start "" powershell -Command "Start-Sleep -Seconds 3; Start-Process 'http://localhost:8080'"

python main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Bot stopped or encountered an error.
    pause
)
