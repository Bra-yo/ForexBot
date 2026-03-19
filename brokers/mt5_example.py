"""
MT5 Integration Example for BrayoForexBot
Shows how to use the professional MT5 trading system
"""

import os
import time
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Import MT5 components
from mt5_trading_engine import MT5TradingEngine
from risk_management import RiskManager
from notifications import NotificationManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def demo_mt5_connection():
    """Demo MT5 connection and basic operations"""
    print("\n🔗 MT5 CONNECTION DEMO")
    print("=" * 50)
    
    # Create MT5 trading engine
    engine = MT5TradingEngine()
    
    try:
        # Initialize MT5 (use demo account for safety)
        print("📡 Connecting to MT5...")
        
        # For demo, try without credentials first (will use existing terminal)
        success = engine.initialize_mt5()
        
        if not success:
            print("❌ Failed to connect to MT5")
            print("💡 Make sure:")
            print("   1. MetaTrader 5 is running")
            print("   2. 'Algo Trading' is enabled")
            print("   3. You're logged into a demo account")
            return False
        
        print("✅ Connected to MT5 successfully!")
        
        # Get account info
        account_info = engine.mt5_connector.get_account_info()
        if 'error' not in account_info:
            print(f"💰 Account: {account_info['login']}")
            print(f"💵 Balance: ${account_info['balance']:.2f}")
            print(f"📊 Equity: ${account_info['equity']:.2f}")
            print(f"🏦 Leverage: 1:{account_info['leverage']}")
        
        # Get symbol info
        symbol_info = engine.mt5_connector.get_symbol_info('EURUSD')
        if 'error' not in symbol_info:
            print(f"📈 EURUSD Info:")
            print(f"   Digits: {symbol_info['digits']}")
            print(f"   Point: {symbol_info['point']}")
            print(f"   Spread: {symbol_info['spread']} points")
        
        # Get current price
        current_price = engine.mt5_connector.get_current_price('EURUSD')
        if 'error' not in current_price:
            print(f"💹 EURUSD Current Price:")
            print(f"   Bid: {current_price['bid']:.5f}")
            print(f"   Ask: {current_price['ask']:.5f}")
            print(f"   Spread: {current_price['ask'] - current_price['bid']:.5f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in MT5 connection demo: {e}")
        return False
    
    finally:
        # Disconnect
        engine.mt5_connector.disconnect()

def demo_historical_data():
    """Demo historical data retrieval"""
    print("\n📊 HISTORICAL DATA DEMO")
    print("=" * 50)
    
    engine = MT5TradingEngine()
    
    try:
        # Initialize MT5
        if not engine.initialize_mt5():
            print("❌ Failed to connect to MT5")
            return False
        
        # Get historical data
        print("📈 Getting historical data for EURUSD...")
        
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        data = engine.mt5_data_reader.get_historical_data(
            'EURUSD', 'H1', start_date, end_date
        )
        
        if not data.empty:
            print(f"✅ Retrieved {len(data)} hourly candles")
            print(f"📅 Date range: {data.index[0]} to {data.index[-1]}")
            print(f"💹 Price range: {data['low'].min():.5f} - {data['high'].max():.5f}")
            print(f"📊 Sample data:")
            print(data.head())
        else:
            print("❌ No historical data retrieved")
        
        # Get latest data
        print("\n📈 Getting latest data...")
        latest_data = engine.mt5_data_reader.get_latest_data('EURUSD', 'M1', bars=10)
        
        if not latest_data.empty:
            print(f"✅ Retrieved {len(latest_data)} latest M1 candles")
            print(f"🕐 Latest candle: {latest_data.index[-1]}")
            print(f"💹 Latest prices: O:{latest_data['open'].iloc[-1]:.5f} H:{latest_data['high'].iloc[-1]:.5f} L:{latest_data['low'].iloc[-1]:.5f} C:{latest_data['close'].iloc[-1]:.5f}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in historical data demo: {e}")
        return False
    
    finally:
        engine.mt5_connector.disconnect()

