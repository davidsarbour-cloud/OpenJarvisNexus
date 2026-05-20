# ============================================
# START_NEXUSX9.ps1 — Lanceur Unifié NexusX9
# ============================================

$ROOT = "C:\OpenJarvisNexus"
$FRONTEND = "C:\OpenJarvisNexus\nexusx9"

Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║     🌌 NexusX9 — DÉMARRAGE NEXUS     ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# --- TERMINAL 1 : OLLAMA ---
Write-Host "🪐 [1/3] Démarrage OLLAMA..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& {
        `$host.UI.RawUI.WindowTitle = '🟠 OLLAMA - qwen3:14b';
        Write-Host '=== OLLAMA SERVER ===' -ForegroundColor Yellow;
        `$env:OLLAMA_HOST = '0.0.0.0:11434';
        ollama serve
    }"
)

Start-Sleep -Seconds 3

# --- TERMINAL 2 : BACKEND FASTAPI ---
Write-Host "⚙️  [2/3] Démarrage BACKEND FastAPI..." -ForegroundColor Blue
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& {
        `$host.UI.RawUI.WindowTitle = '🔵 BACKEND - FastAPI :8000';
        Write-Host '=== BACKEND FASTAPI ===' -ForegroundColor Blue;
        Set-Location '$ROOT';
        & '$ROOT\.venv\Scripts\Activate.ps1';
        Write-Host 'Venv activé ✅' -ForegroundColor Green;
        python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
    }"
)

Start-Sleep -Seconds 2

# --- TERMINAL 3 : FRONTEND VITE ---
Write-Host "🎨 [3/3] Démarrage FRONTEND Vite..." -ForegroundColor Magenta
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "& {
        `$host.UI.RawUI.WindowTitle = '🟣 FRONTEND - Vite :5173';
        Write-Host '=== FRONTEND VITE ===' -ForegroundColor Magenta;
        Set-Location '$FRONTEND';
        npm run dev
    }"
)

Start-Sleep -Seconds 3

# --- VÉRIFICATION FINALE ---
Write-Host ""
Write-Host "╔══════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║         ✅ NEXUSX9 LANCÉ !            ║" -ForegroundColor Green
Write-Host "╠══════════════════════════════════════╣" -ForegroundColor Green
Write-Host "║  🟠 Ollama   → localhost:11434        ║" -ForegroundColor Yellow
Write-Host "║  🔵 Backend  → localhost:8000         ║" -ForegroundColor Blue  
Write-Host "║  🟣 Frontend → localhost:5173         ║" -ForegroundColor Magenta
Write-Host "╚══════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

# Test automatique après 5 secondes
Start-Sleep -Seconds 5
Write-Host "🔍 Test des services..." -ForegroundColor Cyan

try {
    $backend = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 3
    Write-Host "  ✅ Backend  : OK ($($backend.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Backend  : ÉCHEC - Vérifier terminal bleu" -ForegroundColor Red
}

try {
    $ollama = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 3
    Write-Host "  ✅ Ollama   : OK (qwen3:14b détecté)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ Ollama   : ÉCHEC - Vérifier terminal orange" -ForegroundColor Red
}

Write-Host ""
Write-Host "Frontend → Ouvrir: http://localhost:5173" -ForegroundColor Cyan
Read-Host "Appuyer sur Entrée pour fermer ce lanceur"