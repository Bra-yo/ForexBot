"""
NYX AI DIRECT BOT STARTER
Start the trading bot directly without input prompts
"""

import os
import sys
import logging
import MetaTrader5 as mt5
from datetime import datetime
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('local_bot.log')
    ]
)

logger = logging.getLogger(__name__)

def check_mt5_connection():
    """Verify MT5 is running and connected"""
    try:
        if not mt5.initialize():
            logger.error("MT5 initialization failed")
            return False
        
        account_info = mt5.account_info()
        if account_info is None:
            logger.error("No account info - MT5 not connected to broker")
            return False
        
        logger.info(f"Connected to account: {account_info.login}")
        logger.info(f"Server: {account_info.server}")
        logger.info(f"Balance: ${account_info.balance:,.2f}")
        logger.info(f"Equity: ${account_info.equity:,.2f}")
        
        return True
        
    except Exception as e:
        logger.error(f"MT5 connection error: {e}")
        return False
    finally:
        mt5.shutdown()

def start_bot_directly():
    """Start the trading bot directly without any input prompts"""
    logger.info("=== NYX AI LOCAL BOT - DIRECT START ===")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Working Directory: {os.getcwd()}")
    
    # Check MT5 connection
    if not check_mt5_connection():
        logger.error("MT5 connection failed - aborting")
        return
    
    # Import bot components directly
    try:
        from live_trading_executor import LiveTradingExecutor
        from signal_quality_engine import SignalQualityEngine
        from adaptive_threshold_engine import AdaptiveThresholdEngine
        from trade_memory_system import trade_memory
        
        logger.info("Bot components loaded successfully")
        
        # Initialize the bot
        logger.info("Initializing Nyx AI trading bot...")
        
        # Create bot instance
        bot = LiveTradingExecutor()
        
        logger.info("Bot initialized successfully")
        logger.info("Starting trading cycle...")
        
        # Start trading (simplified version)
        bot.start()
        
        # Keep running
        try:
            while bot.running:
                bot.monitor_positions()
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            bot.stop()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        logger.info("=== NYX AI LOCAL BOT STOPPED ===")

if __name__ == "__main__":
    start_bot_directly()
