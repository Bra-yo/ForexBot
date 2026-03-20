"""
MT5 Connection and Trading Test
Test MT5 integration with safe demo operations
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from brokers.mt5_connector import MT5Connector
from brokers.mt5_data_reader import MT5DataReader
from brokers.mt5_order_executor import MT5OrderExecutor, OrderRequest, OrderType
from brokers.mt5_streaming import MT5Streamer
import time
from datetime import datetime

def test_mt5_connection():
    """Test MT5 connection and basic operations"""
    print("🔗 Testing MT5 Connection...")
    
    try:
        # Initialize MT5 connector
        mt5 = MT5Connector()
        
        # Test connection (without credentials first)
        print("📡 Connecting to MT5...")
        success = mt5.initialize()
        
        if not success:
            print("❌ Failed to connect to MT5")
            print("💡 Make sure:")
            print("   1. MetaTrader 5 is running")
            print("   2. 'Algo Trading' is enabled")
            print("   3. You're logged into a DEMO account")
            return False
        
        print("✅ MT5 Connected successfully!")
        
        # Test account info
        print("\n📊 Testing Account Info...")
        account_info = mt5.get_account_info()
        
        if 'error' not in account_info:
            print(f"💰 Account: {account_info['login']}")
            print(f"💵 Balance: ${account_info['balance']:.2f}")
            print(f"📊 Equity: ${account_info['equity']:.2f}")
            print(f"🏦 Leverage: 1:{account_info['leverage']}")
            print("✅ Account info retrieved successfully!")
        else:
            print(f"❌ Error getting account info: {account_info['error']}")
        
        # Test symbol info
        print("\n📈 Testing Symbol Info...")
        symbol_info = mt5.get_symbol_info('EURUSD')
        
        if 'error' not in symbol_info:
            print(f"📊 EURUSD Info:")
            print(f"   Digits: {symbol_info['digits']}")
            print(f"   Point: {symbol_info['point']}")
            print(f"   Spread: {symbol_info['spread']} points")
            print("✅ Symbol info retrieved successfully!")
        else:
            print(f"❌ Error getting symbol info: {symbol_info['error']}")
        
        # Test current price
        print("\n💹 Testing Current Price...")
        current_price = mt5.get_current_price('EURUSD')
        
        if 'error' not in current_price:
            print(f"💹 EURUSD Current Price:")
            print(f"   Bid: {current_price['bid']:.5f}")
            print(f"   Ask: {current_price['ask']:.5f}")
            print(f"   Spread: {current_price['ask'] - current_price['bid']:.5f}")
            print("✅ Current price retrieved successfully!")
        else:
            print(f"❌ Error getting current price: {current_price['error']}")
        
        # Test historical data
        print("\n📊 Testing Historical Data...")
        data_reader = MT5DataReader(mt5)
        
        try:
            # Get recent data
            historical_data = data_reader.get_latest_data('EURUSD', 'H1', bars=10)
            
            if not historical_data.empty:
                print(f"✅ Retrieved {len(historical_data)} hourly candles")
                print(f"📅 Date range: {historical_data.index[0]} to {historical_data.index[-1]}")
                print(f"💹 Price range: {historical_data['low'].min():.5f} - {historical_data['high'].max():.5f}")
                print("✅ Historical data retrieved successfully!")
            else:
                print("❌ No historical data retrieved")
                
        except Exception as e:
            print(f"❌ Error getting historical data: {e}")
        
        # Disconnect
        mt5.disconnect()
        print("\n👋 MT5 Disconnected")
        return True
        
    except Exception as e:
        print(f"❌ MT5 Connection Test Error: {e}")
        return False

def test_mt5_paper_trading():
    """Test MT5 paper trading with very small positions"""
    print("\n📝 Testing MT5 Paper Trading...")
    print("⚠️  Using very small test positions (0.01 lots)")
    
    try:
        # Initialize components
        mt5 = MT5Connector()
        
        if not mt5.initialize():
            print("❌ Cannot test paper trading - MT5 not connected")
            return False
        
        print("✅ MT5 Connected for paper trading test")
        
        # Initialize components
        data_reader = MT5DataReader(mt5)
        order_executor = MT5OrderExecutor(mt5)
        
        # Start execution thread
        order_executor.start_execution_thread()
        
        # Get current price
        current_price = mt5.get_current_price('EURUSD')
        if 'error' in current_price:
            print("❌ Cannot get current price for paper trading")
            mt5.disconnect()
            return False
        
        print(f"💹 Current EURUSD Price: {current_price['bid']:.5f} / {current_price['ask']:.5f}")
        
        # Test 1: Place very small buy order
        print("\n🔄 Testing Small Buy Order...")
        
        buy_request = OrderRequest(
            symbol='EURUSD',
            order_type=OrderType.BUY,
            volume=0.01,  # Minimum size
            stop_loss=current_price['bid'] * 0.998,  # 20 pips SL
            take_profit=current_price['bid'] * 1.002,  # 20 pips TP
            comment='Paper-Test-Buy'
        )
        
        buy_result = order_executor.place_market_order(buy_request)
        
        if buy_result['success']:
            print(f"✅ Buy order placed: #{buy_result.get('order')}")
            
            # Wait a moment
            time.sleep(2)
            
            # Check position
            positions = order_executor.get_open_positions()
            buy_position = None
            
            for pos in positions:
                if pos['symbol'] == 'EURUSD' and pos['type'] == 0:  # BUY
                    buy_position = pos
                    break
            
            if buy_position:
                print(f"📊 Position found: {buy_position['volume']} lots at {buy_position['price_open']}")
                print(f"💰 Current P&L: ${buy_position['profit']:.2f}")
                
                # Test 2: Close the position
                print("\n🔄 Testing Position Close...")
                close_result = order_executor.close_position(buy_position['ticket'])
                
                if close_result['success']:
                    print(f"✅ Position closed: Final P&L ${buy_position['profit']:.2f}")
                else:
                    print(f"❌ Failed to close position: {close_result['error']}")
            else:
                print("❌ Position not found after order placement")
        else:
            print(f"❌ Buy order failed: {buy_result['error']}")
        
        # Stop execution thread
        order_executor.stop_execution_thread()
        
        # Disconnect
        mt5.disconnect()
        print("\n👋 Paper trading test completed")
        return True
        
    except Exception as e:
        print(f"❌ Paper Trading Test Error: {e}")
        try:
            mt5.disconnect()
        except:
            pass
        return False

def test_mt5_streaming():
    """Test MT5 real-time data streaming"""
    print("\n🔄 Testing MT5 Real-time Streaming...")
    
    try:
        # Initialize components
        mt5 = MT5Connector()
        
        if not mt5.initialize():
            print("❌ Cannot test streaming - MT5 not connected")
            return False
        
        print("✅ MT5 Connected for streaming test")
        
        # Initialize streamer
        streamer = MT5Streamer(mt5)
        
        # Test tick streaming
        print("\n📡 Testing Tick Streaming...")
        
        tick_count = 0
        def on_tick(tick):
            nonlocal tick_count
            tick_count += 1
            if tick_count <= 3:  # Show first few ticks
                print(f"📊 Tick {tick_count}: {tick.bid:.5f} / {tick.ask:.5f}")
        
        # Subscribe to ticks
        streamer.subscribe_to_ticks('EURUSD', on_tick)
        
        # Wait for ticks
        print("⏳ Waiting for ticks (10 seconds)...")
        time.sleep(10)
        
        # Unsubscribe
        streamer.unsubscribe_from_ticks('EURUSD')
        
        if tick_count > 0:
            print(f"✅ Received {tick_count} ticks successfully!")
        else:
            print("❌ No ticks received")
        
        # Test bar streaming
        print("\n📊 Testing Bar Streaming...")
        
        bar_count = 0
        def on_bar(bar):
            nonlocal bar_count
            bar_count += 1
            if bar_count <= 2:  # Show first few bars
                print(f"📊 Bar {bar_count}: O:{bar.open:.5f} H:{bar.high:.5f} L:{bar.low:.5f} C:{bar.close:.5f}")
        
        # Subscribe to bars
        streamer.subscribe_to_bars('EURUSD', 'M1', on_bar)
        
        # Wait for bars
        print("⏳ Waiting for bars (30 seconds)...")
        time.sleep(30)
        
        # Unsubscribe
        streamer.unsubscribe_from_bars('EURUSD', 'M1')
        
        if bar_count > 0:
            print(f"✅ Received {bar_count} bars successfully!")
        else:
            print("❌ No bars received")
        
        # Stop streaming
        streamer.stop_streaming()
        
        # Disconnect
        mt5.disconnect()
        print("\n👋 Streaming test completed")
        return True
        
    except Exception as e:
        print(f"❌ Streaming Test Error: {e}")
        try:
            mt5.disconnect()
        except:
            pass
        return False

def run_mt5_tests():
    """Run all MT5 tests"""
    print("🚀 Starting MT5 Integration Tests")
    print("=" * 60)
    print("⚠️  IMPORTANT: Use DEMO account only!")
    print("⚠️  Make sure MT5 is running with Algo Trading enabled")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Basic connection
    results['connection'] = test_mt5_connection()
    
    # Test 2: Paper trading (only if connection works)
    if results.get('connection'):
        results['paper_trading'] = test_mt5_paper_trading()
        results['streaming'] = test_mt5_streaming()
    else:
        results['paper_trading'] = False
        results['streaming'] = False
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 MT5 TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in results.items():
        status_icon = "✅" if result else "❌"
        print(f"{status_icon} {test_name.replace('_', ' ').title()}")
    
    successful_tests = sum(results.values())
    total_tests = len(results)
    
    print(f"\n📈 Results: {successful_tests}/{total_tests} tests passed")
    
    if successful_tests == total_tests:
        print("🎉 EXCELLENT! MT5 integration fully functional!")
        print("🚀 Ready for live trading with demo account!")
    elif successful_tests >= 2:
        print("✅ GOOD! MT5 integration mostly functional.")
        print("🔧 Minor issues to address.")
    else:
        print("🚨 POOR! MT5 integration has significant issues.")
        print("🛠️ Check MT5 setup and connection.")
    
    print("\n💡 Next Steps:")
    print("1. Ensure MT5 is running with demo account")
    print("2. Enable 'Algo Trading' in MT5")
    print("3. Check internet connection")
    print("4. Verify broker server status")
    
    print("=" * 60)

if __name__ == "__main__":
    run_mt5_tests()
