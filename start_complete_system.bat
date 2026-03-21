@echo off
echo ========================================
echo    BrayoForexBot - Complete System
echo ========================================
echo.
echo This will start the dashboard which will:
echo 1. Start the trading engine automatically
echo 2. Show login page for MT5 connection
echo 3. Pass credentials to engine securely
echo.
echo Press any key to start the system...
pause >nul

echo.
echo 🌐 Starting Dashboard (will start engine automatically)...
start "Dashboard" cmd /k "cd /d C:\Users\ESSENCE\CascadeProjects\windsurf-project\dashboard && python -m streamlit run mt5_signal.py --server.port 8505"

echo.
echo ✅ System Started!
echo.
echo Dashboard: Opening in browser at http://localhost:8505
echo Trading Engine: Will start automatically after login
echo.
echo Close this window to keep dashboard running
echo.

pause
