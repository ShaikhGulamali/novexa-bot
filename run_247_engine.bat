@echo off
REM ============================================================
REM  GULAMALI ULTIMATE BOT - 24/7 keep-alive engine
REM  Restarts the bot (and its built-in web dashboard on :8080)
REM  whenever it exits, forever, hidden.
REM ============================================================
title GULAMALI ULTIMATE BOT - 24/7 Engine
cd /d "%~dp0"

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"
set "LOG=%ROOT%\logs\engine.log"

REM --- resolve interpreter -------------------------------------
set "PY=%BOT_PYTHON%"
if not defined PY if exist "%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe" set "PY=%LOCALAPPDATA%\Python\pythoncore-3.15-64\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PY for /f "delims=" %%i in ('where python 2^>nul') do if not defined PY set "PY=%%i"

if not defined PY (
    echo [%date% %time%] FATAL: no python interpreter found >> "%LOG%"
    exit /b 1
)

echo. >> "%LOG%"
echo ============================================================ >> "%LOG%"
echo [%date% %time%] engine start  python="%PY%"  root="%ROOT%" >> "%LOG%"

:loop
REM main.py holds a LISTEN lock on 127.0.0.1:49288 while alive.
netstat -ano | findstr /c:":49288" | findstr /i "LISTENING" >nul 2>&1
if not errorlevel 1 (
    timeout /t 60 /nobreak >nul
    goto loop
)

echo [%date% %time%] launching bot >> "%LOG%"
"%PY%" -u main.py >> "%LOG%" 2>&1
set "CODE=%errorlevel%"
echo [%date% %time%] bot exited with code %CODE% - restarting in 15s >> "%LOG%"
timeout /t 15 /nobreak >nul
goto loop
