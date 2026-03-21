@echo off
echo ========================================
echo    Start Dashboard (Auto Port)
echo ========================================
echo.
echo This will start your original dashboard
echo and let Streamlit find an available port
echo.

echo 🌐 Starting Dashboard (Auto Port)...
cd /d "C:\Users\ESSENCE\CascadeProjects\windsurf-project\dashboard"
python -m streamlit run mt5_signal.py --server.port 0

pause
