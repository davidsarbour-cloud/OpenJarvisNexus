# Nexus9 - vault_graph sidecar launcher
# Tue tout process sur le port du sidecar, set VAULT_PATH, demarre le serveur.

$ErrorActionPreference = 'Stop'

$port = if ($env:VAULT_GRAPH_PORT) { [int]$env:VAULT_GRAPH_PORT } else { 8084 }

Write-Host "[start.ps1] killing anything on port $port ..." -ForegroundColor Cyan
$conns = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($conns) {
    $conns | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        try {
            Stop-Process -Id $_ -Force -ErrorAction Stop
            Write-Host "  killed PID $_" -ForegroundColor Yellow
        } catch {
            Write-Host "  cannot kill PID $_ (Access denied - lance ce terminal en Administrateur si besoin)" -ForegroundColor Red
        }
    }
    Start-Sleep -Milliseconds 500
} else {
    Write-Host '  (port libre)' -ForegroundColor DarkGray
}

# On force toujours le path de la vault Obsidian BRAIN. Pour utiliser un
# autre path, edite cette ligne ci-dessous.
$env:VAULT_PATH = 'C:\OpenJarvisNexus\backend\BRAIN\BRAIN'

Write-Host "[start.ps1] VAULT_PATH      = $env:VAULT_PATH" -ForegroundColor Cyan
Write-Host "[start.ps1] VAULT_GRAPH_PORT = $port" -ForegroundColor Cyan
Write-Host '[start.ps1] starting sidecar (Ctrl+C pour arreter)' -ForegroundColor Cyan
Write-Host ''

Set-Location -LiteralPath $PSScriptRoot
npm start
