<#
.SYNOPSIS
    Nexus9 DX cache cleanup -- purges stale build artifacts, temp files and
    old snapshots safely. Idempotent. Dry-run by default.

.DESCRIPTION
    Targets (all paths are bounded, no recursive surprises):
      - $env:TEMP\*                 older than 14 days
      - $env:LOCALAPPDATA\Temp\*    older than 14 days
      - C:\OpenJarvisNexus\frontend\node_modules\.vite\ (always purged -- regenerates)
      - C:\OpenJarvisNexus\frontend\src-tauri\target\debug\ older than 7 days
      - C:\OpenJarvisNexus\backend\trend_snapshots\*.json older than 30 days
      - C:\OpenJarvisNexus\.jscpd-report\ (regenerated on each pre-commit)
      - C:\OpenJarvisNexus\.gitleaks-report.json (regenerated on demand)
      - C:\OpenJarvisNexus\backend\__pycache__\ (recursive .pyc cleanup)
      - $env:LOCALAPPDATA\pip\Cache\http older than 30 days

    NOT touched (you'll have to do manually if you really want):
      - node_modules/   -- full reinstall is annoying
      - .venv/          -- full reinstall takes minutes
      - %TEMP%\Chrome*, %TEMP%\Edge* -- your browser session cookies
      - Docker volumes  -- has your chromadb data

.PARAMETER Apply
    Without -Apply, the script runs in dry-run mode and only prints what
    WOULD be deleted. Pass -Apply to actually delete.

.PARAMETER TempMaxAgeDays
    Override the "older than N days" threshold for $env:TEMP. Default 14.

.PARAMETER Verbose
    Standard PowerShell -Verbose. Streams the path of each item handled.

.EXAMPLE
    # Preview only (default -- safe, no deletes):
    .\Scripts\dx-cache-cleanup.ps1

.EXAMPLE
    # Actually delete:
    .\Scripts\dx-cache-cleanup.ps1 -Apply

.EXAMPLE
    # Apply + chatty:
    .\Scripts\dx-cache-cleanup.ps1 -Apply -Verbose

.NOTES
    Author: Nexus9 / David Arbour
    Schedule via Task Scheduler (one-time setup): see -RegisterTask block
    at the bottom of this file for the exact command.
#>
[CmdletBinding()]
param(
    [switch] $Apply,
    [int]    $TempMaxAgeDays      = 14,
    [int]    $TauriMaxAgeDays     = 7,
    [int]    $SnapshotMaxAgeDays  = 30,
    [int]    $PipCacheMaxAgeDays  = 30
)

$ErrorActionPreference = 'Stop'
$repoRoot = 'C:\OpenJarvisNexus'

if (-not $Apply) {
    Write-Host "`n[DRY RUN] Pass -Apply to actually delete. Showing what would be cleaned:`n" -ForegroundColor Yellow
}

# -- Helpers -----------------------------------------------------------------

function Get-DiskUsageMB {
    param([string] $Path)
    if (-not (Test-Path $Path)) { return 0 }
    try {
        $bytes = (Get-ChildItem -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue |
            Measure-Object -Property Length -Sum).Sum
        if ($null -eq $bytes) { return 0 }
        return [math]::Round($bytes / 1MB, 1)
    } catch { return 0 }
}

function Remove-StaleItems {
    param(
        [string] $Path,
        [int]    $MaxAgeDays,
        [string] $Label
    )
    if (-not (Test-Path $Path)) {
        Write-Host ("  {0,-50} : path missing, skip" -f $Label) -ForegroundColor DarkGray
        return @{ Count = 0; SizeMB = 0 }
    }
    $cutoff = (Get-Date).AddDays(-$MaxAgeDays)
    $items = Get-ChildItem -LiteralPath $Path -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.LastWriteTime -lt $cutoff }
    $sizeMB = 0
    foreach ($it in $items) {
        try {
            $b = (Get-ChildItem -LiteralPath $it.FullName -Recurse -Force -ErrorAction SilentlyContinue |
                Measure-Object Length -Sum).Sum
            if ($b) { $sizeMB += $b / 1MB }
        } catch { }
    }
    $sizeMB = [math]::Round($sizeMB, 1)
    Write-Host ("  {0,-50} : {1,5} items, {2,8} MB (older than {3}d)" -f $Label, $items.Count, $sizeMB, $MaxAgeDays)
    if ($Apply -and $items.Count -gt 0) {
        foreach ($it in $items) {
            try {
                Remove-Item -LiteralPath $it.FullName -Recurse -Force -ErrorAction SilentlyContinue
                Write-Verbose "  deleted: $($it.FullName)"
            } catch {
                Write-Verbose "  skip (locked): $($it.FullName)"
            }
        }
    }
    return @{ Count = $items.Count; SizeMB = $sizeMB }
}

