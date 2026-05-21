@echo off
:: CyberQuestKids — Lanceur setup routeur (double-clic)
:: Demande l'elevation admin si necessaire (requis pour netsh portproxy)
title CyberQuestKids -- Setup routeur

:: Verifier si on est admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Elevation des privileges necessaire...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_router.ps1"
pause
