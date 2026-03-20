@echo off
echo Starting MT5 Trading Dashboard...
echo.
cd /d "C:\Users\ESSENSE\CascadeProjects\windsurf-project"
"C:\Users\ESSENSE\AppData\Local\Python\pythoncore-3.14-64\Scripts\streamlit.exe" run "dashboard\mt5_signal.py"
pause
