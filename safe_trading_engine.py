"""
Safe Trading Engine - Better error handling for stability
"""
import time
import json
import logging
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'brokers'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'dashboard'))

# Force reload of modules
import importlib
if sys.modules.get('trade_manager'):
    importlib.reload(sys.modules['trade_manager'])
if sys.modules.get('mt5_connector'):
    importlib.reload(sys.modules['mt5_connector'])

from mt5_connector import MT5Connector
from trade_manager import TradeManager
from integrated_scanner import IntegratedScanner

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SafeTradingEngine:
    """Safer trading engine with better error handling"""
    
    def __init__(self):
        self.running = False
        self.mt5_connector = None
        self.trade_manager = None
        self.scanner = None
        self.shared_state_file = "trading_state.json"
        
    def initialize(self):
        """Initialize with maximum safety"""
        try:
            print("🚀 Initializing Safe Trading Engine...")
            
            # Step 1: Initialize MT5
            print("📡 Connecting to MT5...")
            self.mt5_connector = MT5Connector()
            
            if not self.mt5_connector.initialize():
                print("❌ Failed to connect to MT5")
                print("Please ensure MetaTrader 5 is running and 'Algo Trading' is enabled")
                return False
            
            print("✅ MT5 Connected Successfully")
            
            # Step 2: Initialize Trade Manager
            print("📊 Initializing Trade Manager...")
            self.trade_manager = TradeManager(self.mt5_connector)
            print("✅ Trade Manager initialized")
            
            # Step 3: Initialize Scanner
            print("🔍 Initializing Integrated Scanner...")
            self.scanner = IntegratedScanner()
            self.scanner.mt5_connector = self.mt5_connector
            print("✅ Scanner initialized with shared MT5 connection")
            
            # Step 4: Initialize Auto Trading
            print("🤖 Initializing Auto Trading...")
            auto_trading_initialized = self.scanner.initialize_auto_trading(self.trade_manager)
            if auto_trading_initialized:
                print("✅ Auto Trading initialized")
                # Configure auto trading
                auto_trading_config = {
                    'enabled': True,
                    'min_confidence': 60,  # Changed from 50% to 60% for better trade quality
                    'max_trades': 3,
                    'cooldown_minutes': 5,
                    'risk_per_trade': 1.0
                }
                self.scanner.auto_trading_manager.update_config(**auto_trading_config)
                print("📊 Auto Trading Settings:")
                print("   • Min Confidence: {}%".format(auto_trading_config['min_confidence']))
                print("   • Max Trades: {}".format(auto_trading_config['max_trades']))
                print("   • Cooldown: {} minutes".format(auto_trading_config['cooldown_minutes']))
                print("   • Risk per Trade: {}%".format(auto_trading_config['risk_per_trade']))
            else:
                print("⚠️ Auto Trading initialization failed")
            
            print("✅ Safe Trading Engine Initialized")
            return True
            
        except Exception as e:
            print(f"❌ Initialization Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_safe_loop(self):
        """Safe trading loop with maximum error handling"""
        try:
            print("🔄 Starting Safe Trading Loop...")
            print("📝 Engine will run continuously")
            print("🛑 Press CTRL+C to stop trading engine")
            print("=" * 50)
            
            loop_count = 0
            while self.running:
                try:
                    loop_count += 1
                    
                    # Simple status check every 10 loops
                    if loop_count % 10 == 0:
                        print(f"📊 Loop {loop_count}: Engine running normally")
                        
                        # Check MT5 connection
                        if self.mt5_connector and hasattr(self.mt5_connector, 'connected'):
                            if self.mt5_connector.connected:
                                print("✅ MT5 connection: OK")
                            else:
                                print("⚠️ MT5 connection: Lost")
                                # Try to reconnect
                                if self.mt5_connector.initialize():
                                    print("✅ MT5 reconnected successfully")
                                else:
                                    print("❌ MT5 reconnection failed")
                        
                        # Check scanner status
                        if self.scanner and hasattr(self.scanner, 'running'):
                            if self.scanner.running:
                                print("✅ Scanner: Running")
                            else:
                                print("⚠️ Scanner: Stopped")
                                # Try to restart scanner
                                try:
                                    self.scanner.start_background_scanner()
                                    print("✅ Scanner restarted")
                                except Exception as e:
                                    print(f"❌ Scanner restart failed: {e}")
                    
                    # Simple sleep to prevent CPU overload
                    time.sleep(1)
                    
                except KeyboardInterrupt:
                    print("\n🛑 Trading Engine Stopped by User")
                    break
                except Exception as e:
                    print(f"❌ Loop Error: {e}")
                    print("⏳ Continuing after error...")
                    time.sleep(5)  # Wait longer on error
                    
        except Exception as e:
            print(f"❌ Critical Loop Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def start(self):
        """Start the safe trading engine"""
        print("🚀 Starting Safe Trading Engine...")
        self.running = True
        
        if self.initialize():
            self.run_safe_loop()
        else:
            print("❌ Failed to initialize trading engine")
    
    def stop(self):
        """Stop the trading engine"""
        print("🛑 Stopping Safe Trading Engine...")
        self.running = False
    
    def cleanup(self):
        """Clean shutdown"""
        try:
            print("🧹 Cleaning up...")
            
            # Stop scanner
            if self.scanner:
                self.scanner.stop()
                print("✅ Scanner stopped")
            
            # Disconnect MT5
            if self.mt5_connector:
                self.mt5_connector.disconnect()
                print("✅ MT5 disconnected")
            
            print("✅ Cleanup complete")
            
        except Exception as e:
            print(f"❌ Cleanup Error: {e}")

def main():
    """Main function"""
    try:
        engine = SafeTradingEngine()
        engine.start()
    except KeyboardInterrupt:
        print("\n🛑 Program interrupted by user")
    except Exception as e:
        print(f"❌ Program Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
