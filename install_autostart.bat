@echo off
title GULAMALI BOT - install 24/7 autostart
cd /d "%~dp0"
echo Installing boot autostart for GULAMALI ULTIMATE BOT...
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install_autostart.ps1"
echo.
pause
