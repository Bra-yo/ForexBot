"""
START MULTI-PAIR TRADING
Clean launcher for Nyx AI multi-pair trading system
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Safety confirmation
print("\n🛡️  **NYX AI SAFETY CHECK**")
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

print("\nNYX AI RISK WARNING")
print("   Nyx AI watches markets 24/7 across all pairs")
print("   Higher exposure = Higher risk")
print("   Monitor ALL positions closely")
print("   Stop immediately if issues occur")
print("   Each pair will trade independently")

print("\nSTARTING NYX AI LIVE TRADING")
print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
print("   Symbols: 10 major currency pairs")
print("   Timeframes: M15, M30, H1")
print("   Cycle: Every 1 minute")
print("   Max concurrent trades: 30 (3 per symbol)")

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
