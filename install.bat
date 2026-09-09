@echo off
title NEET Parser - Install
color 0B

echo.
echo  ============================================
echo   NEET Selection List Parser - Setup
echo  ============================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python is not installed or not in PATH.
    echo  Download it from: https://www.python.org/downloads/
    echo  Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version') do echo  [OK] Found %%i

:: Upgrade pip silently
echo  [..] Upgrading pip...
python -m pip install --upgrade pip --quiet
echo  [OK] pip is up to date

:: Install requirements
echo  [..] Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  [ERROR] Dependency installation failed.
    pause
    exit /b 1
)
echo  [OK] All dependencies installed

:: Create .env if missing
if not exist ".env" (
    echo MAX_UPLOAD_MB=500 > .env
    echo  [OK] Created .env with default settings
) else (
    echo  [OK] .env already exists
)

:: Configure git hooks
git config core.hooksPath .githooks
echo  [OK] Configured git hooksPath

echo.
echo  ============================================
echo   Setup complete! Run start.bat to launch.
echo  ============================================
echo.
pause
