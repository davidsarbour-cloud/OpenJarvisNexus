# ════════════════════════════════════════════════════════
# Nexus9 — Lance un scan SonarQube
# ════════════════════════════════════════════════════════
# Prérequis :
#   1. Le container nexus_sonarqube doit tourner (http://localhost:9000)
#   2. SonarQube doit être healthy (peut prendre 2-3 min au boot)
#   3. Génère un token : http://localhost:9000 → My Account → Security → Generate Token
#   4. Mets-le dans la variable d'env SONAR_TOKEN avant de lancer ce script :
#        $env:SONAR_TOKEN = "sqp_xxxxxxxxxxxxxxxxxxx"
#
# Usage :
#   .\run_sonar.ps1
# ════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"

# Vérif token
if (-not $env:SONAR_TOKEN) {
    Write-Host "❌ SONAR_TOKEN non défini." -ForegroundColor Red
    Write-Host ""
    Write-Host "Génère un token dans SonarQube :" -ForegroundColor Yellow
    Write-Host "  1. Ouvre http://localhost:9000 (login: admin / pass: admin si neuf)" -ForegroundColor Yellow
    Write-Host "  2. My Account → Security → Generate Token" -ForegroundColor Yellow
    Write-Host "  3. \$env:SONAR_TOKEN = `"sqp_xxxxxxxxxxxxx`"" -ForegroundColor Yellow
    Write-Host "  4. Relance ce script" -ForegroundColor Yellow
    exit 1
}

# Vérif SonarQube up
Write-Host "→ Test SonarQube..." -ForegroundColor Cyan
try {
    $resp = Invoke-WebRequest -Uri "http://localhost:9000/api/system/status" -TimeoutSec 5 -UseBasicParsing
    $status = ($resp.Content | ConvertFrom-Json).status
    if ($status -ne "UP") {
        Write-Host "⚠ SonarQube state = $status (attendre qu'il soit UP avant de relancer)" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "  ✓ SonarQube UP" -ForegroundColor Green
} catch {
    Write-Host "❌ SonarQube inaccessible. Lance: docker compose up -d sonarqube" -ForegroundColor Red
    exit 1
}

# Lance le scanner via Docker (pas besoin d'installer sonar-scanner localement)
Write-Host "→ Lancement du scanner..." -ForegroundColor Cyan

# Détecter l'adresse de host.docker.internal pour le scanner Docker → SonarQube Docker
$sonarHostUrl = "http://host.docker.internal:9000"

docker run --rm `
    --network host `
    -e SONAR_HOST_URL=http://localhost:9000 `
    -e SONAR_TOKEN=$env:SONAR_TOKEN `
    -v "${PSScriptRoot}:/usr/src" `
    sonarsource/sonar-scanner-cli:latest

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Scan terminé." -ForegroundColor Green
    Write-Host "  Résultats : http://localhost:9000/dashboard?id=Nexus9" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "❌ Scan échoué (exit $LASTEXITCODE)" -ForegroundColor Red
}
