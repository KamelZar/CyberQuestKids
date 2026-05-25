@echo off
REM ─────────────────────────────────────────────
REM  CyberQuest — Lancement Windows
REM  Usage :
REM    start_windows.bat           (= --start)
REM    start_windows.bat --start
REM    start_windows.bat --stop
REM    start_windows.bat --restart
REM ─────────────────────────────────────────────

set PORT=8080
set DASHBOARD=http://localhost:%PORT%/dashboard
set SCRIPT_DIR=%~dp0
set POSTER=http://localhost:%PORT%/init-poster
set PID_FILE=%SCRIPT_DIR%.cyberquest.pid

echo.
echo ╔══════════════════════════════════════════════╗
echo ║       CyberQuest — Démarrage Windows         ║
echo ╚══════════════════════════════════════════════╝
echo.

REM ── Lecture de l'argument ────────────────────
set ACTION=%1
if "%ACTION%"=="" set ACTION=--start

if "%ACTION%"=="--start"   goto DO_START
if "%ACTION%"=="--stop"    goto DO_STOP
if "%ACTION%"=="--restart" goto DO_RESTART

echo Usage: start_windows.bat [--start ^| --stop ^| --restart]
pause
exit /b 1

REM ── STOP (label + fonction appelable) ────────
:DO_STOP
call :DO_STOP_FN
goto END

:DO_STOP_FN
REM 1. Essaie via le fichier PID
if exist "%PID_FILE%" (
    set /p SAVED_PID=<"%PID_FILE%"
    tasklist /FI "PID eq %SAVED_PID%" 2>nul | find "%SAVED_PID%" >nul
    if not errorlevel 1 (
        echo 🛑 Serveur arrêté ^(PID %SAVED_PID%^)
        taskkill /PID %SAVED_PID% /F >nul 2>&1
    )
    del "%PID_FILE%"
)

REM 2. Filet de sécurité : tue tout process qui occupe le port (démarré manuellement)
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| find ":%PORT% "') do (
    if not "%%a"=="0" (
        echo 🛑 Process résiduel sur le port %PORT% tué ^(PID %%a^)
        taskkill /PID %%a /F >nul 2>&1
    )
)

echo ✅ Port %PORT% libéré
goto :EOF

REM ── RESTART ──────────────────────────────────
:DO_RESTART
call :DO_STOP_FN
timeout /t 1 /nobreak >nul
goto DO_START

REM ── START ─────────────────────────────────────
:DO_START
if exist "%PID_FILE%" (
    set /p SAVED_PID=<"%PID_FILE%"
    tasklist /FI "PID eq %SAVED_PID%" 2>nul | find "%SAVED_PID%" >nul
    if not errorlevel 1 (
        echo ⚠️  Le serveur tourne déjà ^(PID %SAVED_PID%^)
        echo    Utilise --restart pour le redémarrer
        pause
        exit /b 1
    )
)

REM Vérification Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python introuvable. Installe-le via https://python.org
    pause
    exit /b 1
)

REM Vérification Flask
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo ⚙️  Flask non installé - installation en cours...
    pip install flask
)

REM Démarrage Flask en arrière-plan
echo 🚀 Démarrage du serveur Flask sur le port %PORT%...
cd /d "%SCRIPT_DIR%"
start /B python server.py 2>"%SCRIPT_DIR%flask_error.log"

REM Récupération du PID via PowerShell (fiable, sans dépendance au titre de fenêtre)
timeout /t 1 /nobreak >nul
for /f %%i in ('powershell -NoProfile -Command "Get-Process python | Sort-Object StartTime -Descending | Select-Object -First 1 -ExpandProperty Id"') do (
    echo %%i> "%PID_FILE%"
    set SERVER_PID=%%i
)

REM Attente que Flask soit prêt
echo ⏳ En attente du serveur...
set TRIES=0
:WAIT_LOOP
    timeout /t 1 /nobreak >nul
    curl -s http://localhost:%PORT%/dashboard >nul 2>&1
    if not errorlevel 1 goto READY
    set /a TRIES+=1
    if %TRIES% lss 10 goto WAIT_LOOP

:READY
echo 🌐 Ouverture du dashboard et du poster...
start "" "%DASHBOARD%"
start "" "%POSTER%"

echo.
echo ✅ Serveur démarré ^(PID %SERVER_PID%^)
echo    Dashboard : %DASHBOARD%
echo    Arrêt     : start_windows.bat --stop
echo.

:END
pause
