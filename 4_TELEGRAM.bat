@echo off
title [TELEGRAM] Jarvis Bot
color 0D
echo ============================================
echo    JARVIS TELEGRAM BOT
echo    Token: depuis .env
echo ============================================

cd /d C:\OpenJarvisNexus\backend

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    echo [OK] Venv backend active
) else (
    call ..\venv\Scripts\activate.bat
    echo [OK] Venv racine active
)

echo.
echo Lancement du bot Telegram...
echo Envoie /start a ton bot pour commencer.
echo.

python telegram_bot.py
pause
