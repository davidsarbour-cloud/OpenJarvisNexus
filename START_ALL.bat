@echo off
title NEXUS9 - DEMARRAGE
color 0A

set "ROOT=C:\OpenJarvisNexus"
set "PYTHON=%ROOT%\backend\.venv\Scripts\python.exe"
REM UTF-8 stdout pour les fenetres enfant (evite UnicodeEncodeError emojis en console cp1252)
set "PYTHONIOENCODING=utf-8"

echo.
echo  ==========================================
echo    NEXUS9 - DEMARRAGE (natif)
echo    JARVIS / ULTRON / QWEN / CORTANA / FORGE
echo  ==========================================
echo.

REM -- [1/4] Ollama natif (port 11434) --
echo [1/4] Ollama (natif)...
curl -s http://127.0.0.1:11434/api/version >nul 2>&1
if not errorlevel 1 ( echo   [OK] Ollama deja lance & goto ollama_ok )
echo   Demarrage d'Ollama...
start "NEXUS9 - Ollama" /min ollama serve
set /a t=0
:wait_ollama
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:11434/api/version >nul 2>&1
if not errorlevel 1 ( echo   [OK] Ollama pret & goto ollama_ok )
set /a t+=1
if %t% lss 15 goto wait_ollama
echo   [WARN] Ollama ne repond pas - verifie l'install
:ollama_ok
echo.

REM -- [2/4] Backend FastAPI (uvicorn natif, port 8000) --
echo [2/4] Backend FastAPI...
start "NEXUS9 - Backend" cmd /k "cd /d %ROOT%\backend && %PYTHON% -m uvicorn main:app --port 8000"
set /a t=0
:wait_backend
timeout /t 2 /nobreak >nul
curl -s http://127.0.0.1:8000/health >nul 2>&1
if not errorlevel 1 ( echo   [OK] Backend pret & goto backend_ok )
set /a t+=1
if %t% lss 30 goto wait_backend
echo   [WARN] Backend timeout - voir la fenetre "NEXUS9 - Backend"
:backend_ok
echo.

REM -- [3/4] Vault Graph sidecar (node, port 8084) --
echo [3/4] Vault Graph sidecar...
start "NEXUS9 - Vault Graph" powershell -NoExit -ExecutionPolicy Bypass -File "%ROOT%\services\vault_graph\start.ps1"
echo   [OK] Vault Graph lance dans sa fenetre
echo.

REM -- [4/4] Frontend Vite dev (port 5173) --
echo [4/4] Frontend Vite (HMR)...
start "NEXUS9 - Frontend" cmd /k "cd /d %ROOT%\frontend && npm run dev"
set /a t=0
:wait_frontend
timeout /t 2 /nobreak >nul
curl -s http://localhost:5173 >nul 2>&1
if not errorlevel 1 ( echo   [OK] Frontend pret & goto frontend_ok )
set /a t+=1
if %t% lss 20 goto wait_frontend
echo   [WARN] Frontend timeout - voir la fenetre "NEXUS9 - Frontend"
:frontend_ok
echo.

echo  ==========================================
echo    NEXUS9 OPERATIONNEL
echo  ==========================================
echo    UI        -^> http://localhost:5173
echo    Backend   -^> http://localhost:8000/health
echo    Ollama    -^> http://localhost:11434
echo    VaultGraph-^> ws://localhost:8084
echo  ==========================================
echo.
echo  Services optionnels (docker, si besoin) :
echo    docker compose --profile quality up -d      ^(sonarqube^)
echo    docker compose --profile agents up -d       ^(telegram/bruce^)
echo.

timeout /t 2 /nobreak >nul
start "" http://localhost:5173

echo Bonne session David!
timeout /t 3 /nobreak >nul
