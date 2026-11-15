# Registers the NOVEXA Caddy HTTPS proxy at logon (hidden, keep-alive).
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$bat = Join-Path $root "run_caddy.bat"
$taskName = "NovexaCaddy"

if (-not (Test-Path $bat)) { throw "launcher missing: $bat" }

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument ('/c "' + $bat + '"') -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = "PT40S"

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force `
    -Description "NOVEXA Caddy reverse proxy - https://novexa.duckdns.org -> 127.0.0.1:8080" | Out-Null

Start-ScheduledTask -TaskName $taskName
"Registered: $taskName"
