@echo off
REM ════════════════════════════════════════════════════════
REM Nexus9 — Lance un scan SonarQube (version CMD)
REM ════════════════════════════════════════════════════════
REM Avant de lancer :
REM   1. Le container nexus_sonarqube doit etre UP (http://localhost:9000)
REM   2. Generer un token dans SonarQube UI
REM   3. set SONAR_TOKEN=sqp_xxxxx
REM   4. run_sonar.bat
REM ════════════════════════════════════════════════════════

if "%SONAR_TOKEN%"=="" (
    echo SONAR_TOKEN non defini.
    echo Genere un token dans http://localhost:9000 ^(My Account -^> Security^)
    echo Puis : set SONAR_TOKEN=sqp_xxxxxxxxxxxxxxxxxxx
    exit /b 1
)

echo Test SonarQube...
curl -sf http://localhost:9000/api/system/status >nul
if errorlevel 1 (
    echo SonarQube inaccessible. Lance: docker compose up -d sonarqube
    exit /b 1
)

echo Lancement du scanner...
docker run --rm ^
    --network host ^
    -e SONAR_HOST_URL=http://localhost:9000 ^
    -e SONAR_TOKEN=%SONAR_TOKEN% ^
    -v "%cd%:/usr/src" ^
    sonarsource/sonar-scanner-cli:latest

if errorlevel 0 (
    echo.
    echo Scan termine.
    echo Resultats : http://localhost:9000/dashboard?id=Nexus9
)
