# Removes the autostart task and stops the running bot engine.
$ErrorActionPreference = "Continue"
$taskName = "GulamaliBot24x7"

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue

Get-CimInstance Win32_Process -Filter "name = 'python.exe'" |
    Where-Object { $_.CommandLine -like "*main.py*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Get-CimInstance Win32_Process -Filter "name = 'cmd.exe'" |
    Where-Object { $_.CommandLine -like "*run_247_engine.bat*" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

"Removed task '$taskName' and stopped the bot."
