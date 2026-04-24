"""
NYX AI - SIMPLE BOT STARTER
ASCII-only version for Windows compatibility
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
        logging.FileHandler('simple_bot.log', encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point - start bot immediately"""
    print("=" * 60)
    print("NYX AI - LOCAL BOT STARTER")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Starting without prompts...")
    print("=" * 60)
    
    try:
        # Set environment for ASCII output
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        
        # Import the actual bot module
        print("Loading bot components...")
        import multi_pair_live_bot_clean as multi_pair_live_bot
        
        # Start the bot directly
        print("Starting multi-pair trading bot...")
        multi_pair_live_bot.main()
        
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Bot error: {e}")
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    main()
