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
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause