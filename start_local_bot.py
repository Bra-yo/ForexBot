"""
NYX AI LOCAL BOT STARTER
Run the trading bot locally (instead of VPS)
"""

import os
import sys
import logging
import MetaTrader5 as mt5
from datetime import datetime

# Windows' console (cp1252) can't encode the emoji used throughout this
# codebase's log messages, which was causing a "Logging error" + traceback
# printed for nearly every single log line. This must happen here, before
# logging.basicConfig() below, because this file is the true entry point -
# it's the first thing that runs, and logging.basicConfig() is a documented
# no-op if the root logger already has handlers (which is exactly what was
# silently breaking the same fix when it was placed in multi_pair_live_bot_
# clean.py instead, since that module is imported much later).
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('local_bot.log', encoding='utf-8')
    ],
    force=True  # belt-and-suspenders: override any handler set up earlier
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

def check_environment():
    """Check if all required files exist"""
    required_files = [
        'start_multi_pair_trading_fixed.py',
        'live_trading_executor.py',
        'signal_quality_engine.py',
        'adaptive_threshold_engine.py',
        'trade_memory_system.py',
        'risk_manager.py',
        'config.py'
    ]
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    
    if missing_files:
        logger.error(f"Missing required files: {missing_files}")
        return False
    
    logger.info("All required files found")
    return True

def start_bot():
    """Start the trading bot"""
    logger.info("=== NYX AI LOCAL BOT STARTING ===")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Working Directory: {os.getcwd()}")
    
    # Check environment
    if not check_environment():
        logger.error("Environment check failed - aborting")
        return
    
    # Check MT5 connection
    if not check_mt5_connection():
        logger.error("MT5 connection failed - aborting")
        return
    
    # Start the multi-pair trading bot
    try:
        logger.info("Starting multi-pair trading bot...")
        
        # Import and start the bot
        from start_multi_pair_trading_fixed import main
        main()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        logger.info("=== NYX AI LOCAL BOT STOPPED ===")

if __name__ == "__main__":
    start_bot()