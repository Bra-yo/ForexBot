"""
NYX AI - FINAL BOT STARTER
Completely bypass input prompts and start trading
"""

import os
import sys
import logging
from datetime import datetime

# Setup ASCII-only logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('final_bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def start_bot_final():
    """Start bot with complete input bypass"""
    print("=" * 60)
    print("NYX AI - FINAL LOCAL BOT")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("AUTO-STARTING - All prompts bypassed")
    print("=" * 60)
    
    try:
        # Set environment for UTF-8
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        
        # Override input function globally
        def auto_input(prompt=""):
            print(f"{prompt} [AUTO-CONFIRMED]")
            return "NYX-START"
        
        # Replace built-in input
        import builtins
        builtins.input = auto_input
        
        # Now import and start the bot
        print("Loading bot components...")
        import multi_pair_live_bot_clean as multi_pair_live_bot
        
        print("Starting multi-pair trading bot...")
        multi_pair_live_bot.main()
        
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Bot error: {e}")
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    start_bot_final()
