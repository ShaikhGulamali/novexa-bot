# Registers the NovexaRenderPing task: hits the Render health URL every 10 minutes
# so the free web service never idles long enough to spin down.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$ping = Join-Path $root "scripts\render_ping.ps1"
$taskName = "NovexaRenderPing"

if (-not (Test-Path $ping)) { throw "ping script missing: $ping" }

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "' + $ping + '"') `
    -WorkingDirectory $root

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = "PT1M"

$repeat = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes 10) `
    -RepetitionDuration (New-TimeSpan -Days 3650)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger @($trigger, $repeat) `
    -Settings $settings -Principal $principal -Force `
    -Description "Pings novexa-bot-eu.onrender.com/health every 10 min to keep the free Render service awake" | Out-Null

Start-ScheduledTask -TaskName $taskName
Start-Sleep -Seconds 8

$info = Get-ScheduledTask -TaskName $taskName
"Registered: {0}  state={1}" -f $info.TaskName, $info.State
