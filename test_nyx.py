#!/usr/bin/env python3

import os
import sys
import time
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    print("NYX AI TEST")
    print("Type 'NYX-START' to begin...")
    
    # Simulate user input
    sys.argv.append("NYX-START")
    
    # Load environment variables
    load_dotenv()
    
    try:
        # Import and start bot
        print("Initializing multi-pair trading bot...")
        from multi_pair_live_bot import MultiPairLiveBot
        
        # Test with minimal configuration
        bot = MultiPairLiveBot(None, None)
        
        if bot.initialize():
            print("Multi-pair bot initialized successfully")
            
            # Start with short cycle for testing
            print("Starting NYX AI LIVE TRADING (TEST MODE)")
            print("   Press Ctrl+C to stop")
            print("   Testing position limits and emergency close...")
            
            bot.start_multi_pair_trading(cycle_seconds=10)  # 10 seconds for quick test
            
        else:
            print("Failed to initialize multi-pair bot")
            
    except KeyboardInterrupt:
        print("\nMulti-pair trading stopped by user")
    except Exception as e:
        print(f"Multi-pair trading error: {e}")
    finally:
        print("Multi-pair live trading session ended")

if __name__ == "__main__":
    main()
