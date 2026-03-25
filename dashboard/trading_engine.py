"""
🤖 BrayoForexBot - Independent Trading Engine
Runs continuously, independent of UI
"""
import time
import json
import threading
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from brokers.mt5_connector import MT5Connector
from trade_manager import TradeManager
from integrated_scanner import IntegratedScanner
import pandas as pd
import numpy as np

# Simple technical analysis functions (standalone)
def calculate_rsi(data, period=14):
    """Calculate RSI indicator"""
    try:
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except:
        return pd.Series([50] * len(data), index=data.index)

def calculate_sma(data, period=20):
    """Calculate Simple Moving Average"""
    try:
        return data.rolling(window=period).mean()
    except:
        return pd.Series([data.mean()] * len(data), index=data.index)

def calculate_ema(data, period=20):
    """Calculate Exponential Moving Average"""
    try:
        return data.ewm(span=period).mean()
    except:
        return pd.Series([data.mean()] * len(data), index=data.index)

def calculate_atr(data, period=14):
    """Calculate Average True Range"""
    try:
        high_low = data['high'] - data['low']
        high_close = abs(data['high'] - data['close'].shift())
        low_close = abs(data['low'] - data['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=period).mean()
    except:
        return pd.Series([0.001] * len(data), index=data.index)

def generate_signal(latest_rsi, latest_sma, latest_ema, current_price, historical_data):
    """Generate trading signal based on technical indicators"""
    signal_strength = 0
    reasons = []
    
    # RSI analysis
    if latest_rsi < 30:
        signal_strength += 2
        reasons.append("RSI oversold condition")
    elif latest_rsi > 70:
        signal_strength -= 2
        reasons.append("RSI overbought condition")
    
    # Trend analysis
    if latest_ema > latest_sma:
        signal_strength += 1
        reasons.append("EMA above SMA (uptrend)")
    elif latest_ema < latest_sma:
        signal_strength -= 1
        reasons.append("EMA below SMA (downtrend)")
    
    # Price vs moving averages
    if current_price > latest_ema:
        signal_strength += 1
        reasons.append("Price above EMA")
    elif current_price < latest_ema:
        signal_strength -= 1
        reasons.append("Price below EMA")
    
    # Determine decision
    if signal_strength >= 3:
        decision = "STRONG BUY"
    elif signal_strength >= 1:
        decision = "BUY"
    elif signal_strength >= -1:
        decision = "HOLD"
    elif signal_strength >= -3:
        decision = "SELL"
    else:
        decision = "STRONG SELL"
    
    return decision, reasons, abs(signal_strength)

class TradingEngine:
    def __init__(self):
        self.running = False
        self.mt5_connector = None
        self.trade_manager = None
        self.scanner = None  # Add scanner instance
        self.shared_state_file = "trading_state.json"
        self.login_credentials = None  # Will receive from dashboard
        
    def set_login_credentials(self, login, password, server):
        """Set login credentials from dashboard"""
        self.login_credentials = {
            'login': login,
            'password': password,
            'server': server
        }
        print(f"🔐 Login credentials set for account: {login}")
        
    def initialize(self):
        """Initialize MT5 connection and trading components"""
        try:
            print("🚀 Initializing Trading Engine...")
            
            # Wait for login credentials
            if not self.login_credentials:
                print("⏳ Waiting for login credentials from dashboard...")
                # Wait for credentials to be set
                while not self.login_credentials and self.running:
                    time.sleep(1)
                
                if not self.login_credentials:
                    print("❌ No login credentials provided")
                    return False
            
            # Connect to MT5
            self.mt5_connector = MT5Connector()
                    
            # Try to connect with default credentials or load from config
            print("📡 Attempting MT5 connection...")
            connection_result = self.mt5_connector.initialize()
                    
            if not connection_result:
                print("❌ Failed to connect to MT5")
                print("💡 Please check:")
                print("   1. MetaTrader 5 is running")
                print("   2. 'Algo Trading' is enabled in MT5")
                print("   3. You're logged into MT5")
                print("   4. MT5 terminal path is correct")
                return False
                        
            print("✅ MT5 Connected Successfully")
            
            # Initialize trade manager
            self.trade_manager = TradeManager(self.mt5_connector)
            
            # Initialize integrated scanner (shares MT5 connection)
            print("🔍 Initializing integrated scanner...")
            self.scanner = IntegratedScanner()
            self.scanner.mt5_connector = self.mt5_connector  # Share MT5 connection
            print("✅ Scanner initialized with shared MT5 connection")
            
            # Initialize auto trading with scanner
            print("🤖 Initializing auto trading manager...")
            auto_trading_initialized = self.scanner.initialize_auto_trading(self.trade_manager)
            if auto_trading_initialized:
                print("✅ Auto trading manager initialized")
                # Configure auto trading settings
                self.auto_trading_manager.update_config(
                    enabled=True,
                    min_confidence=50,  # Temporarily lowered to 50% for testing
                    max_trades=3,
                    cooldown_minutes=5,
                    risk_per_trade=1.0
                )
            else:
                print("⚠️ Auto trading manager failed to initialize")
            
            # Load bot settings
            self.bot_settings = self.load_settings()
            
            print("✅ Trading Engine Initialized")
            
            # Start scanner in background
            print("🚀 Starting integrated scanner (multi-pair, multi-timeframe)...")
            self.scanner.start_background_scanner()
            print("✅ Scanner running in background")
            
            # Start the main trading loop
            self.running = True
            print("🔄 Starting Trading Loop...")
            print("📝 Engine will run continuously")
            print("🛑 Press CTRL+C to stop trading engine")
            print("📊 Monitor will show real-time activity")
            print("🔍 Scanner monitoring 4 symbols × 4 timeframes = 16 combinations")
            print("=" * 50)
            
            # Add delay before starting loop to prevent immediate exit
            print("⏳ Stabilizing connection...")
            time.sleep(2)
            
            # Run trading loop
            self.run_trading_loop()
            
        except Exception as e:
            print(f"❌ Initialization Error: {e}")
            import traceback
            traceback.print_exc()
            return False
            
    def load_settings(self):
        """Load bot settings from file or use defaults"""
        try:
            with open("bot_settings.json", "r") as f:
                return json.load(f)
        except:
            # Default settings
            return {
                'trailing_stop_enabled': True,
                'trailing_profit_pips': 20,
                'min_profit_pips': 10,
                'break_even_enabled': True,
                'time_exit_enabled': True,
                'max_trade_time_minutes': 10,
                'spread_filter_enabled': True,
                'max_spread_points': 3,
                'max_daily_loss': 100.0,
                'signal_exit_enabled': True,
                'selected_currency_pair': 'EURUSD',
                'selected_timeframe': 'M15',
                'trade_type': 'BOTH'
            }
    
    def save_shared_state(self, data):
        """Save shared state for UI to read"""
        try:
            with open(self.shared_state_file, "w") as f:
                json.dump(data, f, default=str)
        except Exception as e:
            print(f"❌ Error saving state: {e}")
    
    def is_market_open(self):
        """Check if forex market is open"""
        now = datetime.now()
        weekday = now.weekday()  # 0=Monday, 6=Sunday
        hour = now.hour
        
        # Check if it's Saturday (all day)
        if weekday == 5:  # Saturday
            return False
        
        # Check if it's Sunday before 22:00 UTC
        if weekday == 6 and hour < 22:  # Sunday before 22:00 UTC
            return False
        
        # Forex market is open from Sunday 22:00 UTC to Friday 22:00 UTC
        return True
    
    def run_trading_loop(self):
        """Main trading loop - runs continuously"""
        try:
            while self.running:
                try:
                    # Check if market is open
                    market_open = self.is_market_open()
                    
                    # Prepare shared state
                    shared_state = {
                        'timestamp': datetime.now().isoformat(),
                        'market_open': market_open,
                        'mt5_connected': self.mt5_connector.connected if self.mt5_connector else False,
                        'active_trades': [],
                        'daily_loss': 0.0,
                        'signals': {},
                        'account_info': {}
                    }
                    
                    if market_open and self.mt5_connector and self.mt5_connector.connected:
                        # 🎯 CRITICAL: Sync and monitor trades EVERY loop
                        self.trade_manager.sync_with_mt5_positions()
                        closed_trades = self.trade_manager.monitor_active_trades(self.bot_settings)
                        
                        # Get account info
                        account_info = self.mt5_connector.get_account_info()
                        if 'error' not in account_info:
                            shared_state['account_info'] = account_info
                            shared_state['daily_loss'] = self.trade_manager.daily_loss
                            shared_state['active_trades'] = self.trade_manager.active_trades
                        
                        # Generate signals (less frequently - every 30 seconds)
                        if int(time.time()) % 30 == 0:
                            self.generate_signals(shared_state)
                        
                        print(f"✅ Trading Loop: {len(shared_state['active_trades'])} active trades, {len(closed_trades)} closed")
                    else:
                        print("🔴 Market closed or MT5 disconnected")
                        
                    # Save shared state for UI
                    self.save_shared_state(shared_state)
                    
                    # Sleep for 1 second (INSTANT SL/TP monitoring)
                    time.sleep(1)
                    
                except KeyboardInterrupt:
                    print("\n🛑 Trading Engine Stopped by User")
                    break
                except Exception as e:
                    print(f"❌ Trading Loop Error: {e}")
                    time.sleep(5)  # Wait longer on error
                    
        except Exception as e:
            print(f"❌ Critical Trading Engine Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()
    
    def generate_signals(self, shared_state):
        """Generate trading signals for selected currency pair"""
        try:
            symbol = self.bot_settings['selected_currency_pair']
            timeframe = self.bot_settings['selected_timeframe']
            
            # Get historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            historical_data = self.mt5_connector.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if historical_data is not None and 'error' not in historical_data:
                # Calculate indicators
                rsi = calculate_rsi(historical_data['close'], 14)
                sma = calculate_sma(historical_data['close'], 20)
                ema = calculate_ema(historical_data['close'], 20)
                
                latest_rsi = rsi.iloc[-1]
                latest_sma = sma.iloc[-1]
                latest_ema = ema.iloc[-1]
                current_price = historical_data['close'].iloc[-1]
                
                # Generate signal
                decision, reasons, signal_strength = generate_signal(
                    latest_rsi, latest_sma, latest_ema, current_price, historical_data
                )
                
                # Filter by trade type
                if self.bot_settings['trade_type'] == 'BUY_ONLY' and 'SELL' in decision:
                    decision = 'HOLD'
                elif self.bot_settings['trade_type'] == 'SELL_ONLY' and 'BUY' in decision:
                    decision = 'HOLD'
                
                shared_state['signals'] = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'decision': decision,
                    'reasons': reasons,
                    'strength': signal_strength,
                    'current_price': current_price,
                    'rsi': latest_rsi,
                    'sma': latest_sma,
                    'ema': latest_ema
                }
                
        except Exception as e:
            print(f"❌ Signal Generation Error: {e}")
    
    def start(self):
        """Start the trading engine"""
        if not self.initialize():
            return False
            
        self.running = True
        print("🚀 Trading Engine Started - Running Continuously")
        
        try:
            self.run_trading_loop()
        except KeyboardInterrupt:
            print("\n🛑 Trading Engine Stopped by User")
        except Exception as e:
            print(f"❌ Trading Engine Crash: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the trading engine"""
        self.running = False
        
        # Stop scanner first
        if self.scanner:
            print("🛑 Stopping integrated scanner...")
            self.scanner.stop_scanner()
            print("✅ Scanner stopped")
        
        if self.mt5_connector:
            self.mt5_connector.disconnect()
        print("🛑 Trading Engine Stopped")

# Global engine instance for dashboard communication
_global_engine = None

def get_global_engine():
    """Get the global trading engine instance"""
    global _global_engine
    return _global_engine

def set_global_engine(engine):
    """Set the global trading engine instance"""
    global _global_engine
    _global_engine = engine

def pass_login_to_engine(login, password, server):
    """Pass login credentials from dashboard to engine"""
    engine = get_global_engine()
    if engine:
        engine.set_login_credentials(login, password, server)
        return True
    return False

if __name__ == "__main__":
    print("🤖 BrayoForexBot - Independent Trading Engine")
    print("=" * 50)
    
    engine = TradingEngine()
    set_global_engine(engine)  # Make available for dashboard
    engine.start()
