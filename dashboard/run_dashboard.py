"""
Dashboard Launcher for BrayoForexBot
Easy way to start the professional trading dashboard
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Launch the dashboard"""
    print("🚀 Starting BrayoForexBot Dashboard...")
    
    # Get dashboard directory
    dashboard_dir = Path(__file__).parent
    app_path = dashboard_dir / "app.py"
    
    if not app_path.exists():
        print("❌ Dashboard app.py not found!")
        return
    
    try:
        # Install dashboard requirements
        print("📦 Installing dashboard requirements...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", 
            str(dashboard_dir / "requirements.txt")
        ], check=True)
        
        # Start Streamlit dashboard
        print("🌐 Launching dashboard in browser...")
        print("📊 Dashboard will open at: http://localhost:8501")
        print("⚠️  Press Ctrl+C to stop the dashboard")
        
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", 
            str(app_path),
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
        
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped by user")
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")

if __name__ == "__main__":
    main()
