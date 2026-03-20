"""
Simple ASCII MT5 Connection Test
Test MT5 integration without Unicode issues
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

def test_mt5_connection():
    """Test MT5 connection and basic operations"""
    print("Testing MT5 Connection...")
    
    try:
        # Import MT5 connector
        from brokers.mt5_connector import MT5Connector
        
        # Initialize MT5 connector
        mt5 = MT5Connector()
        
        # Test connection (without credentials first)
        print("Connecting to MT5...")
        success = mt5.initialize()
        
        if not success:
            print("FAILED: Could not connect to MT5")
            print("Make sure:")
            print("   1. MetaTrader 5 is running")
            print("   2. 'Algo Trading' is enabled")
            print("   3. You're logged into a DEMO account")
            return False
        
        print("SUCCESS: MT5 Connected successfully!")
        
        # Test account info
        print("\nTesting Account Info...")
        account_info = mt5.get_account_info()
        
        if 'error' not in account_info:
            print(f"Account: {account_info['login']}")
            print(f"Balance: ${account_info['balance']:.2f}")
            print(f"Equity: ${account_info['equity']:.2f}")
            print(f"Leverage: 1:{account_info['leverage']}")
            print("SUCCESS: Account info retrieved!")
        else:
            print(f"ERROR: {account_info['error']}")
        
        # Test symbol info
        print("\nTesting Symbol Info...")
        symbol_info = mt5.get_symbol_info('EURUSD')
        
        if 'error' not in symbol_info:
            print(f"EURUSD Digits: {symbol_info['digits']}")
            print(f"EURUSD Point: {symbol_info['point']}")
            print(f"EURUSD Spread: {symbol_info['spread']} points")
            print("SUCCESS: Symbol info retrieved!")
        else:
            print(f"ERROR: {symbol_info['error']}")
        
        # Test current price
        print("\nTesting Current Price...")
        current_price = mt5.get_current_price('EURUSD')
        
        if 'error' not in current_price:
            print(f"EURUSD Bid: {current_price['bid']:.5f}")
            print(f"EURUSD Ask: {current_price['ask']:.5f}")
            print(f"EURUSD Spread: {current_price['ask'] - current_price['bid']:.5f}")
            print("SUCCESS: Current price retrieved!")
        else:
            print(f"ERROR: {current_price['error']}")
        
        # Disconnect
        mt5.disconnect()
        print("\nMT5 Disconnected")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Main test function"""
    print("MT5 Connection Test for BrayoForexBot")
    print("=" * 50)
    
    success = test_mt5_connection()
    
    print("\n" + "=" * 50)
    print("MT5 TEST SUMMARY")
    print("=" * 50)
    
    if success:
        print("SUCCESS: MT5 integration is working!")
        print("Ready for live trading with demo account!")
        print("\nNext steps:")
        print("1. Open MetaTrader 5")
        print("2. Enable 'Algo Trading'")
        print("3. Login to DEMO account")
        print("4. Run: python testing/mt5_connection_test.py")
    else:
        print("FAILED: MT5 integration has issues")
        print("Check:")
        print("1. MT5 is running")
        print("2. Algo Trading is enabled")
        print("3. You're logged in")
        print("4. Network connection")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
