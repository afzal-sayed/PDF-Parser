@echo off
title NEET Parser - Server
color 0A

echo.
echo  ============================================
echo   NEET Selection List Parser
echo  ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found. Run install.bat first.
    pause
    exit /b 1
)

:: Check Flask is installed
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Dependencies missing. Run install.bat first.
    pause
    exit /b 1
)

echo  [OK] Starting server...
echo.
echo  ============================================
echo   App is running at: http://127.0.0.1:5000
echo   Press Ctrl+C to stop the server
echo  ============================================
echo.

:: Open browser after a short delay (runs in background)
start "" cmd /c "timeout /t 2 >nul && start http://127.0.0.1:5000"

:: Start Flask
python app.py
