@echo off
REM ============================================================
REM   NEXUS9 - Rebuild script tout-en-un (Phase 4)
REM   Stop + Build --no-cache + Force-recreate + Audit
REM ============================================================
setlocal EnableDelayedExpansion
title NEXUS9 - Rebuild
color 0B
cd /d C:\OpenJarvisNexus

echo.
echo ============================================================
echo   NEXUS9 - REBUILD COMPLET (backend + frontend)
echo ============================================================
echo.

REM ----- Verification rapide des fix sur disque -----
echo [1/6] Verification des fix sur disque...
echo.

set "OK_FRONT=0"
set "OK_BACK=0"

findstr /C:"minHeight={30}" frontend\src\components\Layout\BottomPanel.tsx >nul 2>&1
if !errorlevel! equ 0 (
    echo   [OK]  Fix recharts minHeight
    set /a OK_FRONT+=1
) else (
    echo   [KO]  Fix recharts manquant
)

if exist frontend\src\systems\serviceRegistry.ts (
    echo   [OK]  systems\serviceRegistry.ts
    set /a OK_FRONT+=1
) else (
    echo   [KO]  systems\serviceRegistry.ts manquant
)

if exist frontend\src\pages\AgentNetworkPage.tsx (
    echo   [OK]  AgentNetworkPage.tsx
    set /a OK_FRONT+=1
) else (
    echo   [KO]  AgentNetworkPage.tsx manquant
)

findstr /C:"'.html'" backend\main.py >nul 2>&1
if !errorlevel! equ 0 (
    echo   [OK]  Fix backend .html
    set /a OK_BACK+=1
) else (
    echo   [KO]  Fix backend .html manquant
)

findstr /C:"@app.get(\"/v1/info\")" backend\main.py >nul 2>&1
if !errorlevel! equ 0 (
    echo   [OK]  Endpoint /v1/info
    set /a OK_BACK+=1
) else (
    echo   [KO]  Endpoint /v1/info manquant
)

findstr /C:"@app.get(\"/v1/connectors\")" backend\main.py >nul 2>&1
if !errorlevel! equ 0 (
    echo   [OK]  Endpoint /v1/connectors
    set /a OK_BACK+=1
) else (
    echo   [KO]  Endpoint /v1/connectors manquant
)

echo.
echo   Front: !OK_FRONT!/3   Back: !OK_BACK!/3
echo.

if !OK_FRONT! lss 3 (
    echo [STOP] Des fix front manquent sur disque. Stop ici.
    pause
    exit /b 1
)
if !OK_BACK! lss 3 (
    echo [STOP] Des fix back manquent sur disque. Stop ici.
    pause
    exit /b 1
)

echo.
echo [2/6] Stop containers backend + frontend...
docker compose stop backend frontend
echo.

echo [3/6] Build --no-cache backend (5-10 min)...
docker compose build --no-cache backend
if !errorlevel! neq 0 (
    echo [ERREUR] Build backend a echoue. Stop.
    pause
    exit /b 1
)
echo.

echo [4/6] Build --no-cache frontend (3-5 min)...
docker compose build frontend
if !errorlevel! neq 0 (
    echo [ERREUR] Build frontend a echoue. Stop.
    pause
    exit /b 1
)
echo.

echo [5/6] Force-recreate containers...
docker compose up -d --force-recreate backend frontend
echo.

echo [6/6] Verification post-rebuild...
echo.
timeout /t 4 /nobreak >nul

echo --- Status containers ---
docker compose ps backend frontend
echo.

echo --- Backend: extension .html dans l'image ---
docker compose exec -T backend grep "'.html'" /app/main.py
echo.

echo --- Backend: endpoints /v1/info + /v1/connectors ---
docker compose exec -T backend grep -E "/v1/info|/v1/connectors" /app/main.py
echo.

echo --- Frontend: bundle contient minHeight:30 ---
docker compose exec -T frontend sh -c "grep -o 'minHeight:30' /usr/share/nginx/html/assets/*.js | wc -l"
echo.

echo --- Frontend: bundle contient AgentNetwork ---
docker compose exec -T frontend sh -c "grep -o 'AgentNetwork\|TacticalOverlay\|AlertBanner' /usr/share/nginx/html/assets/*.js | sort -u | head -10"
echo.

echo --- Frontend: hash des nouveaux bundles JS ---
docker compose exec -T frontend sh -c "ls /usr/share/nginx/html/assets/*.js | head -5"
echo.

echo ============================================================
echo   REBUILD TERMINE
echo ============================================================
echo.
echo  Maintenant dans le navigateur :
echo  1. F12 -^> Application -^> Storage -^> Clear site data
echo  2. Ctrl+Shift+R (hard refresh)
echo.
echo  Tu dois voir dans la sidebar gauche : une nouvelle section
echo  VIEWS avec Command Center / Orbital View / Agent Network
echo.
pause
endlocal
