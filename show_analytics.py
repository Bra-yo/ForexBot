#!/usr/bin/env python3
"""
SHOW ANALYTICS DASHBOARD ONLY
Run integrated analytics without starting the trading bot
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print("🔥 NYX AI ANALYTICS DASHBOARD")
    print("=" * 50)
    print("📊 Showing 6-day performance analytics")
    print("⚠️  Make sure MT5 is running with your demo account")
    print("=" * 50)
    
    try:
        # Import analytics
        from integrated_analytics import analytics
        
        # Show full performance dashboard
        analytics.print_performance_dashboard()
        
        # Optional: Keep showing updates every 30 seconds
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
        print("💡 Make sure MT5 is running and you're logged into your demo account")

if __name__ == "__main__":
    main()
