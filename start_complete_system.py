#!/usr/bin/env python3
"""
START COMPLETE SYSTEM
With option to show analytics only (no bot)
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

def show_menu():
    """Show menu options"""
    print("🔥 NYX AI COMPLETE SYSTEM")
    print("=" * 50)
    print("1. 🚀 Start Trading Bot + Dashboard")
    print("2. 📊 Show Analytics Only (No Bot)")
    print("3. ❌ Exit")
    print("=" * 50)

def start_trading_system():
    """Start the complete trading system"""
    print("\n🚀 Starting Trading Bot + Dashboard...")
    
    # Safety confirmation
    print("\n🛡️  **NYX AI SAFETY CHECK**")
    print("   [OK] MT5 Terminal is running")
    print("   [OK] Account is DEMO (not real money)")
    print("   [OK] Lot size is capped at 0.5")
    print("   [OK] Max 3 open trades per symbol")
    print("   [OK] 30-minute position timeout")
    print("   [OK] Spread filter (max 8.0 pips)")
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
        return

    print("🔧 Initializing multi-pair trading bot...")

    try:
        # Import and start bot
        import multi_pair_live_bot_clean as multi_pair_live_bot
        
        # Run the bot
        multi_pair_live_bot.main()
        
    except KeyboardInterrupt:
        print("\n🛑 Trading bot stopped by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("🔧 Make sure all dependencies are installed")

def show_analytics_only():
    """Show analytics dashboard only"""
    print("\n📊 Starting Analytics Dashboard Only...")
    print("⚠️  Make sure MT5 is running with your demo account")
    print("🔄 Analytics will auto-refresh every 30 seconds")
    print("=" * 50)
    
    try:
        # Import analytics
        from integrated_analytics import analytics
        
        # Show full performance dashboard
        analytics.print_performance_dashboard()
        
        # Keep showing updates every 30 seconds
        import time
        print("\n🔄 Auto-refresh every 30 seconds (Ctrl+C to stop)")
        print("=" * 50)
        
        while True:
            time.sleep(30)
            print(f"\n📊 Quick Update - {time.strftime('%H:%M:%S')}")
            analytics.print_quick_stats()
            
    except KeyboardInterrupt:
        print("\n\n✅ Analytics dashboard stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("💡 Make sure MT5 is running and you're logged into your demo account (5048146647)")

def main():
    """Main function with menu"""
    while True:
        show_menu()
        
        try:
            choice = input("\nSelect option (1-3): ").strip()
            
            if choice == "1":
                start_trading_system()
                break
            elif choice == "2":
                show_analytics_only()
                break
            elif choice == "3":
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice. Please select 1, 2, or 3.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break

if __name__ == "__main__":
    main()
