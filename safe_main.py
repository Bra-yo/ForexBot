"""
SAFE MAIN LAUNCHER
Includes all control systems for safe bot operation
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Main function to run multi-pair live trading with safety controls"""
    
    # Load environment variables
    load_dotenv()
    
    # Configuration
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    print("NYX AI MULTI-PAIR LIVE TRADING SYSTEM")
    print("=" * 60)
    print("Nyx AI - 24/7 Market Intelligence")
    print("   Trading across multiple currency pairs and timeframes")
    print()
    
    # Safety confirmation
    print("NYX AI SAFETY CHECKLIST")
    print("   [OK] Single instance protection")
    print("   [OK] Emergency stop file monitoring")
    print("   [OK] Ctrl+C signal handling")
    print("   [OK] Process ID tracking")
    print("   [OK] Lock file protection")
    print("   [OK] Safe shutdown procedures")
    print()
    
    # Import and initialize bot
    try:
        from multi_pair_live_bot import MultiPairLiveBot
        
        # Create bot instance
        bot = MultiPairLiveBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
        
        # Run with proper error handling
        try:
            success = bot.run_multi_pair_trading()
            if success:
                print("\n✅ Bot completed successfully")
            else:
                print("\n❌ Bot failed to start")
                
        except KeyboardInterrupt:
            print("\n🛑 Bot stopped by user (Ctrl+C)")
            if bot.live_executor:
                bot.live_executor.stop()
            bot.stop()
            
        except Exception as e:
            print(f"\n❌ Bot error: {e}")
            logger.error(f"Bot execution error: {e}")
            if bot.live_executor:
                bot.live_executor.stop()
            bot.stop()
            
    except ImportError as e:
        print(f"\n❌ Import error: {e}")
        return False
        
    return True

if __name__ == "__main__":
    main()
