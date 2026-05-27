<#
.SYNOPSIS
    Registers the Nexus9 FastAPI backend as a Windows service via NSSM.

.DESCRIPTION
    What this gives you that the Startup-folder shortcut doesn't:
      - Backend runs BEFORE you log in (boot-time, system account)
      - Survives logoffs and session disconnects
      - Auto-restarts on crash (NSSM default: throttled exponential backoff)
      - Stdout/stderr captured to rotating log files
      - Standard Windows service controls (sc query, net start/stop, Services.msc)

    Steps performed (idempotent -- safe to re-run):
      1. Self-elevate if not already running as admin.
      2. Install NSSM via winget if not present (one-time, ~300 KB download).
      3. Stop + remove any existing 'Nexus9-Backend' service.
      4. Register a fresh service pointing at the backend .venv uvicorn.
      5. Configure restart-on-failure + log rotation.
      6. Start the service.

.PARAMETER ServiceName
    Service identifier in Windows. Default: 'Nexus9-Backend'.

.PARAMETER Port
    TCP port for uvicorn. Default: 8000.

.PARAMETER NoStart
    Register the service but do not start it (useful if port 8000 is
    currently held by your dev uvicorn).

.EXAMPLE
    # Right-click "Run with PowerShell" -- or from any shell:
    .\Scripts\install-nexus9-service.ps1

.EXAMPLE
    # Register without starting (free port 8000 first):
    .\Scripts\install-nexus9-service.ps1 -NoStart

.NOTES
    To uninstall:    .\Scripts\uninstall-nexus9-service.ps1
    Logs:            C:\OpenJarvisNexus\backend\service-logs\nexus9-backend.{out,err}.log
    Service status:  sc query Nexus9-Backend
    Stop temporarily: net stop Nexus9-Backend
    Start again:      net start Nexus9-Backend
#>
[CmdletBinding()]
param(
    [string] $ServiceName = 'Nexus9-Backend',
    [int]    $Port        = 8000,
    [switch] $NoStart
)

$ErrorActionPreference = 'Stop'
$repoRoot   = 'C:\OpenJarvisNexus'
$backendDir = "$repoRoot\backend"
$venvPython = "$backendDir\.venv\Scripts\python.exe"
$logDir     = "$backendDir\service-logs"

# -- 1) Self-elevation ------------------------------------------------------

function Test-IsAdmin {
    $identity  = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    Write-Host "Re-launching elevated (UAC prompt incoming)..." -ForegroundColor Yellow
    $args = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', $PSCommandPath,
        '-ServiceName', $ServiceName,
        '-Port', $Port
    )
    if ($NoStart) { $args += '-NoStart' }
    Start-Process powershell.exe -ArgumentList $args -Verb RunAs
    exit
}

Write-Host "Running elevated as $env:USERNAME." -ForegroundColor Green
Write-Host ""

# -- 2) Sanity checks -------------------------------------------------------

if (-not (Test-Path $venvPython)) {
    Write-Error "Backend venv python not found at $venvPython. Run 'python -m venv backend\.venv' + install deps first."
    exit 1
}
if (-not (Test-Path "$backendDir\main.py")) {
    Write-Error "Backend main.py not found at $backendDir. Wrong repo path?"
    exit 1
}

# -- 3) Ensure NSSM is installed --------------------------------------------

$nssm = (Get-Command nssm -ErrorAction SilentlyContinue).Source
if (-not $nssm) {
    Write-Host "NSSM not found -- installing via winget..." -ForegroundColor Cyan
    & winget install --id NSSM.NSSM --silent --accept-source-agreements --accept-package-agreements
    if ($LASTEXITCODE -ne 0) {
        Write-Error "winget install NSSM.NSSM failed (exit $LASTEXITCODE). Install manually from https://nssm.cc/download and re-run."
        exit 1
    }
    # Refresh PATH in this session
    $env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' +
                [System.Environment]::GetEnvironmentVariable('Path','User')
    $nssm = (Get-Command nssm -ErrorAction SilentlyContinue).Source
    if (-not $nssm) {
        Write-Error "NSSM installed but not on PATH. Open a new shell and re-run, or add NSSM to PATH manually."
        exit 1
    }
}
Write-Host "NSSM at: $nssm" -ForegroundColor Green

# -- 4) Stop + remove existing service if any -------------------------------

$existing = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Existing '$ServiceName' service found -- stopping + removing for a clean reinstall..." -ForegroundColor Yellow
    if ($existing.Status -eq 'Running') {
        & $nssm stop $ServiceName | Out-Null
        Start-Sleep -Seconds 2
    }
    & $nssm remove $ServiceName confirm | Out-Null
    Start-Sleep -Seconds 1
}

# -- 5) Prepare log dir -----------------------------------------------------

