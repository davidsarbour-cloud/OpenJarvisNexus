@echo off
title NEXUS9 — Crush AI (local)
echo.
echo  ╔══════════════════════════════════════════════╗
echo  ║   NEXUS9  —  CRUSH AI  (natif Windows)       ║
echo  ║   Providers : Ollama local (zero API key)    ║
echo  ║   Models    : qwen3:14b / deepseek-r1:7b     ║
echo  ╚══════════════════════════════════════════════╝
echo.

:: Chemin direct WinGet (pas besoin que PATH soit rechargé)
set CRUSH_EXE=%LOCALAPPDATA%\Microsoft\WinGet\Packages\charmbracelet.crush_Microsoft.Winget.Source_8wekyb3d8bbwe\crush_0.69.1_Windows_x86_64\crush.exe
if not exist "%CRUSH_EXE%" (
    :: Fallback PATH système
    where crush >nul 2>&1
    if %errorlevel%==0 (
        set CRUSH_EXE=crush
    ) else (
        echo [ERREUR] crush.exe introuvable.
        echo Installe avec : winget install charmbracelet.crush
        pause
        exit /b 1
    )
)

:launch
:: Vérifie Ollama
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel%==0 (
    echo [OK] Ollama tourne sur :11434
) else (
    echo [WARN] Ollama offline - lance 1_OLLAMA.bat d'abord
)
echo.
echo [*] Lancement Crush dans ce terminal...
echo     Modele par defaut : qwen3:14b
echo     Switch model      : Ctrl+M
echo     Quit              : Ctrl+C
echo.

:: Lance Crush dans le dossier Nexus9
cd /d C:\OpenJarvisNexus
"%CRUSH_EXE%"
