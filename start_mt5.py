"""
Simple MT5 Dashboard Starter
"""

import subprocess
import os
import sys

def main():
    print("Starting MT5 Trading Dashboard...")
    
    # Change to project directory
    os.chdir(r"C:\Users\ESSENSE\CascadeProjects\windsurf-project")
    
    # Run MT5 dashboard
    cmd = [
        r"C:\Users\ESSENSE\AppData\Local\Python\pythoncore-3.14-64\Scripts\streamlit.exe",
        "run",
        "dashboard/mt5_signal.py"
    ]
    
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
