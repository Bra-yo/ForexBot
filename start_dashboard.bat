@echo off
echo ========================================
echo    BrayoForexBot Dashboard UI
echo ========================================
echo.
echo Starting dashboard interface...
echo This will open in your browser
echo.
echo NOTE: Make sure trading engine is running first!
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

REM Check if Streamlit is installed
python -c "import streamlit" >nul 2>&1
if errorlevel 1 (
    echo Installing Streamlit...
    pip install streamlit
)

REM Start the dashboard UI
echo 🌐 Launching Dashboard...
echo Dashboard will open at: http://localhost:8505
echo.
python -m streamlit run mt5_signal.py --server.port 8505 --server.headless false

pause
