"""
NYX AI - RUN BOT NOW
Immediate start without any prompts
"""

import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot_run.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point - start bot immediately"""
    logger.info("=== NYX AI - IMMEDIATE START ===")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("Bypassing all safety prompts - starting directly...")
    
    try:
        # Import the actual bot module
        import multi_pair_live_bot_clean as multi_pair_live_bot
        
        # Start the bot directly
        logger.info("Starting multi-pair trading bot...")
        multi_pair_live_bot.main()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main()
