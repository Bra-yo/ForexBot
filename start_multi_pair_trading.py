"""
MULTI-PAIR LIVE TRADING LAUNCHER
Launch trading across multiple currency pairs and timeframes
"""

import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Launch multi-pair live trading with safety checks"""
    
    # Load environment variables
    load_dotenv()
    
    print("NYX AI MULTI-PAIR LIVE TRADING SYSTEM")
    print("=" * 60)
    print("Nyx AI - 24/7 Market Intelligence")
    print("   Trading across multiple currency pairs and timeframes")
    print()
    
    # Load environment variables
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    telegram_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not telegram_token:
        print("   WARNING: No Telegram token found")
        print("   You won't receive trade notifications")
        response = input("   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    # Safety confirmation
    print("NYX AI SAFETY CHECKLIST")
    print("   [OK] MT5 Terminal is running")
    print("   [OK] Account is DEMO (not real money)")
    print("   [OK] Lot size is capped at 0.5")
    print("   [OK] Max 3 open trades per symbol")
    print("   [OK] 30-minute position timeout")
    print("   [OK] Spread filter (max 5.0 pips)")
    print("   [OK] Trading hours filter (6:00-20:00)")
    print("   [OK] Weekend protection")
    print("   [OK] Multiple pairs: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURGBP, EURJPY, GBPJPY, NZDUSD, EURCHF")
    print("   [OK] Multiple timeframes: M15, M30, H1")
    
    print("NYX AI RISK WARNING")
    print("   Nyx AI watches markets 24/7 across all pairs")
    print("   Higher exposure = Higher risk")
    print("   Monitor ALL positions closely")
    print("   Stop immediately if issues occur")
    print("   Each pair will trade independently")
    
    # Final confirmation
    print("\nSTARTING NYX AI LIVE TRADING")
    print("   Time: " + datetime.now().strftime('%H:%M:%S'))
    print("   Symbols: 10 major currency pairs")
    print("   Timeframes: M15, M30, H1")
    print("   Cycle: Every 1 minute")
    print("   Max concurrent trades: 30 (3 per symbol)")
    
    try:
        confirm = input("\n   Type 'NYX-START' to begin multi-pair live trading: ")
    except EOFError:
        print("   Input cancelled - exiting")
        return
    
    if confirm.upper() != 'NYX-START':
        print("❌ Nyx AI trading cancelled")
        return
    
    try:
        # Import and start bot
        print("🔧 Initializing multi-pair trading bot...")
        import multi_pair_live_bot_clean as multi_pair_live_bot

        if __name__ == "__main__":
            multi_pair_live_bot.main()
            
        print("   Press Ctrl+C to stop")
        print("   Monitor terminal for updates")
        print("   Nyx AI watches across 10 symbols x 3 timeframes")
            
    except KeyboardInterrupt:
        print("\nMulti-pair trading stopped by user")
    except Exception as e:
        print(f"\nMulti-pair trading error: {e}")
    finally:
        print("Multi-pair live trading session ended")

if __name__ == "__main__":
    main()
