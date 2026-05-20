@echo off
title NEXUS9 v0.8 - JARVIS / ULTRON / QWEN / CORTANA / BRUCE / NOVA / FORGE
color 0A

echo.
echo  ==========================================
echo    NEXUS9 v0.8 - DEMARRAGE COMPLET
echo    JARVIS / ULTRON / QWEN / CORTANA / BRUCE / NOVA / FORGE
echo  ==========================================
echo.

REM -- [0/8] Docker Desktop --
echo [0/8] Verification Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker pas actif - demarrage Docker Desktop...
    start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    echo Attente Docker Desktop (30 secondes)...
    timeout /t 10 /nobreak >nul
    :wait_docker
    docker info >nul 2>&1
    if errorlevel 1 (
        timeout /t 5 /nobreak >nul
        goto :wait_docker
    )
    echo [OK] Docker Desktop pret
) else (
    echo [OK] Docker deja actif
)
echo.

REM -- [1/8] Nettoyage --
echo [1/8] Nettoyage des anciens processus...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul
timeout /t 2 /nobreak >nul
echo [OK] Processus tues
echo.

REM -- [2/8] Ollama --
echo [2/8] Demarrage Ollama (QWEN + CORTANA + NOVA)...
start "OLLAMA - Port 11434" /MIN cmd /c "C:\OpenJarvisNexus\1_OLLAMA.bat"
timeout /t 4 /nobreak >nul

REM -- [3/8] Backend JARVIS --
echo [3/8] Demarrage Backend FastAPI (JARVIS)...
start "BACKEND - Port 8000" cmd /c "C:\OpenJarvisNexus\2_BACKEND.bat"
timeout /t 4 /nobreak >nul

REM -- [4/8] Telegram --
echo [4/8] Demarrage Telegram Bot...
start "TELEGRAM - Jarvis Bot" cmd /c "C:\OpenJarvisNexus\4_TELEGRAM.bat"
timeout /t 2 /nobreak >nul

REM -- [5/8] BRUCE --
echo [5/8] Demarrage BRUCE (OpenHands + qwen3:14b)...
docker start nexus_bruce >nul 2>&1
if errorlevel 1 (
    echo Container BRUCE introuvable - creation...
    cd /d C:\OpenJarvisNexus
    docker compose up -d bruce >nul 2>&1
)
timeout /t 4 /nobreak >nul

REM -- [6/8] Obsidian Skills --
echo [6/8] Demarrage Obsidian Skills (port 8081)...
docker start obsidian-skills >nul 2>&1
if errorlevel 1 (
    echo Container introuvable - creation...
    docker run -d -p 8081:80 --name obsidian-skills obsidian-skills >nul 2>&1
)
echo [OK] Obsidian Skills :8081
timeout /t 2 /nobreak >nul

REM -- [7/8] Superpowers --
echo [7/8] Demarrage Superpowers (port 8082)...
docker start superpowers >nul 2>&1
if errorlevel 1 (
    echo Container introuvable - creation...
    docker run -d -p 8082:80 --name superpowers superpowers >nul 2>&1
)
echo [OK] Superpowers :8082
timeout /t 2 /nobreak >nul

REM -- [8/8] Checks --
echo [8/8] Verification des services...
timeout /t 5 /nobreak >nul

curl -s http://localhost:8000/health >nul && echo [OK] JARVIS          :8000  || echo [ERR] JARVIS offline
curl -s http://127.0.0.1:11434/api/tags >nul && echo [OK] Ollama          :11434 || echo [ERR] Ollama offline
curl -s http://localhost:3000/api/options/models >nul && echo [OK] BRUCE           :3000  || echo [WARN] BRUCE offline
curl -s http://localhost:8081 >nul && echo [OK] Obsidian Skills  :8081  || echo [ERR] Obsidian offline
curl -s http://localhost:8082 >nul && echo [OK] Superpowers      :8082  || echo [ERR] Superpowers offline

echo.
echo  ==========================================
echo    NEXUS9 v0.8 OPERATIONNEL
echo  ==========================================
echo  NEXUS9          -> http://localhost:8000/orbital
echo  BRUCE           -> http://localhost:3000
echo  Ollama          -> http://127.0.0.1:11434
echo  Obsidian Skills -> http://localhost:8081
echo  Superpowers     -> http://localhost:8082
echo  Telegram        -> Bot actif
echo  ==========================================
echo.

REM -- Ouverture apps + navigateurs --
timeout /t 2 /nobreak >nul

start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
timeout /t 1 /nobreak >nul

start "CRUSH AI - Terminal" cmd /k "C:\OpenJarvisNexus\5_CRUSH.bat"
timeout /t 1 /nobreak >nul

start "" http://localhost:8000/orbital
timeout /t 1 /nobreak >nul
start "" http://localhost:3000
timeout /t 1 /nobreak >nul
start "" http://localhost:8081
timeout /t 1 /nobreak >nul
start "" http://localhost:8082
timeout /t 1 /nobreak >nul
start "" https://www.meshy.ai/workspace?page=landing^&sidebar=assets
timeout /t 1 /nobreak >nul

REM -- Morning Routine JARVIS --
echo [OK] Morning Routine JARVIS...
timeout /t 3 /nobreak >nul
curl -s -X POST http://localhost:8000/v1/system/morning-routine >nul && echo [OK] Morning Routine lancee || echo [WARN] Morning Routine - backend pas pret

echo.
echo Tous les services sont prets. Bonne session David!
timeout /t 3 /nobreak >nul