if (-not (Test-Path $logDir)) {
    New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

# -- 6) Install + configure service -----------------------------------------

Write-Host "Registering service '$ServiceName'..." -ForegroundColor Cyan

# Core command line
& $nssm install $ServiceName $venvPython `
    "-m" "uvicorn" "main:app" `
    "--host" "0.0.0.0" "--port" "$Port"     | Out-Null

# Working directory (so relative paths in main.py work)
& $nssm set $ServiceName AppDirectory $backendDir | Out-Null

# Friendly display name + description
& $nssm set $ServiceName DisplayName 'Nexus9 Backend (FastAPI + APScheduler)' | Out-Null
& $nssm set $ServiceName Description ("Nexus9 personal AI stack backend. " +
    "Auto-restarts on crash. Logs to $logDir.") | Out-Null

# Startup type: automatic (boot)
& $nssm set $ServiceName Start SERVICE_AUTO_START | Out-Null

# Restart-on-failure: throttle 1.5s exponential backoff, max 30s
& $nssm set $ServiceName AppThrottle    1500  | Out-Null
& $nssm set $ServiceName AppExit Default Restart | Out-Null
& $nssm set $ServiceName AppRestartDelay 2000 | Out-Null

# Stdout / stderr -> log files with rotation
& $nssm set $ServiceName AppStdout       "$logDir\nexus9-backend.out.log" | Out-Null
& $nssm set $ServiceName AppStderr       "$logDir\nexus9-backend.err.log" | Out-Null
& $nssm set $ServiceName AppRotateFiles  1     | Out-Null     # enable rotation
& $nssm set $ServiceName AppRotateOnline 1     | Out-Null     # rotate while running
& $nssm set $ServiceName AppRotateBytes  10485760 | Out-Null  # 10 MB / file

# Environment variables -- uvicorn needs PYTHONUNBUFFERED for live log streaming
& $nssm set $ServiceName AppEnvironmentExtra `
    "PYTHONUNBUFFERED=1" `
    "PYTHONIOENCODING=utf-8" | Out-Null

# Graceful shutdown -- give uvicorn 15s to drain (default is too aggressive)
& $nssm set $ServiceName AppStopMethodConsole 15000 | Out-Null
& $nssm set $ServiceName AppStopMethodWindow  15000 | Out-Null
& $nssm set $ServiceName AppStopMethodThreads 15000 | Out-Null

Write-Host "Service registered." -ForegroundColor Green

# -- 7) Start (unless -NoStart) ---------------------------------------------

if ($NoStart) {
    Write-Host ""
    Write-Host "Service registered but NOT started (you passed -NoStart)." -ForegroundColor Yellow
    Write-Host "Free port $Port then run:   net start $ServiceName"
} else {
    Write-Host ""
    Write-Host "Starting service..." -ForegroundColor Cyan
    # If port 8000 is currently held by your dev uvicorn, NSSM start will
    # succeed at the service layer but uvicorn will crash repeatedly.
    # Best UX: warn first.
    $listener = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($listener) {
        Write-Warning ("Port $Port is currently held by PID $($listener.OwningProcess). " +
                       "The service will crash-loop until that process releases it. " +
                       "Stop your dev uvicorn first, or pass -NoStart to register without starting.")
    }
    & $nssm start $ServiceName | Out-Null
    Start-Sleep -Seconds 3
    $status = (Get-Service $ServiceName).Status
    if ($status -eq 'Running') {
        Write-Host "Service is RUNNING." -ForegroundColor Green
    } else {
        Write-Warning "Service status: $status -- check $logDir for clues."
    }
}

# -- 8) Final summary -------------------------------------------------------

Write-Host ""
Write-Host "============================================================"
Write-Host "  Nexus9 Backend Service installed"                  -ForegroundColor Green
Write-Host "============================================================"
Write-Host "  Service name : $ServiceName"
Write-Host "  Status       : $((Get-Service $ServiceName).Status)"
Write-Host "  Endpoint     : http://localhost:$Port"
Write-Host "  Logs         : $logDir\nexus9-backend.{out,err}.log"
Write-Host ""
Write-Host "  Controls:"
Write-Host "    net start $ServiceName        # start"
Write-Host "    net stop $ServiceName         # stop (15s graceful)"
Write-Host "    sc query $ServiceName         # status"
Write-Host "    Get-Service $ServiceName      # PowerShell status"
Write-Host "    services.msc                  # GUI"
Write-Host ""
Write-Host "  To uninstall:  .\Scripts\uninstall-nexus9-service.ps1"
Write-Host "============================================================"
Write-Host ""

# -- 9) Conflict warning: Startup-folder shortcut ---------------------------

$startupShortcut = "$([System.Environment]::GetFolderPath('Startup'))\Nexus9 (START_ALL).lnk"
if (Test-Path $startupShortcut) {
    Write-Warning ""
    Write-Warning "  Heads up: you also have a Startup-folder shortcut to START_ALL.bat:"
    Write-Warning "    $startupShortcut"
    Write-Warning ""
    Write-Warning "  At next login, START_ALL.bat will try to launch uvicorn on the SAME port -- they'll fight."
    Write-Warning "  Two options:"
    Write-Warning "    A) Delete the shortcut (service handles backend now):"
    Write-Warning "       Remove-Item '$startupShortcut'"
    Write-Warning "    B) Edit START_ALL.bat to skip the uvicorn step (keep it for Ollama + Vite + sidecar)."
    Write-Warning ""
}
