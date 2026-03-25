"""
Restart Trading Engine - Reload Updated TradeManager
"""
import sys
import os
import time

def restart_trading():
    """Restart the trading engine to reload updated TradeManager"""
    print("🔄 Restarting Trading Engine...")
    print("📝 This will reload the updated TradeManager...")
    print("⏳ Please wait 3 seconds...")
    time.sleep(3)
    
    # Start the safe trading engine
    print("🚀 Starting Safe Trading Engine with updated TradeManager...")
    os.system("python safe_trading_engine.py")

if __name__ == "__main__":
    restart_trading()
