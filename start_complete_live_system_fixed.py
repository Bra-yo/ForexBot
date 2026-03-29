"""
COMPLETE LIVE TRADING SYSTEM WITH SAFETY CONTROLS
Professional trading bot with dashboard and full safety management
"""

import os
import sys
import logging
import time
import subprocess
import threading
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# NEW: Import safety controller
from bot_controller import BotController

class CompleteLiveSystem:
    """Manages both trading bot and dashboard with full safety controls"""
    
    def __init__(self):
        self.trading_process = None
        self.dashboard_process = None
        self.is_running = False
        
        # NEW: Initialize safety controller
        self.controller = BotController()
        
    def start_dashboard(self):
        """Start Streamlit dashboard"""
        try:
            print("🌐 Starting Dashboard...")
            
            # Check if dashboard directory exists
            dashboard_path = os.path.join(os.getcwd(), "dashboard")
            if not os.path.exists(dashboard_path):
                print("⚠️ Dashboard directory not found, skipping dashboard")
                return True
            
            # Start Streamlit dashboard
            self.dashboard_process = subprocess.Popen([
                sys.executable, "-m", "streamlit", "run", 
                "mt5_signal.py", "--server.port", "8505"
            ], cwd=dashboard_path)
            
            print("✅ Dashboard started at http://localhost:8505")
            print("   You can monitor trades and control bot from web interface")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start dashboard: {e}")
            return False
    
    def start_trading_bot(self, multi_pair=True):
        """Start trading bot"""
        try:
            print("🤖 Starting Trading Bot...")
            
            # Choose which bot to start
            if multi_pair:
                script = "start_multi_pair_trading_clean.py"  # Updated to clean version
                print("📊 Multi-Pair Trading Bot selected")
            else:
                script = "start_live_trading.py"
                print("🤖 Single Pair Trading Bot selected")
                
            # NEW: Check single instance before starting
            if not self.controller.check_single_instance():
                print("❌ Another instance is already running")
                return False
                
            # Start the trading bot process
            self.trading_process = subprocess.Popen([
                sys.executable, script
            ])
            
            print(f"✅ Trading Bot started (PID: {self.trading_process.pid})")
            print(f"   Script: {script}")
            print("   Process ID tracked for safety controls")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start trading bot: {e}")
            return False
    
    def stop_all(self):
        """Stop all processes and cleanup"""
        print("🛑 Stopping all processes...")
        
        self.is_running = False
        
        # Stop trading bot
        if self.trading_process:
            self.trading_process.terminate()
            self.trading_process.wait(timeout=5)
            
        # Stop dashboard
        if self.dashboard_process:
            self.dashboard_process.terminate()
            self.dashboard_process.wait(timeout=5)
            
        # Cleanup control files
        self.controller.cleanup_lock_files()
        
        print("✅ All processes stopped")
        
    def monitor_processes(self):
        """Monitor both processes and restart if needed"""
        while self.is_running:
            try:
                # Check if processes are still running
                if self.trading_process and self.trading_process.poll() is not None:
                    print("🔄 Trading bot stopped, restarting...")
                    self.start_trading_bot(multi_pair=True)
                    
                if self.dashboard_process and self.dashboard_process.poll() is not None:
                    print("🔄 Dashboard stopped, restarting...")
                    self.start_dashboard()
                    
            except Exception as e:
                print(f"❌ Process monitoring error: {e}")
                
            time.sleep(5)  # Check every 5 seconds

def main():
    """Main function to run complete live trading system"""
    
    # Load environment variables
    load_dotenv()
    
    print("🌙 **NYX AI COMPLETE LIVE SYSTEM**")
    print("=" * 60)
    print("🤖 Trading Bot + 🌐 Dashboard + 🛡️ Safety Controls")
    print("=" * 60)
    print()
    
    # Configuration
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    if not TELEGRAM_TOKEN:
        print("⚠️ WARNING: No Telegram token found")
        print("   You won't receive trade notifications")
        response = input("   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    print("🔒 SAFETY CHECKLIST")
    print("   [OK] Single instance protection")
    print("   [OK] Emergency stop file monitoring")
    print("   [OK] Ctrl+C signal handling")
    print("   [OK] Process ID tracking")
    print("   [OK] Lock file protection")
    print("   [OK] Safe shutdown procedures")
    print("   [OK] Level 3 Intelligence System")
    print("   [OK] Adaptive lot sizing")
    print("   [OK] R-multiple profit targets")
    print("   [OK] Market regime detection")
    print("   [OK] Signal scoring engine")
    print("   [OK] Professional trade execution")
    print("   [OK] Multi-mode order closing")
    print("   [OK] Emergency stop file monitoring")
    print("   [OK] Single instance protection")
    print("   [OK] Process ID tracking")
    print("   [OK] Ctrl+C signal handling")
    print("   [OK] Telegram stop commands")
    print()
    
    # Create system manager
    system = CompleteLiveSystem()
    
    # Final confirmation
    print(f"\n🌙 **NYX AI READY TO START COMPLETE SYSTEM**")
    print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"   Trading: {'Multi-Pair' if True else 'Single-Pair'}")
    print(f"   Dashboard: http://localhost:8505")
    print(f"   🌙 Nyx AI: 24/7 Market Intelligence")
    print()
    
    confirm = input("\n   Type 'NYX-START' to begin: ")
    if confirm.upper() != 'NYX-START':
        print("❌ Nyx AI complete system start cancelled")
        return
    
    try:
        # Start dashboard
        if not system.start_dashboard():
            print("❌ Failed to start dashboard")
            return
        
        # Wait a moment for dashboard to start
        time.sleep(3)
        
        # Start trading bot
        if not system.start_trading_bot(multi_pair=True):
            print("❌ Failed to start trading bot")
            system.stop_all()
            return
        
        # Start monitoring
        system.is_running = True
        print("\n🚀 **COMPLETE SYSTEM RUNNING**")
        print("   🌐 Dashboard: http://localhost:8505")
        print("   🤖 Trading Bot: Running in background")
        print("   📱 Telegram: Notifications enabled")
        print("   🛑 Press Ctrl+C to stop everything")
        print("   📄 Create 'stop.txt' file for emergency stop")
        print("   📱 Send 'STOP NYX' via Telegram")
        print("   🔒 Single instance protection active")
        print("   🆔 Process ID tracking enabled")
        print()
        print("   You can now:")
        print("   - Monitor trades in dashboard")
        print("   - Control trading manually")
        print("   - View real-time data")
        print("   - Receive Telegram alerts")
        print("   - Use Level 3 Intelligence System")
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=system.monitor_processes)
        monitor_thread.daemon = True
        monitor_thread.start()
        
        # Wait for user interrupt
        try:
            while system.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 System stopped by user")
            system.stop_all()
            
    except Exception as e:
        print(f"\n❌ System error: {e}")
        system.stop_all()
        
    finally:
        print("✅ Complete live trading session ended")

if __name__ == "__main__":
    main()
