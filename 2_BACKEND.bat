@echo off
title [BACKEND] FastAPI - Port 8000
color 0B
echo ============================================
echo    BACKEND FastAPI - Port 8000
echo    Dossier: C:\OpenJarvisNexus\backend
echo ============================================

cd /d C:\OpenJarvisNexus\backend

REM Activer le bon venv (celui dans backend/)
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [OK] Venv backend active
) else (
    call ..\venv\Scripts\activate.bat
    echo [OK] Venv racine active
)

echo.
echo Lancement uvicorn depuis: %CD%
echo.

REM IMPORTANT: main:app PAS backend.main:app
REM UTF-8 stdout — évite UnicodeEncodeError sur les emojis dans les logs (console cp1252)
set PYTHONIOENCODING=utf-8
REM Chemin venv EXPLICITE (pas `python` nu) — garantit Kokoro/rembg même si
REM l'activate a échoué ou si le PATH pointe sur le python système.
set "PYTHON=C:\OpenJarvisNexus\backend\.venv\Scripts\python.exe"
REM Tuer un backend fantôme sur :8000 avant de relancer
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
"%PYTHON%" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause