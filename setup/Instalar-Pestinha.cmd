@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Instalar-Pestinha.ps1"
if errorlevel 1 (
  echo.
  echo A instalacao encontrou um problema. Veja a mensagem acima.
  pause
)
