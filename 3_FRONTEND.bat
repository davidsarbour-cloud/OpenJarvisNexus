@echo off
title [FRONTEND] Vite - Port 5174
color 0D
cd /d C:\OpenJarvisNexus\nexusx9

REM Tuer ce qui bloque le port 5173/5174
echo Nettoyage des ports...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173"') do taskkill /F /PID %%a 2>nul
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5174"') do taskkill /F /PID %%a 2>nul
timeout /t 2 /nobreak >nul

npm run dev
pause