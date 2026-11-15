@echo off
REM Run this ONCE as Administrator (right click -> Run as administrator).
REM Opens the Windows Firewall for the web dashboard (8080) and HTTPS proxy (80/443).
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Administrator rights required.
    echo Right click this file and choose "Run as administrator".
    pause
    exit /b 1
)

netsh advfirewall firewall delete rule name="NOVEXA HTTP 80" >nul 2>&1
netsh advfirewall firewall delete rule name="NOVEXA HTTPS 443" >nul 2>&1
netsh advfirewall firewall delete rule name="NOVEXA Dashboard 8080" >nul 2>&1

netsh advfirewall firewall add rule name="NOVEXA HTTP 80" dir=in action=allow protocol=TCP localport=80
netsh advfirewall firewall add rule name="NOVEXA HTTPS 443" dir=in action=allow protocol=TCP localport=443
netsh advfirewall firewall add rule name="NOVEXA Dashboard 8080" dir=in action=allow protocol=TCP localport=8080

echo.
echo Firewall rules installed for ports 80, 443 and 8080.
pause
