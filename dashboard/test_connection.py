"""
🧪 Trading Engine Test - Debug Connection Issues
Tests MT5 connection and shows detailed status
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from brokers.mt5_connector import MT5Connector

def test_mt5_connection():
    """Test MT5 connection step by step"""
    print("🧪 Trading Engine Connection Test")
    print("=" * 50)
    
    try:
        print("📡 Step 1: Creating MT5Connector...")
        connector = MT5Connector()
        print("✅ MT5Connector created")
        
        print("\n📡 Step 2: Attempting connection...")
        result = connector.initialize()
        print(f"📊 Connection result: {result}")
        
        if result:
            print("\n✅ SUCCESS: MT5 Connected!")
            
            print("\n📡 Step 3: Getting account info...")
            account_info = connector.get_account_info()
            
            if 'error' not in account_info:
                print(f"✅ Account: {account_info.get('login', 'N/A')}")
                print(f"✅ Balance: ${account_info.get('balance', 0):.2f}")
                print(f"✅ Equity: ${account_info.get('equity', 0):.2f}")
                print(f"✅ Server: {account_info.get('server', 'N/A')}")
                
                print("\n📡 Step 4: Testing symbol info...")
                symbol_info = connector.get_symbol_info('EURUSD')
                if 'error' not in symbol_info:
                    print(f"✅ EURUSD: {symbol_info.get('description', 'N/A')}")
                    print(f"✅ Digits: {symbol_info.get('digits', 'N/A')}")
                    print(f"✅ Spread: {symbol_info.get('spread', 'N/A')}")
                else:
                    print(f"❌ Symbol info error: {symbol_info['error']}")
                    
            else:
                print(f"❌ Account info error: {account_info['error']}")
                
        else:
            print("\n❌ FAILED: MT5 Connection failed!")
            print("\n💡 Troubleshooting:")
            print("   1. Is MetaTrader 5 running?")
            print("   2. Are you logged into MT5?")
            print("   3. Is 'Algo Trading' enabled?")
            print("   4. Is MT5 path correct?")
            
            # Try to get MT5 error
            import MetaTrader5 as mt5
            error = mt5.last_error()
            if error:
                print(f"\n🚨 MT5 Error: {error}")
        
        print("\n📡 Step 5: Testing disconnect...")
        connector.disconnect()
        print("✅ Disconnected")
        
    except Exception as e:
        print(f"\n❌ Test Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mt5_connection()
    print("\n🎯 Test complete!")
    input("Press any key to exit...")
