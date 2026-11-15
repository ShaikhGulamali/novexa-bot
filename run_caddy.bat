@echo off
REM ============================================================
REM  GULAMALI - Caddy HTTPS reverse proxy keep-alive
REM  novexa.duckdns.org  ->  http://127.0.0.1:8080
REM ============================================================
title NOVEXA Caddy HTTPS
cd /d "%~dp0"
set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"
if not exist "%ROOT%\logs" mkdir "%ROOT%\logs"

:loop
if not exist "%ROOT%\caddy.exe" (
    echo [%date% %time%] caddy.exe missing >> "%ROOT%\logs\caddy.log"
    timeout /t 60 /nobreak >nul
    goto loop
)

echo [%date% %time%] starting caddy >> "%ROOT%\logs\caddy.log"
"%ROOT%\caddy.exe" run --config "%ROOT%\Caddyfile" --adapter caddyfile >> "%ROOT%\logs\caddy.log" 2>&1
echo [%date% %time%] caddy exited - restart in 10s >> "%ROOT%\logs\caddy.log"
timeout /t 10 /nobreak >nul
goto loop
