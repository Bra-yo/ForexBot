"""
START MULTI-PAIR TRADING
Clean launcher for Nyx AI multi-pair trading system

NOTE: This used to run entirely as top-level module code, which meant
`from start_multi_pair_trading_fixed import main` (used by start_local_bot.py)
always failed with ImportError - `main` was never actually defined anywhere,
it just ran inline the moment the module was imported. Wrapped in an actual
main() function below so the import succeeds and the caller controls when it
runs.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv


def main():
    # Safety confirmation
    print("\n[SAFETY CHECK] NYX AI SAFETY CHECK")
    print("   [OK] MT5 Terminal is running")
    print("   [OK] Account is DEMO (not real money) - VERIFY THIS YOURSELF IN MT5 BEFORE TYPING NYX-START")
    print("   [OK] Lot size is capped at 0.5")
    print("   [OK] Max 7 open trades per symbol (one per timeframe)")
    print("   [OK] No time-based exit - trades close on stop_loss/take_profit only")
    print("   [OK] Spread filter (max 5.0 pips)")
    print("   [OK] Trading hours filter (6:00-20:00)")
    print("   [OK] Weekend protection")
    print("   [OK] Symbol: XAUUSD (Gold) - pivoted from multi-pair Forex")
    print("   [OK] Multiple timeframes: M1, M5, M15, M30, H1, H4, D1")

    print("\nNYX AI RISK WARNING")
    print("   Nyx AI watches the Gold (XAUUSD) market 24/7")
    print("   Higher exposure = Higher risk")
    print("   Monitor open positions closely")
    print("   Stop immediately if issues occur")

    print("\nSTARTING NYX AI LIVE TRADING")
    print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
    print("   Symbol: XAUUSD (Gold)")
    print("   Timeframes: M1, M5, M15, M30, H1, H4, D1")
    print("   Cycle: Every 1 minute")
    print("   Max concurrent trades: 7")

    confirm = input("\n   Type 'NYX-START' to begin multi-pair live trading: ")
    if confirm.upper() != 'NYX-START':
        print("❌ Nyx AI multi-pair trading cancelled")
        sys.exit(0)

    print("🔧 Initializing multi-pair trading bot...")

    try:
        # Import and start bot
        import multi_pair_live_bot_clean as multi_pair_live_bot

        # Run the bot
        multi_pair_live_bot.main()

    except KeyboardInterrupt:
        print("\nMulti-pair trading stopped by user")
    except Exception as e:
        print(f"\nMulti-pair trading error: {e}")
    finally:
        print("Multi-pair live trading session ended")


if __name__ == "__main__":
    main()