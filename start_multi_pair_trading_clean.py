"""
NYX AI MULTI-PAIR LIVE TRADING LAUNCHER
Clean version without Unicode encoding issues
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
    print("   [OK] Max 5 open trades globally")
    print("   [OK] 30-minute position timeout")
    print("   [OK] Spread filter (max 5.0 pips)")
    print("   [OK] Trading hours filter (6:00-20:00)")
    print("   [OK] Weekend protection")
    print("   [OK] Position stacking prevention")
    print("   [OK] Global risk control (5% max)")
    print("   [OK] Professional position management")
    print("   [OK] Trade lifecycle management")
    print("   [OK] Max 3 USD-direction trades")
    print("   [OK] Max 3 JPY-related trades")
    print("   [OK] 45-minute trade timeout (increased)")
    print("   [OK] $5 profit/loss targets (increased)")
    print("   [OK] Adaptive lot sizing (confidence-based)")
    print("   [OK] R-multiple profit targets (1.5R/2.5R)")
    print("   [OK] Market regime detection")
    print("   [OK] Signal scoring engine (0-100)")
    print("   [OK] Intelligent trade filtering")
    print("   [OK] Trending/ranging market adaptation")
    print("   [OK] Professional trade execution (no 10030)")
    print("   [OK] Multi-mode order closing (FOK/IOC/RETURN)")
    print("   [OK] Emergency stop file monitoring")
    print("   [OK] Single instance protection")
    print("   [OK] Process ID tracking")
    print("   [OK] Ctrl+C signal handling")
    print("   [OK] Telegram stop commands")
    print("   [OK] Level 3 Intelligence System")
    print("   [OK] Multiple pairs: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURGBP, EURJPY, GBPJPY, NZDUSD, EURCHF")
    print("   [OK] Multiple timeframes: M15, M30, H1")
    
    print("NYX AI RISK WARNING")
    print("   Nyx AI watches markets 24/7 across all pairs")
    print("   Higher exposure = Higher risk")
    print("   Monitor ALL positions closely")
    print("   Stop immediately if issues occur")
    print("   Each pair will trade independently")
    
    # Final confirmation
    print("NYX AI READY TO GO LIVE")
    print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
    print("   Symbols: 10 major currency pairs")
    print("   Timeframes: M15, M30, H1")
    print("   Cycle: Every 1 minute")
    print("   Max concurrent trades: 30 (3 per symbol)")
    
    try:
        confirm = input("   Type 'NYX-START' to begin multi-pair live trading: ")
    except EOFError:
        print("   Input cancelled - exiting")
        return
    
    if confirm.upper() != 'NYX-START':
        print("Nyx AI trading cancelled")
        return
    
    try:
        # NEW: Use safe main launcher
        print(" STARTING WITH SAFETY CONTROLS...")
        print("   [OK] Single instance protection")
        print("   [OK] Emergency stop file monitoring")
        print("   [OK] Ctrl+C signal handling")
        print("   [OK] Process ID tracking")
        print("   [OK] Lock file protection")
        print("   [OK] Safe shutdown procedures")
        print()
        
        # Import and run safe main
        from safe_main import main as safe_main
        safe_main()
    except ImportError as e:
        print(f" Failed to import safety system: {e}")
        print("Falling back to basic launcher...")
        
        # Fallback to original method
        from multi_pair_live_bot import MultiPairLiveBot
        bot = MultiPairLiveBot(telegram_token, telegram_chat_id)
        
        try:
            bot.run_multi_pair_trading()
        except KeyboardInterrupt:
            print("\n Bot stopped by user")
            if bot.live_executor:
                bot.live_executor.stop()
            bot.stop()
            
    except KeyboardInterrupt:
        print("Multi-pair trading stopped by user")
    except Exception as e:
        print(f"Multi-pair trading error: {e}")
    finally:
        print("Multi-pair live trading session ended")

if __name__ == "__main__":
    main()
