"""
MT5 Diagnostic Tool - Check MT5 connection details
"""
import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def diagnose_mt5():
    """Diagnose MT5 connection issues"""
    try:
        logger.info("=== MT5 DIAGNOSTIC ===")
        
        # Step 1: Check MetaTrader5 import
        logger.info("Step 1: Testing MetaTrader5 import...")
        try:
            import MetaTrader5 as mt5
            logger.info(f"MetaTrader5 imported successfully")
            logger.info(f"   Version: {mt5.__version__}")
        except ImportError as e:
            logger.error(f"MetaTrader5 import failed: {e}")
            return False
        
        # Step 2: Check MT5 terminal info
        logger.info("Step 2: Checking MT5 terminal info...")
        try:
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                logger.error("❌ MT5 terminal_info() returned None")
                logger.error("   This usually means MT5 is not running or not accessible")
                
                # Try to initialize first
                logger.info("Step 2b: Attempting to initialize MT5...")
                init_result = mt5.initialize()
                if init_result:
                    logger.info("✅ MT5 initialized successfully")
                    
                    # Check terminal info again
                    terminal_info = mt5.terminal_info()
                    if terminal_info:
                        logger.info("✅ MT5 terminal info retrieved after initialization")
                        logger.info(f"   Terminal: {terminal_info.name}")
                        logger.info(f"   Version: {terminal_info.version}")
                        logger.info(f"   Build: {terminal_info.build}")
                        logger.info(f"   Path: {terminal_info.path}")
                    else:
                        logger.error("❌ Still no terminal info after initialization")
                else:
                    logger.error("❌ MT5 initialization failed")
                    logger.error(f"   Last error: {mt5.last_error()}")
                    
                    # Try with specific path
                    logger.info("Step 2c: Trying with specific MT5 path...")
                    common_paths = [
                        r"C:\Program Files\MetaTrader 5\terminal64.exe",
                        r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
                        r"C:\MetaTrader 5\terminal64.exe"
                    ]
                    
                    for path in common_paths:
                        if os.path.exists(path):
                            logger.info(f"   Trying path: {path}")
                            init_result = mt5.initialize(path=path)
                            if init_result:
                                logger.info(f"✅ MT5 initialized with path: {path}")
                                break
                        else:
                            logger.info(f"   Path not found: {path}")
                    else:
                        logger.error("❌ Could not find MT5 terminal path")
                        return False
            else:
                logger.info("✅ MT5 terminal info retrieved")
                logger.info(f"   Terminal: {terminal_info.name}")
                logger.info(f"   Build: {terminal_info.build}")
                logger.info(f"   Path: {terminal_info.path}")
        except Exception as e:
            logger.error(f"❌ Error checking MT5 terminal info: {e}")
            return False
        
        # Step 3: Check account info
        logger.info("Step 3: Checking account info...")
        try:
            account_info = mt5.account_info()
            if account_info:
                logger.info("✅ Account info retrieved")
                logger.info(f"   Login: {account_info.login}")
                logger.info(f"   Server: {account_info.server}")
                logger.info(f"   Balance: ${account_info.balance}")
                logger.info(f"   Equity: ${account_info.equity}")
                logger.info(f"   Trade allowed: {account_info.trade_allowed}")
                logger.info(f"   Trade expert: {account_info.trade_expert}")
            else:
                logger.error("❌ No account info retrieved")
                logger.error(f"   Last error: {mt5.last_error()}")
                return False
        except Exception as e:
            logger.error(f"❌ Error checking account info: {e}")
            return False
        
        # Step 4: Check permissions
        logger.info("Step 4: Checking trading permissions...")
        try:
            account_info = mt5.account_info()
            if account_info:
                if not account_info.trade_allowed:
                    logger.error("❌ Trading not allowed on this account")
                    logger.error("   Please check with your broker")
                    return False
                
                if not account_info.trade_expert:
                    logger.error("❌ Expert trading (auto trading) not allowed")
                    logger.error("   Please enable 'Algo Trading' in MT5")
                    return False
                
                logger.info("✅ Trading permissions OK")
        except Exception as e:
            logger.error(f"❌ Error checking permissions: {e}")
            return False
        
        # Step 5: Test symbol access
        logger.info("Step 5: Testing symbol access...")
        try:
            symbols = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
            for symbol in symbols:
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info:
                    logger.info(f"✅ {symbol}: {symbol_info.description}")
                    if not symbol_info.visible:
                        logger.warning(f"⚠️ {symbol} not visible in market watch")
                else:
                    logger.error(f"❌ {symbol}: Not available")
        except Exception as e:
            logger.error(f"❌ Error checking symbols: {e}")
        
        logger.info("=== MT5 DIAGNOSTIC COMPLETE ===")
        logger.info("✅ All MT5 checks passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ MT5 diagnostic failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    print("Running MT5 Diagnostic...")
    success = diagnose_mt5()
    
    if success:
        print("\nAll MT5 checks passed!")
        print("Your trading engine should be able to connect.")
    else:
        print("\nMT5 connection issues detected!")
        print("Check the diagnostic logs above for details.")
