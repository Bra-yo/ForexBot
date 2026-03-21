@echo off
echo ========================================
echo    Kill Streamlit Processes
echo ========================================
echo.
echo This will stop all running Streamlit instances
echo to free up ports 8502, 8503, 8504, etc.
echo.

echo 🛑 Stopping Streamlit processes...
taskkill /f /im streamlit.exe 2>nul
taskkill /f /im python.exe /fi "WINDOWTITLE eq streamlit*" 2>nul

echo.
echo 🧹 Checking for ports in use...
netstat -an | findstr ":8502" 
netstat -an | findstr ":8503" 
netstat -an | findstr ":8504" 

echo.
echo ✅ Streamlit processes stopped!
echo.
echo Now you can run:
echo - start_complete_system.bat
echo - start_dashboard.bat
echo.

pause
