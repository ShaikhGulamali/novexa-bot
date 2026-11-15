# Registers (or refreshes) the GulamaliBot24x7 scheduled task.
# Runs hidden at every logon, restarts the keep-alive engine if it dies,
# has no execution time limit, and starts late if the machine was off.

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$vbs = Join-Path $root "start_247_silent.vbs"
$taskName = "GulamaliBot24x7"

if (-not (Test-Path $vbs)) { throw "launcher missing: $vbs" }

$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument ('"' + $vbs + '"') -WorkingDirectory $root

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = "PT20S"

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -MultipleInstances IgnoreNew `
    -DisallowHardTerminate

$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force `
    -Description "GULAMALI ULTIMATE BOT + web dashboard (:8080) - 24/7 keep-alive" | Out-Null

Unregister-ScheduledTask -TaskName "GulamaliBot24x7-old" -Confirm:$false -ErrorAction SilentlyContinue

Start-ScheduledTask -TaskName $taskName

$info = Get-ScheduledTask -TaskName $taskName
"Registered: {0}  state={1}" -f $info.TaskName, $info.State
