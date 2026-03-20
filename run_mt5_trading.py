"""
MT5 Trading Dashboard Launcher
Guaranteed to run the MT5 integrated version
"""

import subprocess
import sys
import os
from pathlib import Path

def run_mt5_dashboard():
    """Run the MT5 integrated trading dashboard"""
    try:
        # Get project directory
        project_dir = Path(__file__).parent
        
        # Path to streamlit executable
        streamlit_path = Path("C:/Users/ESSENSE/AppData/Local/Python/pythoncore-3.14-64/Scripts/streamlit.exe")
        
        # Path to MT5 dashboard file
        dashboard_path = project_dir / "dashboard" / "mt5_signal.py"
        
        print("Starting MT5 Trading Dashboard...")
        print(f"Streamlit: {streamlit_path}")
        print(f"Dashboard: {dashboard_path}")
        print("URL: http://localhost:8501")
        print()
        
        # Run streamlit
        cmd = [
            str(streamlit_path),
            "run",
            str(dashboard_path),
            "--server.port", "8501",
            "--server.address", "localhost"
        ]
        
        # Change to project directory and run
        os.chdir(project_dir)
        subprocess.run(cmd, check=True)
        
    except Exception as e:
        print(f"Error starting dashboard: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    run_mt5_dashboard()
