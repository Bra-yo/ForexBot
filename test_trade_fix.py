"""
Test Trade Manager Fix
"""
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'brokers'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'dashboard'))

from mt5_connector import MT5Connector
from trade_manager import TradeManager

def test_trade_manager():
    """Test the TradeManager place_trade method"""
    print("Testing TradeManager fix...")
    
    try:
        # Initialize MT5
        mt5_connector = MT5Connector()
        if not mt5_connector.initialize():
            print("Failed to connect to MT5")
            return False
        
        print("MT5 Connected Successfully")
        
        # Create TradeManager
        trade_manager = TradeManager(mt5_connector)
        print("TradeManager created")
        
        # Test place_trade method existence
        if hasattr(trade_manager, 'place_trade'):
            print("place_trade method exists")
            
            # Check method signature
            import inspect
            sig = inspect.signature(trade_manager.place_trade)
            print(f"Method signature: {sig}")
            
            # Test method call (without actually placing trade)
            print("Testing method call...")
            try:
                result = trade_manager.place_trade(
                    symbol="EURUSD",
                    trade_type="BUY",
                    lot_size=0.01,
                    sl=1.0,
                    tp=1.1,
                    current_price=1.05
                )
                print(f"Method call successful: {result}")
                return True
            except Exception as e:
                print(f"Method call failed: {e}")
                return False
        else:
            print("place_trade method still missing!")
            return False
            
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_trade_manager()
    if success:
        print("\nTradeManager fix verified!")
        print("Auto trading should work now.")
    else:
        print("\nTradeManager fix failed!")
        print("Need to check on method implementation.")
