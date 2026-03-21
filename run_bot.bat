@echo off
echo ========================================
echo    BrayoForexBot - Complete System
echo ========================================
echo.
echo This will start BOTH:
echo 1. Trading Engine (background)
echo 2. Dashboard UI (browser)
echo.
echo Press any key to start the complete system...
pause >nul

echo.
echo 🚀 Starting Trading Engine...
start "Trading Engine" cmd /k "cd /d C:\Users\ESSENCE\CascadeProjects\windsurf-project\dashboard && python trading_engine.py"

echo 🌐 Starting Dashboard UI...
timeout /t 3 >nul
start "Dashboard" cmd /k "cd /d C:\Users\ESSENCE\CascadeProjects\windsurf-project\dashboard && streamlit run dashboard_ui.py --server.port 8502"

echo.
echo ✅ System Started!
echo.
echo Trading Engine: Running in background window
echo Dashboard: Opening in browser at http://localhost:8502
echo.
echo Close this window to keep both running
echo Press CTRL+C in engine window to stop trading
echo.

pause
