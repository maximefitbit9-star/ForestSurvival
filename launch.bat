@echo off
REM Ninety-Nine Nights in the Wildwood - launcher
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH. Install Python 3.11+ from python.org and retry.
    pause
    exit /b 1
)
python main.py
pause
