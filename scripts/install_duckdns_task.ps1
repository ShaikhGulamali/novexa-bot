# Registers the DuckDNS IP updater to run every 5 minutes.
# schtasks is used because Register-ScheduledTask needs elevation on this box.

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$script = Join-Path $PSScriptRoot "duckdns_update.py"

$candidates = @(
    (Join-Path $env:LOCALAPPDATA "Python\pythoncore-3.15-64\pythonw.exe"),
    "C:\Program Files\Python311\pythonw.exe",
    "C:\Program Files\Python312\pythonw.exe",
    "C:\Program Files\Python313\pythonw.exe"
)

$python = $null
foreach ($candidate in $candidates) {
    if (Test-Path $candidate) { $python = $candidate; break }
}
if (-not $python) {
    $python = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
}
if (-not $python) { throw "No pythonw.exe interpreter found." }
if (-not (Test-Path $script)) { throw "Updater script missing: $script" }

$taskName = "NovexaDuckDNS"
$action = "`"$python`" `"$script`""

$ErrorActionPreference = "Continue"
schtasks.exe /Delete /TN $taskName /F 2>&1 | Out-Null
$output = schtasks.exe /Create /TN $taskName /TR $action /SC MINUTE /MO 5 /IT /RL LIMITED /F 2>&1
Write-Host $output

schtasks.exe /Run /TN $taskName | Out-Null
Start-Sleep -Seconds 8

$query = schtasks.exe /Query /TN $taskName /V /FO LIST 2>&1
$query | Select-String -Pattern "Status|Last Result|Last Run|Task To Run" | ForEach-Object {
    Write-Host $_.Line.Trim()
}

$log = Join-Path $root "logs\duckdns.log"
if (Test-Path $log) {
    Write-Host "--- logs\duckdns.log (last 3) ---"
    Get-Content $log -Tail 3
}
