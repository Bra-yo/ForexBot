@echo off
echo 🚀 Starting Market Scanner Service...
echo.
echo 📊 Multi-Pair Multi-Timeframe Scanner
echo.
echo 🎯 Features:
echo    ✅ 15 Currency Pairs + Gold
echo    ✅ 7 Timeframes (M5-H4)
echo    ✅ Continuous Independent Scanning
echo    ✅ Telegram Alerts with Charts
echo    ✅ Anti-Spam Protection
echo.
echo 📡 This runs independently from dashboard
echo 📱 Telegram alerts will be sent automatically
echo 🔄 Continuous market monitoring
echo.
echo Press Ctrl+C to stop the scanner
echo.

cd /d "C:\Users\ESSENCE\CascadeProjects\windsurf-project"
python market_scanner_service.py

pause
