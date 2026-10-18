@echo off
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Create the project .venv and install requirements-dev.txt first. See README.md.
  pause
  exit /b 1
)
echo FraudMesh final preview: http://127.0.0.1:8018/?scenario=ring^&scope=local
echo Keep this window open. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -B -m uvicorn app.main:app --host 127.0.0.1 --port 8018
pause
