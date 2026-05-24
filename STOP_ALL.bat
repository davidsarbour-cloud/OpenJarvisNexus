@echo off
title NEXUS9 - ARRET SERVICES NATIFS
color 0C

echo.
echo  ==========================================
echo    NEXUS9 - ARRET DES SERVICES NATIFS
echo    (libere les ports pour Docker)
echo  ==========================================
echo.

REM -- Ferme les fenetres de terminal NEXUS9 --
echo [1/4] Fermeture des terminaux NEXUS9...
taskkill /F /FI "WINDOWTITLE eq NEXUS9 - Backend" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq NEXUS9 - Frontend" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq NEXUS9 - Vault Graph" >nul 2>&1
taskkill /F /FI "WINDOWTITLE eq NEXUS9 - Ollama" >nul 2>&1
echo   [OK]

REM -- Tue les processus par port --
echo [2/4] Liberation port 8000 (backend natif)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000.*LISTENING" 2^>nul') do (
    tasklist /FI "PID eq %%a" /NH 2>nul | findstr /V "docker\|vpnkit" >nul 2>&1
    if not errorlevel 1 ( taskkill /F /PID %%a >nul 2>&1 & echo   Tue PID %%a )
)
echo   [OK]

echo [3/4] Liberation port 5173 (frontend natif)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173.*LISTENING" 2^>nul') do (
    tasklist /FI "PID eq %%a" /NH 2>nul | findstr /V "docker\|vpnkit" >nul 2>&1
    if not errorlevel 1 ( taskkill /F /PID %%a >nul 2>&1 & echo   Tue PID %%a )
)
echo   [OK]

echo [4/4] Liberation port 11434 (ollama natif)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":11434.*LISTENING" 2^>nul') do (
    tasklist /FI "PID eq %%a" /NH 2>nul | findstr /V "docker\|vpnkit" >nul 2>&1
    if not errorlevel 1 ( taskkill /F /PID %%a >nul 2>&1 & echo   Tue PID %%a )
)
echo   [OK]

echo.
echo  ==========================================
echo    SERVICES NATIFS ARRETES
echo    Tu peux maintenant lancer Docker :
echo      docker compose up -d
echo    ou dire "ouvre docker" a JARVIS
echo  ==========================================
echo.
timeout /t 3 /nobreak >nul
