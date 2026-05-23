@echo off
title NEXUS9 — DEMARRAGE COMPLET
color 0A

echo.
echo  ==========================================
echo    NEXUS9 — DEMARRAGE COMPLET
echo    JARVIS / ULTRON / BRUCE / QWEN / CORTANA
echo  ==========================================
echo.

REM -- [1/4] Docker Desktop --
echo [1/4] Verification Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker pas actif - demarrage...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Attente Docker Desktop...
    :wait_docker
    timeout /t 5 /nobreak >nul
    docker info >nul 2>&1
    if errorlevel 1 goto :wait_docker
    echo [OK] Docker Desktop pret
) else (
    echo [OK] Docker deja actif
)
echo.

REM -- [2/4] Docker Compose --
echo [2/4] Demarrage de tous les services...
cd /d C:\OpenJarvisNexus
docker compose up -d >nul 2>&1
echo [OK] Conteneurs lances
echo.

REM -- [3/4] Attente backend --
echo [3/4] Attente backend...
:wait_backend
timeout /t 3 /nobreak >nul
curl -s http://localhost:8000/health >nul 2>&1
if errorlevel 1 goto :wait_backend
echo [OK] Backend pret
echo.

REM -- [3.5/4] Vault Graph sidecar --
echo [3.5/4] Demarrage Vault Graph sidecar (port 8084)...
start "NEXUS9 - Vault Graph" powershell -NoExit -ExecutionPolicy Bypass -File "C:\OpenJarvisNexus\services\vault_graph\start.ps1"
timeout /t 2 /nobreak >nul
echo [OK] Vault Graph sidecar lance dans sa fenetre
echo.

REM -- [3.7/4] Frontend Vite dev (HMR, source maps, modifs live) --
echo [3.7/4] Demarrage Vite dev (frontend)...
start "NEXUS9 - Vite Dev" powershell -NoExit -ExecutionPolicy Bypass -Command "cd C:\OpenJarvisNexus\frontend; npm run dev"
timeout /t 5 /nobreak >nul
echo [OK] Vite lance dans sa fenetre - regarde le port Local: dans son terminal
echo.

REM -- [4/4] Checks --
echo [4/4] Verification des services...
curl -s http://localhost:8000/health >nul  && echo [OK] Backend        :8000  || echo [ERR] Backend offline
curl -s http://localhost:5173        >nul  && echo [OK] Frontend       :5173  || echo [ERR] Frontend offline
curl -s http://localhost:11434       >nul  && echo [OK] Ollama         :11434 || echo [ERR] Ollama offline
curl -s http://localhost:3000        >nul  && echo [OK] BRUCE          :3000  || echo [WARN] BRUCE offline
curl -s http://localhost:8081        >nul  && echo [OK] Obsidian       :8081  || echo [ERR] Obsidian offline
curl -s http://localhost:8082        >nul  && echo [OK] Superpowers    :8082  || echo [ERR] Superpowers offline
curl -s -o nul http://localhost:8084       && echo [OK] Vault Graph    :8084  || echo [WARN] Vault Graph en cours...
curl -s http://localhost:3001        >nul  && echo [OK] Grafana        :3001  || echo [ERR] Grafana offline
curl -s http://localhost:9090        >nul  && echo [OK] Prometheus     :9090  || echo [ERR] Prometheus offline
curl -s http://localhost:9000        >nul  && echo [OK] SonarQube      :9000  || echo [WARN] SonarQube en cours...

echo.
echo  ==========================================
echo    NEXUS9 OPERATIONNEL
echo  ==========================================
echo  Nexus9 UI      -> http://localhost:5173
echo  Orbital        -> http://localhost:8000/orbital
echo  Vault Graph    -> ws://localhost:8084 (clic planete VAULT)
echo  Meshy AI       -> https://www.meshy.ai
echo.
echo  Autres services accessibles via JARVIS HTML :
echo    BRUCE :3000  Obsidian :8081  Superpowers :8082
echo    Grafana :3001  Prometheus :9090  SonarQube :9000
echo  ==========================================
echo.

REM -- Ouverture navigateur (Nexus9 UI + Orbital + Meshy) --
REM -- BRUCE/Obsidian/Superpowers/Grafana/Prometheus/SonarQube accessibles depuis JARVIS HTML --
timeout /t 2 /nobreak >nul
start "" http://localhost:5173
timeout /t 1 /nobreak >nul
start "" http://localhost:8000/orbital
timeout /t 1 /nobreak >nul
start "" https://www.meshy.ai/workspace?page=landing^&sidebar=assets

REM -- Morning Routine JARVIS --
echo.
echo [*] Morning Routine JARVIS...
timeout /t 2 /nobreak >nul
curl -s -X POST http://localhost:8000/v1/system/morning-routine >nul 2>&1
if errorlevel 1 (echo [WARN] Morning Routine - reessaie plus tard) else (echo [OK] Morning Routine lancee)

echo.
echo Bonne session David!
timeout /t 3 /nobreak >nul
