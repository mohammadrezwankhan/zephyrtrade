@echo off
setlocal
pushd "%~dp0" || exit /b 1
echo ZephyrTrade Champion - optional local Python research server
echo The first setup downloads Python packages. No trades are submitted.
if exist ".venv-champion\Scripts\python.exe" goto check_package
where py >nul 2>nul
if not errorlevel 1 (
  set "BASE_PY=py -3"
) else (
  set "BASE_PY=python"
)
%BASE_PY% -c "import sys;sys.exit(0 if sys.version_info >= (3,11) else 1)"
if errorlevel 1 (
  echo Install Python 3.11 or newer, then run this file again.
  echo The portable ZephyrTrade-Champion.html does not need Python.
  goto failed
)
%BASE_PY% -m venv .venv-champion
if errorlevel 1 goto failed
:check_package
".venv-champion\Scripts\python.exe" -c "import zephyrtrade.app" >nul 2>nul
if not errorlevel 1 goto launch
".venv-champion\Scripts\python.exe" -m pip install -e .
if errorlevel 1 goto failed
:launch
echo Starting on http://127.0.0.1:8765 . Keep this window open.
".venv-champion\Scripts\python.exe" -m zephyrtrade.app
if errorlevel 1 goto failed
popd
exit /b 0
:failed
echo Setup or startup did not complete. The error above has not been suppressed.
echo Read README.md for manual setup and alternate port instructions.
pause
popd
exit /b 1
