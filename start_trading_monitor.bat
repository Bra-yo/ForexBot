@echo off
echo ========================================
echo    BrayoForexBot - Complete Trading System
echo ========================================
echo.
echo This will start:
echo 1. Market Scanner (background)
echo 2. Trading Monitor (foreground)
echo.
echo Features:
echo - 15 Currency Pairs + Gold scanning
echo - 7 Timeframes monitoring
echo - Telegram alerts with charts
echo - Real-time trading engine
echo.
echo Press any key to start complete system...
pause >nul

echo.
echo � Starting Market Scanner (background)...
cd /d "C:\Users\ESSENCE\CascadeProjects\windsurf-project"
start /B python market_scanner_service.py

echo �� Starting Trading Monitor (foreground)...
cd /d "C:\Users\ESSENCE\CascadeProjects\windsurf-project\dashboard"
python trading_monitor.py

echo.
echo 🛑 Stopping Market Scanner...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq market_scanner_service.py*" 2>nul

pause
