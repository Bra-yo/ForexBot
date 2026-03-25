"""
Debug Trading Engine - Identify exact crash point
"""
import time
import logging
import traceback
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def debug_engine_startup():
    """Debug engine startup step by step"""
    try:
        logger.info("=== DEBUG ENGINE STARTUP ===")
        
        # Step 1: Import test
        logger.info("Step 1: Testing imports...")
        try:
            from brokers.mt5_connector import MT5Connector
            logger.info("✅ MT5Connector import OK")
        except Exception as e:
            logger.error(f"❌ MT5Connector import failed: {e}")
            return False
        
        try:
            from dashboard.trade_manager import TradeManager
            logger.info("✅ TradeManager import OK")
        except Exception as e:
            logger.error(f"❌ TradeManager import failed: {e}")
            return False
        
        try:
            from integrated_scanner import IntegratedScanner
            logger.info("✅ IntegratedScanner import OK")
        except Exception as e:
            logger.error(f"❌ IntegratedScanner import failed: {e}")
            return False
            
        try:
            from auto_trading_manager import AutoTradingManager
            logger.info("✅ AutoTradingManager import OK")
        except Exception as e:
            logger.error(f"❌ AutoTradingManager import failed: {e}")
            return False
        
        # Step 2: MT5 Connection
        logger.info("Step 2: Testing MT5 connection...")
        try:
            mt5_connector = MT5Connector()
            connection_result = mt5_connector.initialize()
            if connection_result:
                logger.info("✅ MT5 connection OK")
            else:
                logger.error("❌ MT5 connection failed")
                return False
        except Exception as e:
            logger.error(f"❌ MT5 connection error: {e}")
            logger.error(traceback.format_exc())
            return False
        
        # Step 3: Trade Manager
        logger.info("Step 3: Testing TradeManager...")
        try:
            trade_manager = TradeManager(mt5_connector)
            logger.info("✅ TradeManager creation OK")
        except Exception as e:
            logger.error(f"❌ TradeManager creation failed: {e}")
            logger.error(traceback.format_exc())
            return False
        
        # Step 4: Scanner
        logger.info("Step 4: Testing IntegratedScanner...")
        try:
            scanner = IntegratedScanner()
            scanner.mt5_connector = mt5_connector
            logger.info("✅ IntegratedScanner creation OK")
        except Exception as e:
            logger.error(f"❌ IntegratedScanner creation failed: {e}")
            logger.error(traceback.format_exc())
            return False
        
        # Step 5: Auto Trading Manager
        logger.info("Step 5: Testing AutoTradingManager...")
        try:
            auto_trading_manager = AutoTradingManager(
                mt5_connector, 
                trade_manager, 
                None  # No telegram assistant for debug
            )
            logger.info("✅ AutoTradingManager creation OK")
        except Exception as e:
            logger.error(f"❌ AutoTradingManager creation failed: {e}")
            logger.error(traceback.format_exc())
            return False
        
        # Step 6: Configure Auto Trading
        logger.info("Step 6: Testing auto trading config...")
        try:
            auto_trading_manager.update_config(
                enabled=True,
                min_confidence=50,
                max_trades=3,
                cooldown_minutes=5,
                risk_per_trade=1.0
            )
            logger.info("✅ Auto trading config OK")
        except Exception as e:
            logger.error(f"❌ Auto trading config failed: {e}")
            logger.error(traceback.format_exc())
            return False
        
        # Step 7: Scanner Auto Trading Init
        logger.info("Step 7: Testing scanner auto trading init...")
        try:
            auto_trading_initialized = scanner.initialize_auto_trading(trade_manager)
            if auto_trading_initialized:
                logger.info("✅ Scanner auto trading init OK")
            else:
                logger.error("❌ Scanner auto trading init failed")
                return False
        except Exception as e:
            logger.error(f"❌ Scanner auto trading init failed: {e}")
            logger.error(traceback.format_exc())
            return False
        
        # Step 8: Start Scanner
        logger.info("Step 8: Testing scanner start...")
        try:
            scanner.start_background_scanner()
            logger.info("✅ Scanner start OK")
        except Exception as e:
            logger.error(f"❌ Scanner start failed: {e}")
            logger.error(traceback.format_exc())
            return False
        
        logger.info("=== ALL STEPS PASSED ===")
        return True
        
    except Exception as e:
        logger.error(f"❌ Debug engine failed: {e}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("🔍 Starting Trading Engine Debug...")
    success = debug_engine_startup()
    
    if success:
        print("✅ All engine components working!")
        print("The issue might be in the main trading loop logic.")
    else:
        print("❌ Engine component failure detected!")
        print("Check the debug logs above for exact error.")
