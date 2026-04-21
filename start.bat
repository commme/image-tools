@echo off
REM ─────────────────────────────────────────────────
REM  Image Tools — 1-Click Launcher (Windows)
REM ─────────────────────────────────────────────────
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo  Image Tools - Starting up...
echo.

REM Check Python
where py >nul 2>nul
if errorlevel 1 (
  echo  [ERROR] Python is not installed.
  echo  Download from https://python.org and try again.
  pause
  exit /b 1
)

REM Install dependencies (idempotent — safe to run every time)
echo  Installing dependencies (first run takes a few minutes)...
py -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo  [ERROR] Dependency installation failed.
  pause
  exit /b 1
)

REM Open browser after 2 seconds
start "" cmd /c "timeout /t 2 >nul && start http://localhost:5001"

REM Run server
echo.
echo  Server starting at http://localhost:5001
echo  Press Ctrl+C to stop.
echo.
py web.py
pause
