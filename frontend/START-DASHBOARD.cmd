@echo off
setlocal
cd /d "%~dp0"
where node >nul 2>nul
if not errorlevel 1 (
  node server.mjs
  exit /b
)
set "FRAUDMESH_NODE=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
if exist "%FRAUDMESH_NODE%" (
  "%FRAUDMESH_NODE%" server.mjs
  exit /b
)
echo Node.js was not found. Install Node.js 18 or newer, or run:
echo python -m http.server 4173 --bind 127.0.0.1
pause
