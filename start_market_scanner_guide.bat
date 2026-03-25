@echo off
echo ========================================
echo MARKET SCANNER STARTUP GUIDE
echo ========================================
echo.
echo BEFORE RUNNING:
echo 1. Make sure MetaTrader 5 is OPEN
echo 2. Make sure you are LOGGED IN to MT5
echo 3. Make sure MT5 is CONNECTED to server
echo.
echo If MT5 is ready, press any key to start scanner...
pause >nul
echo.
echo Starting Market Scanner Service...
echo.

cd /d "C:\Users\ESSENCE\CascadeProjects\windsurf-project"
python market_scanner_service.py

pause
