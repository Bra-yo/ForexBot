@echo off
echo ========================================
echo    BrayoForexBot Trading Engine
echo ========================================
echo.
echo Starting independent trading engine...
echo This will run continuously in background
echo.
echo Press CTRL+C to stop the engine
echo.

REM Navigate to project directory
cd /d "C:\Users\ESSENCE\CascadeProjects\windsurf-project\dashboard"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Start the trading engine
echo 🚀 Launching Trading Engine...
echo.
python trading_engine.py

pause