def demo_real_time_streaming():
    """Demo real-time streaming (short duration)"""
    print("\n🔄 REAL-TIME STREAMING DEMO")
    print("=" * 50)
    
    engine = MT5TradingEngine()
    
    try:
        # Initialize MT5
        if not engine.initialize_mt5():
            print("❌ Failed to connect to MT5")
            return False
        
        # Start real-time trading
        symbols = ['EURUSD']
        timeframes = ['M1', 'M5']
        
        print(f"🚀 Starting real-time streaming for {symbols}...")
        
        success = engine.start_real_time_trading(symbols, timeframes)
        
        if not success:
            print("❌ Failed to start real-time trading")
            return False
        
        # Monitor for 30 seconds
        print("⏱️ Monitoring for 30 seconds...")
        
        for i in range(30):
            # Get streaming stats
            stats = engine.mt5_streamer.get_streaming_stats()
            
            if i % 5 == 0:  # Print every 5 seconds
                print(f"📊 Ticks received: {stats['ticks_received']}")
                print(f"📈 Bars generated: {stats['bars_generated']}")
                print(f"📡 Active symbols: {stats['active_symbols']}")
                
                # Get latest tick
                latest_tick = engine.mt5_streamer.get_latest_tick('EURUSD')
                if latest_tick:
                    print(f"💹 Latest tick: {latest_tick.bid:.5f} / {latest_tick.ask:.5f}")
                
                print("-" * 30)
            
            time.sleep(1)
        
        # Stop streaming
        engine.stop_real_time_trading()
        print("✅ Streaming stopped")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in streaming demo: {e}")
        return False
    
    finally:
        engine.mt5_connector.disconnect()

def demo_paper_trading():
    """Demo paper trading with small test positions"""
    print("\n📝 PAPER TRADING DEMO")
    print("=" * 50)
    
    # Create components
    risk_manager = RiskManager(initial_balance=10000)
    notifications = NotificationManager()
    engine = MT5TradingEngine(risk_manager)
    
    try:
        # Initialize MT5
        if not engine.initialize_mt5():
            print("❌ Failed to connect to MT5")
            return False
        
        # Start real-time trading
        symbols = ['EURUSD']
        
        print(f"🚀 Starting paper trading for {symbols}...")
        
        success = engine.start_real_time_trading(symbols, ['M1', 'M5'])
        
        if not success:
            print("❌ Failed to start paper trading")
            return False
        
        # Monitor for 60 seconds
        print("⏱️ Paper trading for 60 seconds...")
        print("⚠️  This will place very small test positions (0.01 lots)")
        
        start_time = time.time()
        
        while time.time() - start_time < 60:
            try:
                # Analyze EURUSD
                decision = engine.analyze_symbol_real_time('EURUSD', 'M1')
                
                if decision and decision.action in ['BUY', 'SELL']:
                    print(f"\n🎯 Trading Signal: {decision.action} EURUSD")
                    print(f"💰 Confidence: {decision.confidence:.1f}%")
                    print(f"💹 Entry: {decision.entry_price:.5f}")
                    print(f"🛑 SL: {decision.stop_loss:.5f}")
                    print(f"🎯 TP: {decision.take_profit:.5f}")
                    print(f"📊 Position size: {decision.position_size} lots")
                    print(f"📝 Reasons: {', '.join(decision.reasons[:3])}")
                    
                    # Execute paper trade
                    result = engine.execute_mt5_trade(decision)
                    
                    if result['success']:
                        print(f"✅ Trade executed: Order #{result.get('order')}")
                    else:
                        print(f"❌ Trade failed: {result['error']}")
                
                # Manage positions
                engine.manage_mt5_positions()
                
                # Get account summary
                if int(time.time() - start_time) % 20 == 0:  # Every 20 seconds
                    summary = engine.get_mt5_account_summary()
                    
                    if 'error' not in summary:
                        print(f"\n📊 Account Summary:")
                        print(f"💰 Balance: ${summary['account']['balance']:.2f}")
                        print(f"📊 Equity: ${summary['account']['equity']:.2f}")
                        print(f"📋 Open positions: {summary['positions']['count']}")
                        print(f"💸 Unrealized P&L: ${summary['positions']['unrealized_pnl']:.2f}")
                
                time.sleep(2)
                
            except KeyboardInterrupt:
                print("\n👋 Paper trading interrupted")
                break
        
        # Close all positions
        print("\n🔄 Closing all positions...")
        positions = engine.mt5_order_executor.get_open_positions()
        
        for position in positions:
            close_result = engine.mt5_order_executor.close_position(position.ticket)
            if close_result['success']:
                print(f"✅ Closed position {position.ticket}")
            else:
                print(f"❌ Failed to close position {position.ticket}")
        
        # Final summary
        final_summary = engine.get_mt5_account_summary()
        
        if 'error' not in final_summary:
            print(f"\n📊 Final Summary:")
            print(f"💰 Final Balance: ${final_summary['account']['balance']:.2f}")
            print(f"📊 Final Equity: ${final_summary['account']['equity']:.2f}")
            print(f"📈 Total P&L: ${final_summary['account']['profit']:.2f}")
            print(f"📊 Orders placed: {final_summary['execution_stats']['orders_placed']}")
            print(f"✅ Orders executed: {final_summary['execution_stats']['orders_executed']}")
        
        # Stop trading
        engine.stop_real_time_trading()
        print("✅ Paper trading completed")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in paper trading demo: {e}")
        return False
    
    finally:
        engine.mt5_connector.disconnect()

