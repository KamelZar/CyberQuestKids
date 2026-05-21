@echo off
:: CyberQuestKids — Lanceur setup routeur (double-clic)
:: Appelle setup_router.ps1 avec bypass de la politique d'execution PowerShell
title CyberQuestKids — Setup routeur
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_router.ps1"
pause
