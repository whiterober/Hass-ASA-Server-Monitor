# ============================================================
# Install scheduled tasks: dino_backend + cloudflared tunnel (auto-start)
# Run as ADMIN PowerShell on Win Server 2019:
#   powershell -ExecutionPolicy Bypass -File D:\dino_backend\install_services.ps1
# ============================================================

$ErrorActionPreference = 'Stop'

Write-Host '=== Install dino backend + tunnel auto-start ==='

# ---------- 1. dino_backend.py ----------
$pyPath = (Get-Command python).Source
if (-not $pyPath) { Write-Host 'ERROR: python not found' -ForegroundColor Red; exit 1 }
$backendScript = 'D:\dino_backend\dino_backend.py'

Write-Host 'Create task: dino_backend' -ForegroundColor Cyan
$action1 = New-ScheduledTaskAction -Execute $pyPath -Argument "`"$backendScript`"" -WorkingDirectory 'D:\dino_backend'
$trigger1 = New-ScheduledTaskTrigger -AtStartup
$settings1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName 'dino_backend' -Action $action1 -Trigger $trigger1 -Settings $settings1 -Description 'ASA dino-import backend (RCON + data + static)' -Force
Start-ScheduledTask -TaskName 'dino_backend'
Write-Host '  OK: dino_backend registered & started' -ForegroundColor Green

# ---------- 2. cloudflared tunnel ----------
$cf = 'D:\dino_backend\cloudflared.exe'
if (-not (Test-Path $cf)) { Write-Host "WARN: $cf not found, skip tunnel task" -ForegroundColor Yellow }
else {
  Write-Host 'Create task: dino_tunnel' -ForegroundColor Cyan
  $action2 = New-ScheduledTaskAction -Execute $cf -Argument 'tunnel run dino-backend' -WorkingDirectory 'D:\dino_backend'
  $trigger2 = New-ScheduledTaskTrigger -AtStartup
  $settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
  Register-ScheduledTask -TaskName 'dino_tunnel' -Action $action2 -Trigger $trigger2 -Settings $settings2 -Description 'CF Tunnel: data.whiterober.ccwu.cc -> 127.0.0.1:8080' -Force
  Start-ScheduledTask -TaskName 'dino_tunnel'
  Write-Host '  OK: dino_tunnel registered & started' -ForegroundColor Green
}

Write-Host ''
Write-Host '=== Done. Verify: schtasks /query /tn dino_backend ==='
