@echo off
echo ========================================
echo    BrayoForexBot - Connection Test
echo ========================================
echo.
echo This will test MT5 connection step by step
echo and show detailed status information
echo.
echo Press any key to start test...
pause >nul

echo.
echo 🧪 Starting Connection Test...
cd /d "C:\Users\ESSENCE\CascadeProjects\windsurf-project\dashboard"
python test_connection.py

pause
