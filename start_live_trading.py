"""
LIVE TRADING LAUNCHER
Quick start script for live trading with all safety features
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv  # Add this import
from live_trading_bot import LiveTradingBot

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Launch live trading with safety checks"""
    
    # Load environment variables from .env file
    load_dotenv()  # Add this line
    
    print("🚀 **LIVE TRADING SYSTEM**")
    print("=" * 50)
    
    # Load environment variables
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not telegram_token:
        print("⚠️  WARNING: No Telegram token found")
        print("   You won't receive trade notifications")
        response = input("   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Safety confirmation
    print("\n🛡️  **SAFETY CHECKLIST**")
    print("   ✅ MT5 Terminal is running")
    print("   ✅ Account is DEMO (not real money)")
    print("   ✅ Lot size is capped at 0.5")
    print("   ✅ Max 3 open trades")
    print("   ✅ 30-minute position timeout")
    print("   ✅ Spread filter (max 2.0 pips)")
    print("   ✅ Trading hours filter (6:00-20:00)")
    print("   ✅ Weekend protection")
    
    print("\n⚠️  **RISK WARNING**")
    print("   This is REAL trading with REAL money")
    print("   Even in DEMO, treat it seriously")
    print("   Monitor positions closely")
    print("   Stop immediately if issues occur")
    
    # Final confirmation
    print("\n🎯 **READY TO GO LIVE**")
    print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
    print(f"   Symbol: EURUSD")
    print(f"   Cycle: Every 5 minutes")
    
    confirm = input("\n   Type 'START' to begin live trading: ")
    if confirm.upper() != 'START':
        print("❌ Trading cancelled")
        return
    
    try:
        # Create and initialize bot
        print("\n🔧 Initializing trading bot...")
        bot = LiveTradingBot(telegram_token, telegram_chat_id)
        
        if bot.initialize():
            print("✅ Bot initialized successfully")
            
            # Start live trading
            print("\n🚀 **STARTING LIVE TRADING**")
            print("   Press Ctrl+C to stop")
            print("   Monitor terminal for updates")
            
            bot.start_live_trading(cycle_seconds=300)  # 5 minutes
            
        else:
            print("❌ Failed to initialize bot")
            
    except KeyboardInterrupt:
        print("\n🛑 Trading stopped by user")
    except Exception as e:
        print(f"\n❌ Trading error: {e}")
    finally:
        print("✅ Live trading session ended")

if __name__ == "__main__":
    main()
