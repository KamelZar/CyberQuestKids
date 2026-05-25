@echo off
:: CyberQuestKids — Lanceur setup routeur
:: Usage :
::   setup_router.bat                → setup complet (defaut)
::   setup_router.bat --setup        → setup complet
::   setup_router.bat --forward      → active FORWARD DROP (captive portal)
::   setup_router.bat --passthrough  → coupe FORWARD DROP (internet retabli)
title CyberQuestKids -- Setup routeur

set MODE=%1
if "%MODE%"=="" set MODE=--setup

:: Verifier si on est admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Elevation des privileges necessaire...
    powershell -Command "Start-Process '%~f0' -ArgumentList '%MODE%' -Verb RunAs"
    exit /b
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_router.ps1" -Mode "%MODE%"
pause
