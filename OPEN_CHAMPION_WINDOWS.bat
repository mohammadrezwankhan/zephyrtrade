@echo off
setlocal
if not exist "%~dp0ZephyrTrade-Champion.html" (
  echo Extract the complete ZIP before running this launcher.
  pause
  exit /b 1
)
start "" "%~dp0ZephyrTrade-Champion.html"
