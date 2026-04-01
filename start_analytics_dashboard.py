#!/usr/bin/env python3
"""
LEVEL 9: Analytics Dashboard Launcher
Quick start script for Nyx AI Analytics Dashboard
"""

import subprocess
import sys
import os

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import flask
        import MetaTrader5
        print("✅ All dependencies are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("📦 Installing dependencies...")
        
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements_dashboard.txt"])
            print("✅ Dependencies installed successfully")
            return True
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies")
            return False

def main():
    print("🔥 NYX AI LEVEL 9 - Analytics Dashboard")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Cannot start dashboard - missing dependencies")
        return
    
    # Start the dashboard
    print("🚀 Starting Analytics Dashboard...")
    print("📊 Dashboard will be available at: http://localhost:5000")
    print("🔄 Auto-refresh every 30 seconds")
    print("⚠️  Make sure MT5 is running with your demo account")
    print("=" * 50)
    
    try:
        # Import and run the dashboard
        from analytics_dashboard import app
        app.run(debug=False, host="0.0.0.0", port=5000)
    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")
        print("💡 Make sure MT5 is running and you're logged into your demo account")

if __name__ == "__main__":
    main()
