# Keeps the free Render web service from sleeping after 15 minutes idle.
# Render spins the container down on inactivity, which drops the Discord gateway,
# so the bot only stays connected while something keeps poking /health.

$url = "https://novexa-bot-eu.onrender.com/health"
$log = Join-Path (Split-Path -Parent $PSScriptRoot) "logs\render_ping.log"

try {
    $r = Invoke-WebRequest -Uri $url -TimeoutSec 90 -UseBasicParsing
    $line = "{0} {1} {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $r.StatusCode, $r.Content
} catch {
    $line = "{0} FAIL {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $_.Exception.Message
}

$dir = Split-Path -Parent $log
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
Add-Content -Path $log -Value $line -Encoding UTF8

# keep the log from growing forever
$content = Get-Content -Path $log -ErrorAction SilentlyContinue
if ($content -and $content.Count -gt 500) {
    $content | Select-Object -Last 200 | Set-Content -Path $log -Encoding UTF8
}