def demo_performance_monitoring():
    """Demo performance monitoring and analytics"""
    print("\n📈 PERFORMANCE MONITORING DEMO")
    print("=" * 50)
    
    engine = MT5TradingEngine()
    
    try:
        # Initialize MT5
        if not engine.initialize_mt5():
            print("❌ Failed to connect to MT5")
            return False
        
        # Start streaming
        symbols = ['EURUSD', 'GBPUSD']
        engine.start_real_time_trading(symbols, ['M1', 'M5'])
        
        print(f"📊 Monitoring performance for {symbols}...")
        
        # Monitor for 30 seconds
        for i in range(30):
            # Get account summary
            summary = engine.get_mt5_account_summary()
            
            if 'error' not in summary:
                print(f"\n📊 Performance Update ({i+1}/30):")
                print(f"💰 Account Balance: ${summary['account']['balance']:.2f}")
                print(f"📊 Equity: ${summary['account']['equity']:.2f}")
                print(f"📋 Open Positions: {summary['positions']['count']}")
                print(f"💸 Unrealized P&L: ${summary['positions']['unrealized_pnl']:.2f}")
                
                # Streaming stats
                streaming = summary['streaming_stats']
                print(f"📡 Ticks: {streaming['ticks_received']} | Bars: {streaming['bars_generated']}")
                
                # Execution stats
                execution = summary['execution_stats']
                print(f"📈 Orders: {execution['orders_placed']} placed, {execution['orders_executed']} executed")
                
                if summary['positions']['symbols']:
                    print(f"📈 Active symbols: {', '.join(summary['positions']['symbols'])}")
            
            time.sleep(1)
        
        # Stop streaming
        engine.stop_real_time_trading()
        print("✅ Performance monitoring completed")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in performance monitoring demo: {e}")
        return False
    
    finally:
        engine.mt5_connector.disconnect()

def main():
    """Main demo function"""
    print("🚀 MT5 INTEGRATION DEMO")
    print("=" * 60)
    print("⚠️  IMPORTANT SAFETY NOTES:")
    print("   1. Use DEMO account only!")
    print("   2. Start with connection test first")
    print("   3. Paper trading uses real market data")
    print("   4. Positions are very small (0.01 lots)")
    print("   5. Monitor closely and stop if needed")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv()
    
    demos = [
        ("MT5 Connection", demo_mt5_connection),
        ("Historical Data", demo_historical_data),
        ("Real-Time Streaming", demo_real_time_streaming),
        ("Paper Trading", demo_paper_trading),
        ("Performance Monitoring", demo_performance_monitoring)
    ]
    
    for name, demo_func in demos:
        try:
            print(f"\n{'='*60}")
            print(f"🎯 STARTING: {name}")
            print(f"{'='*60}")
            
            success = demo_func()
            
            if success:
                print(f"\n✅ {name} completed successfully!")
            else:
                print(f"\n❌ {name} failed!")
            
            # Ask user if they want to continue
            if name != demos[-1][0]:  # Not the last demo
                response = input(f"\nContinue to next demo? (y/n): ").lower()
                if response != 'y':
                    print("👋 Demo stopped by user")
                    break
            
            print(f"\n{'='*60}")
            
        except KeyboardInterrupt:
            print(f"\n👋 {name} interrupted by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error in {name}: {e}")
            print(f"\n❌ {name} failed with error: {e}")
    
    print(f"\n🎉 MT5 DEMO COMPLETED!")
    print("📚 Next steps:")
    print("   1. Test with your demo account")
    print("   2. Modify parameters as needed")
    print("   3. Integrate with your strategies")
    print("   4. Add risk management rules")

if __name__ == "__main__":
    main()
