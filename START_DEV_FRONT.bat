@echo off
REM ============================================================
REM   NEXUS9 - Frontend en mode DEV (Vite + HMR)
REM   Bypass Docker pour le frontend, plus rapide a iterer.
REM ============================================================
setlocal EnableDelayedExpansion
title NEXUS9 - Frontend DEV
color 0A
cd /d C:\OpenJarvisNexus\frontend

echo.
echo ============================================================
echo   NEXUS9 - Frontend Vite DEV mode
echo ============================================================
echo.

echo [1/5] Stop container nexus_frontend (libere le port 5173)...
docker compose stop frontend 2>nul
echo.

echo [2/5] Verifier que le backend tourne...
docker compose ps backend | findstr "Up" >nul 2>&1
if !errorlevel! neq 0 (
    echo   [INFO] Backend pas demarre, je le lance...
    docker compose up -d backend
    timeout /t 5 /nobreak >nul
) else (
    echo   [OK] Backend deja UP
)
echo.

echo [3/5] Verifier node_modules...
if not exist node_modules\.bin\vite (
    echo   [INFO] node_modules manquant ou casse, npm install...
    npm install --legacy-peer-deps --no-audit --no-fund
    if !errorlevel! neq 0 (
        echo   [ERREUR] npm install a echoue
        pause
        exit /b 1
    )
) else (
    echo   [OK] node_modules present
)
echo.

echo [4/5] Tuer eventuels process Node bloquants sur 5173/5174...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173" ^| findstr LISTENING') do (
    echo   Killing PID %%a
    taskkill /F /PID %%a 2>nul
)
echo.

echo [5/5] Demarrage Vite dev server avec HMR...
echo.
echo ============================================================
echo   Ouvre: http://localhost:5173
echo   API proxy: /v1 et /health pointent sur http://localhost:8000
echo   HMR actif - chaque modif src/ s'affiche en moins d'1s
echo   Ctrl+C ici pour stopper
echo ============================================================
echo.

call npm run dev

pause
endlocal
