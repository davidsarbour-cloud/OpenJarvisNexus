<#
.SYNOPSIS
    Removes the Nexus9-Backend Windows service installed by
    install-nexus9-service.ps1. Idempotent.

.NOTES
    Self-elevates if not running as admin.
#>
[CmdletBinding()]
param([string] $ServiceName = 'Nexus9-Backend')

$ErrorActionPreference = 'Stop'

function Test-IsAdmin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    return ([Security.Principal.WindowsPrincipal]::new($id)).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-IsAdmin)) {
    Write-Host "Re-launching elevated (UAC prompt incoming)..." -ForegroundColor Yellow
    Start-Process powershell.exe -Verb RunAs -ArgumentList @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass',
        '-File', $PSCommandPath,
        '-ServiceName', $ServiceName
    )
    exit
}

$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if (-not $svc) {
    Write-Host "No service named '$ServiceName' is registered. Nothing to do." -ForegroundColor Yellow
    exit 0
}

$nssm = (Get-Command nssm -ErrorAction SilentlyContinue).Source
if (-not $nssm) {
    Write-Warning "NSSM not on PATH. Falling back to native sc.exe -- the service will be removed but NSSM-specific config will linger."
}

if ($svc.Status -eq 'Running') {
    Write-Host "Stopping '$ServiceName' (15s grace)..." -ForegroundColor Cyan
    if ($nssm) {
        & $nssm stop $ServiceName | Out-Null
    } else {
        Stop-Service -Name $ServiceName -Force
    }
    Start-Sleep -Seconds 2
}

Write-Host "Removing service '$ServiceName'..." -ForegroundColor Cyan
if ($nssm) {
    & $nssm remove $ServiceName confirm | Out-Null
} else {
    & sc.exe delete $ServiceName | Out-Null
}

Start-Sleep -Seconds 1
$check = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($check) {
    Write-Warning "Service still present -- may need a reboot to fully release."
} else {
    Write-Host "Service '$ServiceName' removed." -ForegroundColor Green
    Write-Host ""
    Write-Host "Logs are still on disk at:"
    Write-Host "  C:\OpenJarvisNexus\backend\service-logs\"
    Write-Host "  (Delete manually if you don't want them anymore.)"
}