function Remove-Wholesale {
    param([string] $Path, [string] $Label)
    if (-not (Test-Path $Path)) {
        Write-Host ("  {0,-50} : not present, skip" -f $Label) -ForegroundColor DarkGray
        return @{ SizeMB = 0 }
    }
    $sizeMB = Get-DiskUsageMB -Path $Path
    Write-Host ("  {0,-50} : wholesale purge, {1,8} MB" -f $Label, $sizeMB)
    if ($Apply -and $sizeMB -gt 0) {
        try {
            Remove-Item -LiteralPath $Path -Recurse -Force -ErrorAction SilentlyContinue
            Write-Verbose "  deleted: $Path"
        } catch {
            Write-Warning "  could not delete $Path : $($_.Exception.Message)"
        }
    }
    return @{ SizeMB = $sizeMB }
}

# -- Targets -----------------------------------------------------------------

Write-Host "-- Aged temp / build caches --------------------------------"
$report = @()
$report += Remove-StaleItems -Path $env:TEMP                                                      -MaxAgeDays $TempMaxAgeDays     -Label '$env:TEMP'
$report += Remove-StaleItems -Path "$env:LOCALAPPDATA\Temp"                                       -MaxAgeDays $TempMaxAgeDays     -Label '$env:LOCALAPPDATA\Temp'
$report += Remove-StaleItems -Path "$repoRoot\frontend\src-tauri\target\debug"                    -MaxAgeDays $TauriMaxAgeDays    -Label 'Tauri debug/'
$report += Remove-StaleItems -Path "$repoRoot\backend\trend_snapshots"                            -MaxAgeDays $SnapshotMaxAgeDays -Label 'backend\trend_snapshots\'
$report += Remove-StaleItems -Path "$env:LOCALAPPDATA\pip\Cache\http"                             -MaxAgeDays $PipCacheMaxAgeDays -Label 'pip http cache'

Write-Host "`n-- Wholesale purges (regenerated on next dev/build) -------"
$wReport = @()
$wReport += Remove-Wholesale -Path "$repoRoot\frontend\node_modules\.vite"                        -Label 'Vite cache (.vite/)'
$wReport += Remove-Wholesale -Path "$repoRoot\.jscpd-report"                                      -Label '.jscpd-report/'
$wReport += Remove-Wholesale -Path "$repoRoot\.gitleaks-report.json"                              -Label '.gitleaks-report.json'

# .pyc files (recursive -- bytecode regenerated on next import)
Write-Host "`n-- Python bytecode (__pycache__) --------------------------"
$pycaches = Get-ChildItem -LiteralPath "$repoRoot\backend" -Filter '__pycache__' -Recurse -Directory -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -notlike '*\.venv\*' }
$pycSizeMB = 0
foreach ($d in $pycaches) {
    $b = (Get-ChildItem -LiteralPath $d.FullName -Recurse -Force -ErrorAction SilentlyContinue |
        Measure-Object Length -Sum).Sum
    if ($b) { $pycSizeMB += $b / 1MB }
}
$pycSizeMB = [math]::Round($pycSizeMB, 1)
Write-Host ("  {0,-50} : {1,5} dirs, {2,8} MB" -f 'backend\**\__pycache__\', $pycaches.Count, $pycSizeMB)
if ($Apply -and $pycaches.Count -gt 0) {
    foreach ($d in $pycaches) {
        try { Remove-Item -LiteralPath $d.FullName -Recurse -Force -ErrorAction SilentlyContinue }
        catch { Write-Verbose "  skip: $($d.FullName)" }
    }
}

# -- Summary -----------------------------------------------------------------

$totalAged    = ($report  | ForEach-Object { $_.SizeMB } | Measure-Object -Sum).Sum
$totalWhole   = ($wReport | ForEach-Object { $_.SizeMB } | Measure-Object -Sum).Sum
if ($null -eq $totalAged)  { $totalAged  = 0 }
if ($null -eq $totalWhole) { $totalWhole = 0 }
$grandTotalMB = [math]::Round($totalAged + $totalWhole + $pycSizeMB, 1)

Write-Host "`n--------------------------------------------------------------"
$verb = if ($Apply) { 'RECOVERED' } else { 'WOULD RECOVER' }
Write-Host ("  TOTAL {0}: {1} MB" -f $verb, $grandTotalMB) -ForegroundColor Green
Write-Host "--------------------------------------------------------------`n"

if (-not $Apply) {
    Write-Host "Re-run with -Apply to actually delete.`n" -ForegroundColor Yellow
}

<#
.LINK
    One-time Task Scheduler registration (run elevated PowerShell, once):

    $action  = New-ScheduledTaskAction `
        -Execute 'powershell.exe' `
        -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\OpenJarvisNexus\Scripts\dx-cache-cleanup.ps1" -Apply'
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 21:00
    $settings = New-ScheduledTaskSettingsSet `
        -StartWhenAvailable -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
        -RestartCount 0
    Register-ScheduledTask `
        -TaskName 'Nexus9 DX cache cleanup' `
        -Description 'Weekly purge of stale build artifacts (Vite cache, Tauri debug, pip http, temp).' `
        -Action $action -Trigger $trigger -Settings $settings `
        -RunLevel Limited -Force

    To remove later:
        Unregister-ScheduledTask -TaskName 'Nexus9 DX cache cleanup' -Confirm:$false
#>
