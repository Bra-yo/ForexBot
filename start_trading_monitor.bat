@echo off
echo ========================================
echo    BrayoForexBot - Trading Monitor
echo ========================================
echo.
echo This will show REAL-TIME trading engine activity
echo Updates every 2 seconds
echo.
echo Press any key to start monitoring...
pause >nul

echo.
echo 📊 Starting Trading Monitor...
cd /d "C:\Users\ESSENCE\CascadeProjects\windsurf-project\dashboard"
python trading_monitor.py

pause
