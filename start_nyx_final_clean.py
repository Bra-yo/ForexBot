#!/usr/bin/env python3

import os
import sys
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure basic logging without Unicode
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    print("NYX AI FINAL CLEAN TEST")
    print("Testing position limits and emergency close...")
    
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
            
            # Start with very short cycle for testing (5 seconds)
            print("Starting NYX AI LIVE TRADING (FINAL CLEAN TEST)")
            print("   Will test position limits (max 5)")
            print("   Will test emergency close on stop")
            print("   Press Ctrl+C to stop")
            
            bot.start_multi_pair_trading(cycle_seconds=5)  # 5 seconds for quick test
            
        else:
            print("Failed to initialize multi-pair bot")
            
    except KeyboardInterrupt:
        print("\nMulti-pair trading stopped by user - Testing emergency close...")
        # Test emergency close
        bot.live_executor.emergency_close_all()
    except Exception as e:
        print(f"Multi-pair trading error: {e}")
    finally:
        print("Multi-pair live trading session ended")

if __name__ == "__main__":
    main()
