"""
Auto Trading Manager - Controlled automatic trade execution
Integrates with scanner for automated trading based on signal quality
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class AutoTradingConfig:
    """Auto trading configuration"""
    enabled: bool = True
    min_confidence: int = 60
    max_trades: int = 3
    min_lot_size: float = 0.01
    max_lot_size: float = 1.0
    cooldown_minutes: int = 5
    risk_per_trade: float = 1.0  # Risk percentage per trade
    
class AutoTradingManager:
    """Manages automatic trade execution with safety controls"""
    
    def __init__(self, mt5_connector, trade_manager, telegram_assistant=None):
        self.mt5_connector = mt5_connector
        self.trade_manager = trade_manager
        self.telegram_assistant = telegram_assistant
        
        # Configuration
        self.config = AutoTradingConfig()
        
        # Safety tracking
        self.last_trade_time = {}  # Track last trade time per symbol
        self.active_trades = []     # Track active trades
        self.execution_lock = threading.Lock()  # Thread safety
        
        # Statistics
        self.stats = {
            'total_trades': 0,
            'successful_trades': 0,
            'failed_trades': 0,
            'blocked_by_confidence': 0,
            'blocked_by_cooldown': 0,
            'blocked_by_max_trades': 0,
            'blocked_by_duplicates': 0
        }
        
        # Break-even settings
        self.break_even_pips = 10  # Move to break-even after 10 pips profit
        self.break_even_trades = {}  # Track which trades have break-even applied
        
        # Trailing stop settings
        self.trailing_start_pips = 15  # Start trailing after 15 pips profit
        self.trailing_distance_pips = 10  # Trail 10 pips behind current price
        self.trailing_trades = {}  # Track which trades have trailing activated
        
        # Signal stability filter
        self.signal_history = {}  # Track signal history for stability
        self.signal_stability_confirmations = 3  # Minimum confirmations needed
        
        # Cooldown system
        self.last_trade_time = {}  # Track last trade time per symbol
        self.cooldown_seconds = 300  # 5 minutes cooldown
        
        # Trend lock (anti-contradiction)
        self.last_signal_direction = {}  # Track last signal direction
        
        # Session filter
        self.session_filter_enabled = True  # Enable session filtering
        
        # Daily profit management
        self.daily_target = 3  # % daily profit target
        self.daily_loss_limit = -3  # % daily loss limit
        self.daily_profit = 0  # Current daily profit
        self.stop_trading = False  # Emergency stop flag
        
        # Correlation filter
        self.correlated_pairs = [
            ("EURUSD", "GBPUSD"),
            ("USDJPY", "XAUUSD")
        ]
        
        # Trade quality scoring
        self.quality_threshold = 70  # Minimum quality score
        
        # Market behavior adaptation
        self.market_modes = {
            "TRENDING": {"min_confidence": 60, "allow_counter_trend": False, "risk_multiplier": 1.0},
            "RANGING": {"min_confidence": 70, "allow_breakouts": False, "risk_multiplier": 0.8},
            "VOLATILE": {"min_confidence": 80, "risk_multiplier": 0.5}
        }
        self.current_market_mode = "RANGING"  # Default mode
        
        # Enhanced market filters
        self.ema_fast_period = 50
        self.ema_slow_period = 200
        self.trend_filter_enabled = True  # EMA trend filter
        self.momentum_threshold = 0.002  # 0.2% minimum momentum
        self.atr_multiplier = 1.5  # ATR-based filter
        
        # Daily performance tracker
        self.daily_stats = {
            "wins": 0,
            "losses": 0,
            "profit": 0.0,
            "date": datetime.now().date()
        }
        
        # Self-improving system
        self.trade_memory = []  # Store all trades for learning
        self.adaptive_confidence = True  # Enable adaptive thresholds
        
        # AI Prediction System
        self.ml_model = None  # Machine learning model
        self.prediction_threshold = 0.7  # Minimum prediction confidence
        self.ml_enabled = True  # Enable ML predictions
        
        # Enhanced filtering
        self.dual_filter_enabled = True  # Use dual filter (ML + traditional)
        self.high_confidence_threshold = 0.75  # Higher threshold for dual filter
        self.trade_selectivity = True  # Be selective in trades
        
        # Ultra-high confidence threshold
        self.ultra_confidence_threshold = 75  # Reduced to 75% after fixing ML overfitting
        self.ultra_selective = True  # Enable ultra-selective mode
        
        # Trade frequency control
        self.max_trades_per_day = 5  # Limit trades per day
        self.daily_trade_count = 0  # Track daily trades
        
        # Risk management (LEVELED UP)
        self.risk_per_trade = 0.02  # Increased to 2% for higher returns
        self.take_profit_pips = 40  # 0.4% take profit
        self.stop_loss_pips = 20    # 0.2% stop loss (2:1 RR)
        self.leverage = 10  # 10:1 leverage for forex
        
        # Trend filter (VERY IMPORTANT)
        self.trend_filter_enabled = True  # Enable trend alignment
        self.ema_trend_period = 50  # EMA period for trend detection
        self.min_trend_strength = 0.002  # Minimum trend strength
        
        # Overtrading control
        self.min_candles_between_trades = 3  # Minimum candles between trades
        self.last_trade_candle = 0  # Track last trade candle index
        
        # Backtesting Engine
        self.backtest_results = {}  # Store backtest results
        
        # Strategy Optimization
        self.optimized_params = {
            "confidence": 60,
            "risk_reward": 2.0
        }
        self.auto_optimize = True  # Enable auto-optimization
        
        # Weekly Reports
        self.trade_log_file = "trades.csv"  # Trade history file
        self.report_enabled = True  # Enable weekly reports
        
        logger.info("Auto Trading Manager initialized")
        self._log_config()
    
    def _log_config(self):
        """Log current configuration"""
        logger.info("Auto Trading Configuration:")
        logger.info(f"   Enabled: {self.config.enabled}")
        logger.info(f"   Min Confidence: {self.config.min_confidence}%")
        logger.info(f"   Max Trades: {self.config.max_trades}")
        logger.info(f"   Cooldown: {self.config.cooldown_minutes} minutes")
        logger.info(f"   Risk per Trade: {self.config.risk_per_trade}%")
    
    def update_config(self, **kwargs):
        """Update trading configuration"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                logger.info(f"Updated config: {key} = {value}")
        self._log_config()
    
    def should_execute_trade(self, signal_data: Dict) -> tuple:
        """Determine if trade should be executed"""
        if not self.config.enabled:
            return False, "Auto trading disabled"
        
        # 2. Basic signal validation
        signal = signal_data.get('signal', 'WAIT')
        if signal not in ['BUY', 'SELL']:
            self.stats['blocked_by_confidence'] += 1
            return False, f"Invalid signal: {signal}"
        
        # 3. Confidence validation
        confidence = signal_data.get('confidence', 0)
        if confidence < self.config.min_confidence:
            self.stats['blocked_by_confidence'] += 1
            return False, f"Confidence too low: {confidence}% < {self.config.min_confidence}%"
        
        # 4. Entry confirmation validation
        if not signal_data.get('entry_confirmed', False):
            return False, "Entry not confirmed"
        
        # 5. SL/TP validation
        structure_sl = signal_data.get('structure_sl', 0)
        structure_tp = signal_data.get('structure_tp', 0)
        if structure_sl == 0 or structure_tp == 0:
            return False, "Invalid SL/TP levels"
        
        # 6. Cooldown validation
        symbol = signal_data.get('symbol', '')
        if self._is_in_cooldown(symbol):
            self.stats['blocked_by_cooldown'] += 1
            return False, f"Cooldown active for {symbol}"
        
        # 7. Max trades validation
        if self._is_max_trades_reached():
            self.stats['blocked_by_max_trades'] += 1
            return False, f"Max trades reached: {len(self.active_trades)}/{self.config.max_trades}"
        
        # 8. Duplicate trade validation
        if self._has_duplicate_trade(symbol, signal):
            self.stats['blocked_by_duplicates'] += 1
            return False, f"Duplicate trade for {symbol}"
        
        return True, "All validations passed"
    
    def _is_in_cooldown(self, symbol: str) -> bool:
        """Check if symbol is in cooldown period"""
        if symbol not in self.last_trade_time:
            return False
        
        last_time = self.last_trade_time[symbol]
        cooldown_period = timedelta(minutes=self.config.cooldown_minutes)
        
        return datetime.now() - last_time < cooldown_period
    
    def _is_max_trades_reached(self) -> bool:
        """Check if maximum trades limit reached"""
        return len(self.active_trades) >= self.config.max_trades
    
    def _has_duplicate_trade(self, symbol: str, signal: str) -> bool:
        """Check for duplicate trades on same symbol"""
        try:
            # Get current positions from MT5
            positions = self.mt5_connector.get_positions()
            
            for position in positions:
                if position.get('symbol') == symbol:
                    # Check if it's the same direction
                    pos_type = position.get('type', 0)  # 0=BUY, 1=SELL
                    if (signal == 'BUY' and pos_type == 0) or (signal == 'SELL' and pos_type == 1):
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking duplicate trades: {e}")
            return False  # Allow trade if we can't check
    
    def is_signal_stable(self, symbol: str, signal: str, min_confirmations: int = None) -> bool:
        """Check if signal is stable with multiple confirmations"""
        if min_confirmations is None:
            min_confirmations = self.signal_stability_confirmations
            
        if symbol not in self.signal_history:
            self.signal_history[symbol] = []
        
        self.signal_history[symbol].append(signal)
        
        # Keep last 5 signals only
        self.signal_history[symbol] = self.signal_history[symbol][-5:]
        
        # Count same signals
        count = self.signal_history[symbol].count(signal)
        
        is_stable = count >= min_confirmations
        logger.info(f"📊 Signal Stability for {symbol}: {signal} (count: {count}/{min_confirmations}) - {'✅ STABLE' if is_stable else '❌ UNSTABLE'}")
        
        return is_stable
    
    def can_trade(self, symbol: str, cooldown_seconds: int = None) -> bool:
        """Check if symbol is not in cooldown period"""
        if cooldown_seconds is None:
            cooldown_seconds = self.cooldown_seconds
            
        now = time.time()
        
        if symbol not in self.last_trade_time:
            logger.info(f"⏰ Cooldown for {symbol}: ✅ FIRST TRADE")
            return True
        
        time_since_last = now - self.last_trade_time[symbol]
        can_trade_now = time_since_last > cooldown_seconds
        
        if can_trade_now:
            logger.info(f"⏰ Cooldown for {symbol}: ✅ READY ({time_since_last:.0f}s since last)")
        else:
            remaining = cooldown_seconds - time_since_last
            logger.info(f"⏰ Cooldown for {symbol}: ❌ ACTIVE ({remaining:.0f}s remaining)")
        
        return can_trade_now
    
    def is_opposite_signal(self, symbol: str, new_signal: str) -> bool:
        """Check if new signal contradicts last signal direction"""
        if symbol not in self.last_signal_direction:
            logger.info(f"🔄 Trend Lock for {symbol}: ✅ NO PREVIOUS SIGNAL")
            return False
        
        last_signal = self.last_signal_direction[symbol]
        is_opposite = (last_signal == "BUY" and new_signal == "SELL") or (last_signal == "SELL" and new_signal == "BUY")
        
        if is_opposite:
            logger.info(f"🔄 Trend Lock for {symbol}: ❌ OPPOSITE DETECTED ({last_signal} → {new_signal})")
        else:
            logger.info(f"🔄 Trend Lock for {symbol}: ✅ CONSISTENT ({last_signal} → {new_signal})")
        
        return is_opposite
    
    def is_trading_session(self) -> bool:
        """Check if current time is within optimal trading session"""
        if not self.session_filter_enabled:
            logger.info(f"🌍 Session Filter: ✅ DISABLED")
            return True
        
        from datetime import datetime
        hour = datetime.utcnow().hour
        
        # London + NY session (7:00 - 20:00 UTC)
        in_session = 7 <= hour <= 20
        
        session_name = ""
        if 7 <= hour < 12:
            session_name = "London"
        elif 12 <= hour < 17:
            session_name = "London/NY Overlap"
        elif 17 <= hour <= 20:
            session_name = "New York"
        
        if in_session:
            logger.info(f"🌍 Session Filter: ✅ {session_name} Session ({hour}:00)")
        else:
            logger.info(f"🌍 Session Filter: ❌ Outside Session ({hour}:00)")
        
        return in_session
    
    def detect_market_mode(self, atr_percent: float, volatility: float, trend_strength: float) -> str:
        """Detect current market regime based on technical factors"""
        if atr_percent > 0.3 and volatility > 0.2:
            market_mode = "VOLATILE"
        elif trend_strength > 60:
            market_mode = "TRENDING"
        else:
            market_mode = "RANGING"
        
        self.current_market_mode = market_mode
        logger.info(f"🎯 Market Mode Detected: {market_mode}")
        logger.info(f"   ATR%: {atr_percent:.3f}, Volatility: {volatility:.3f}, Trend: {trend_strength:.1f}")
        
        return market_mode
    
    def adapt_to_market_mode(self, market_mode: str) -> Dict:
        """Adapt trading parameters based on market mode"""
        if market_mode not in self.market_modes:
            return self.market_modes["RANGING"]
        
        mode_config = self.market_modes[market_mode]
        
        logger.info(f"� Adapting to {market_mode} market:")
        logger.info(f"   Min Confidence: {mode_config['min_confidence']}%")
        logger.info(f"   Risk Multiplier: {mode_config['risk_multiplier']}")
        
        return mode_config
    
    def update_daily_stats(self, profit: float):
        """Update daily performance statistics"""
        today = datetime.now().date()
        
        # Reset if new day
        if self.daily_stats["date"] != today:
            logger.info(f"📅 New day detected - resetting daily stats")
            self.daily_stats = {
                "wins": 0,
                "losses": 0,
                "profit": 0.0,
                "date": today
            }
        
        # Update stats
        if profit > 0:
            self.daily_stats["wins"] += 1
            logger.info(f"✅ Daily Win: {self.daily_stats['wins']}")
        else:
            self.daily_stats["losses"] += 1
            logger.info(f"❌ Daily Loss: {self.daily_stats['losses']}")
        
        self.daily_stats["profit"] += profit
        
        total_trades = self.daily_stats["wins"] + self.daily_stats["losses"]
        win_rate = self.daily_stats["wins"] / max(1, total_trades)
        
        logger.info(f"� Daily Performance: {win_rate:.1%} win rate, {self.daily_stats['profit']:+.2f}% profit")
    
    def is_bad_trading_day(self) -> bool:
        """Detect if current day is performing poorly"""
        total = self.daily_stats["wins"] + self.daily_stats["losses"]
        
        if total < 3:
            logger.info(f"📊 Bad Day Check: Not enough data ({total} trades)")
            return False  # Not enough data
        
        win_rate = self.daily_stats["wins"] / total
        is_bad_day = False
        
        if win_rate < 0.4:
            logger.warning(f"📊 Bad Day Detected: Low win rate ({win_rate:.1%} < 40%)")
            is_bad_day = True
        
        if self.daily_stats["profit"] < -2:  # -2%
            logger.warning(f"📊 Bad Day Detected: High losses ({self.daily_stats['profit']:.2f}% < -2%)")
            is_bad_day = True
        
        if is_bad_day:
            logger.warning("BAD TRADING DAY - Stopping trading to prevent further losses")
        else:
            logger.info(f"📊 Day Performance: Acceptable ({win_rate:.1%} win rate, {self.daily_stats['profit']:+.2f}% profit)")
        
        return is_bad_day
    
    def store_trade_memory(self, symbol: str, confidence: float, market_mode: str, result: str, profit: float = 0.0):
        """Store trade in memory for learning"""
        trade_record = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "confidence": confidence,
            "market_mode": market_mode,
            "result": result,
            "profit": profit
        }
        
        self.trade_memory.append(trade_record)
        
        # Keep only last 1000 trades to prevent memory issues
        if len(self.trade_memory) > 1000:
            self.trade_memory = self.trade_memory[-1000:]
        
        logger.info(f"Trade Stored in Memory: {symbol} {result} ({confidence}% confidence)")
    
    def get_success_rate(self, min_conf: int = 0) -> float:
        """Calculate success rate for trades above minimum confidence"""
        trades = [t for t in self.trade_memory if t["confidence"] >= min_conf]
        
        if len(trades) == 0:
            return 0.0
        
        wins = sum(1 for t in trades if t["result"] == "WIN")
        success_rate = wins / len(trades)
        
        logger.info(f"📈 Success Rate (≥{min_conf}% confidence): {success_rate:.1%} ({wins}/{len(trades)} trades)")
        
        return success_rate
    
    def get_mode_performance(self, mode: str) -> float:
        """Calculate success rate for specific market mode"""
        trades = [t for t in self.trade_memory if t["market_mode"] == mode]
        
        if len(trades) < 5:
            logger.info(f"📈 {mode} Performance: Insufficient data ({len(trades)} trades)")
            return 0.5
        
        wins = sum(1 for t in trades if t["result"] == "WIN")
        success_rate = wins / len(trades)
        
        logger.info(f"📈 {mode} Performance: {success_rate:.1%} ({wins}/{len(trades)} trades)")
        
        return success_rate
    
    def prepare_ml_data(self, df):
        """Prepare data for machine learning"""
        try:
            import pandas as pd
            import numpy as np
            
            df['returns'] = df['close'].pct_change()
            df['ma_fast'] = df['close'].rolling(5).mean()
            df['ma_slow'] = df['close'].rolling(20).mean()
            df['volatility'] = df['returns'].rolling(10).std()
            
            # Enhanced features
            df['rsi'] = self._compute_rsi(df['close'])
            df['ema'] = df['close'].ewm(span=10).mean()
            df['momentum'] = df['close'] - df['close'].shift(5)
            df['atr'] = self._compute_atr(df)
            
            # NEW: MACD indicator
            df['macd'] = self._compute_macd(df['close'])
            
            # NEW: Candlestick patterns
            df['doji'] = self._detect_doji(df)
            df['engulfing'] = self._detect_engulfing(df)
            
            # Better target: Meaningful moves only (3 candles, 0.1% threshold)
            future_price = df['close'].shift(-3)
            current_price = df['close']
            price_change = (future_price - current_price) / current_price
            df['target'] = (price_change > 0.001).astype(int)  # 0.1% minimum move
            
            df = df.dropna()
            logger.info(f"Enhanced ML Data Prepared: {len(df)} samples, 9 features")
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error preparing ML data: {e}")
            return df
    
    def _compute_macd(self, prices, fast=12, slow=26, signal=9):
        """Compute MACD indicator"""
        try:
            import numpy as np
            exp1 = prices.ewm(span=fast).mean()
            exp2 = prices.ewm(span=slow).mean()
            macd = exp1 - exp2
            signal = macd.ewm(span=signal).mean()
            return macd
        except:
            return prices * 0 + 0  # Return neutral MACD
    
    def _detect_doji(self, df):
        """Detect doji candlestick patterns"""
        try:
            body = abs(df['close'] - df['open'])
            upper_shadow = df['high'] - df[['close', 'open']].max(axis=1)
            lower_shadow = df[['close', 'open']].min(axis=1) - df['low']
            
            # Doji: Very small body
            doji = body < (upper_shadow + lower_shadow) * 0.1
            return doji.astype(int)
        except:
            return 0  # No doji
    
    def _detect_engulfing(self, df):
        """Detect engulfing candlestick patterns"""
        try:
            prev_body = abs(df['close'].shift() - df['open'].shift())
            curr_body = abs(df['close'] - df['open'])
            
            # Bullish engulfing
            bull_engulf = (df['close'].shift() < df['open'].shift() and 
                          df['open'] > df['high'].shift() and 
                          df['close'] > df['low'].shift())
            
            # Bearish engulfing
            bear_engulf = (df['close'].shift() > df['open'].shift() and 
                          df['open'] < df['low'].shift() and 
                          df['close'] < df['high'].shift())
            
            return (bull_engulf | bear_engulf).astype(int)
        except:
            return 0  # No engulfing
    
    def _compute_rsi(self, prices, period=14):
        """Compute RSI indicator"""
        try:
            import numpy as np
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except:
            return prices * 0 + 50  # Return neutral RSI
    
    def _compute_atr(self, df, period=14):
        """Compute Average True Range"""
        try:
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(period).mean()
            return atr
        except:
            return df['close'] * 0 + 0.001  # Return small ATR
    
    def train_model(self, df):
        """Train ML model with proper time-series validation"""
        try:
            import pandas as pd
            from sklearn.model_selection import train_test_split
            from sklearn.ensemble import RandomForestClassifier
            
            # CRITICAL FIX: Time-series split (NO SHUFFLING!)
            split_index = int(len(df) * 0.8)
            
            train = df.iloc[:split_index]
            test = df.iloc[split_index:]
            
            # CRITICAL FIX: Shift all features to prevent future data leakage
            features_to_shift = ['ma_fast', 'ma_slow', 'rsi', 'ema', 'momentum', 'atr', 'volatility']
            
            for feature in features_to_shift:
                if feature in train.columns:
                    train[feature] = train[feature].shift(1)
                    test[feature] = test[feature].shift(1)
            
            # Drop NaN values created by shifting
            train = train.dropna()
            test = test.dropna()
            
            # Prepare features
            features = ['ma_fast', 'ma_slow', 'volatility', 'rsi', 'ema', 'momentum', 'atr']
            features = [f for f in features if f in train.columns]
            
            X_train = train[features]
            y_train = train['target']
            X_test = test[features]
            y_test = test['target']
            
            logger.info(f"CRITICAL FIX: Time-series split with shifted features")
            logger.info(f"   Train period: {len(train)} candles")
            logger.info(f"   Test period: {len(test)} candles")
            logger.info(f"   Features shifted: {features_to_shift}")
            
            # Train model
            self.ml_model = RandomForestClassifier(n_estimators=100, random_state=42)
            self.ml_model.fit(X_train, y_train)
            
            # Store feature names for consistency
            self.model_features = features
            
            # REAL ACCURACY ON TEST DATA (not training data!)
            train_accuracy = self.ml_model.score(X_train, y_train)
            test_accuracy = self.ml_model.score(X_test, y_test)
            
            logger.info(f"ML Model Trained:")
            logger.info(f"   Training Accuracy: {train_accuracy:.1%} (expected: high)")
            logger.info(f"   Test Accuracy: {test_accuracy:.1%} (REAL performance)")
            logger.info(f"   Features: {len(features)}")
            logger.info(f"   Train Size: {len(X_train)}, Test Size: {len(X_test)}")
            
            # WARN if overfitting detected
            if train_accuracy > 0.9 and test_accuracy < 0.7:
                logger.warning(f"OVERFITTING DETECTED! Train: {train_accuracy:.1%} vs Test: {test_accuracy:.1%}")
            elif test_accuracy > 0.8:
                logger.warning(f"Suspiciously high test accuracy: {test_accuracy:.1%} - possible data leakage")
            elif 0.5 <= test_accuracy <= 0.7:
                logger.info(f"Realistic ML accuracy: {test_accuracy:.1%}")
            else:
                logger.warning(f"Low test accuracy: {test_accuracy:.1%} - model may not be useful")
            
            return self.ml_model
            
        except Exception as e:
            logger.error(f"Error training ML model: {e}")
            return None
    
    def predict_signal(self, latest_data):
        """Predict next move using ML model"""
        try:
            if self.ml_model is None:
                return None, 0.0
            
            import pandas as pd
            
            # Use the same features that were used during training
            if hasattr(self, 'model_features'):
                features = self.model_features
            else:
                features = ['ma_fast', 'ma_slow', 'volatility', 'rsi', 'ema', 'momentum', 'atr']
            
            # Check if all features are available in latest_data
            available_features = [f for f in features if f in latest_data]
            if len(available_features) != len(features):
                logger.warning(f"Missing features: {set(features) - set(available_features)}")
                return None, 0.0
            
            # Extract feature values properly
            feature_values = []
            for feature in features:
                feature_values.append(latest_data.get(feature, 0))
            
            X = pd.DataFrame([feature_values], columns=features)
            
            prediction = self.ml_model.predict(X)[0]
            prob = self.ml_model.predict_proba(X)[0][prediction]
            
            signal = "BUY" if prediction == 1 else "SELL"
            
            logger.info(f"ML Prediction: {signal} ({prob:.1%} confidence)")
            
            return signal, prob
            
        except Exception as e:
            logger.error(f"Error predicting signal: {e}")
            return None, 0.0
    
    def apply_all_filters(self, symbol: str, signal: str, confidence: float, signal_data: Dict) -> bool:
        """Apply all professional filters before trade execution"""
        try:
            # Filter 1: Minimum confidence
            if confidence < self.config.min_confidence:
                logger.info(f"🚫 Filter: Confidence too low ({confidence}% < {self.config.min_confidence}%)")
                return False
            
            # Filter 2: Cooldown check
            if self._is_in_cooldown(symbol):
                logger.info(f"🚫 Filter: {symbol} in cooldown")
                return False
            
            # Filter 3: Max trades check
            if self._is_max_trades_reached():
                logger.info(f"🚫 Filter: Max trades reached ({len(self.active_trades)}/{self.config.max_trades})")
                return False
            
            # Filter 4: Duplicate trade check
            if self._has_duplicate_trade(symbol, signal):
                logger.info(f"🚫 Filter: Duplicate trade for {symbol}")
                return False
            
            # Filter 5: Signal stability
            if not self.is_signal_stable(symbol, signal):
                logger.info(f"🚫 Filter: Signal not stable for {symbol}")
                return False
            
            # Filter 6: Trading session
            if not self.is_trading_session():
                logger.info(f"🚫 Filter: Outside trading session")
                return False
            
            # Filter 7: Opposite signal check
            if self.is_opposite_signal(symbol, signal):
                logger.info(f"🚫 Filter: Opposite signal for {symbol}")
                return False
            
            # Filter 8: Daily limits
            if hasattr(self, 'check_daily_limits') and not self.check_daily_limits():
                logger.info(f"🚫 Filter: Daily limits reached")
                return False
            
            # Filter 9: Market conditions (if available)
            if hasattr(self, '_check_market_conditions'):
                if not self._check_market_conditions(signal_data):
                    logger.info(f"🚫 Filter: Poor market conditions")
                    return False
            
            # Filter 10: Ultra-selective mode
            if self.ultra_selective and confidence < self.ultra_confidence_threshold:
                logger.info(f"🚫 Filter: Ultra-selective mode ({confidence}% < {self.ultra_confidence_threshold}%)")
                return False
            
            logger.info(f"✅ All filters passed for {symbol} {signal} ({confidence}%)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error in filters: {e}")
            return False
    
    def calculate_lot_size(self, balance, risk_percent, stop_loss_pips, pip_value=10):
        """Calculate proper lot size based on risk and stop loss distance"""
        risk_amount = balance * (risk_percent / 100)
        
        if stop_loss_pips == 0:
            return 0.01  # fallback
        
        lot_size = risk_amount / (stop_loss_pips * pip_value)
        
        # Safety limits
        lot_size = max(0.01, min(lot_size, 10))
        
        return round(lot_size, 2)

    def calculate_atr(self, df, period=14):
        """Calculate Average True Range for dynamic stop loss"""
        import pandas as pd
        
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        
        atr = true_range.rolling(period).mean()
        return atr

    def calculate_dynamic_sl_tp(self, entry_price, atr, signal, sl_multiplier=1.5, tp_multiplier=2.5, trend="neutral"):
        """Calculate dynamic stop loss and take profit based on ATR and market conditions"""
        
        # OPTIMIZED FOR PROFITABILITY: Better risk/reward ratios
        if trend == "bearish" and signal == "SELL":
            # In bear market, excellent risk/reward
            sl_multiplier = 1.8  # Slightly tighter for better RR
            tp_multiplier = 4.0  # Much bigger targets for profitability
        elif trend == "ranging":
            # In ranging markets, very tight stops and quick targets
            sl_multiplier = 1.0  # Very tight stops
            tp_multiplier = 2.0  # Quick targets
        elif trend == "bullish" and signal == "BUY":
            # In bull market, excellent risk/reward
            sl_multiplier = 1.8
            tp_multiplier = 4.0
        else:
            # Default - improved risk/reward
            sl_multiplier = 1.5
            tp_multiplier = 3.0
        
        if signal == "BUY":
            stop_loss = entry_price - (atr * sl_multiplier)
            take_profit = entry_price + (atr * tp_multiplier)
        else:  # SELL
            stop_loss = entry_price + (atr * sl_multiplier)
            take_profit = entry_price - (atr * tp_multiplier)
        
        return stop_loss, take_profit

    def manage_trade_dynamically(self, signal, entry_price, current_price, atr, stop_loss, take_profit, lot_size, trade_open_pips):
        """Advanced trade management with break-even, trailing stop, and partial TP"""
        
        # BREAK-EVEN LOGIC
        if trade_open_pips >= atr * 10000:  # 1 ATR in pips
            if signal == "BUY" and stop_loss < entry_price:
                stop_loss = entry_price
                logger.info(f"Break-even activated: BUY SL moved to {entry_price:.5f}")
            elif signal == "SELL" and stop_loss > entry_price:
                stop_loss = entry_price
                logger.info(f"Break-even activated: SELL SL moved to {entry_price:.5f}")
        
        # TRAILING STOP LOGIC
        if signal == "BUY":
            new_stop = current_price - (atr * 1.2)
            if new_stop > stop_loss:
                stop_loss = new_stop
                logger.info(f"Trailing stop updated: {stop_loss:.5f}")
        elif signal == "SELL":
            new_stop = current_price + (atr * 1.2)
            if new_stop < stop_loss:
                stop_loss = new_stop
                logger.info(f"Trailing stop updated: {stop_loss:.5f}")
        
        # PARTIAL TAKE PROFIT (would need position tracking in live trading)
        # For backtest, we'll just log when this would happen
        if trade_open_pips >= atr * 1.5 * 10000:  # 1.5 ATR in pips
            logger.info(f"Partial TP opportunity: {trade_open_pips:.1f} pips profit")
        
        return stop_loss, take_profit

    def detect_market_strength(self, df, current_index: int) -> str:
        """Detect overall market strength for additional filtering"""
        try:
            # Get recent candles for analysis
            start_idx = max(0, current_index - 20)
            recent_df = df.iloc[start_idx:current_index + 1]
            
            if len(recent_df) < 10:
                return "weak"
            
            # Calculate price movement strength
            price_change = abs(recent_df['close'].iloc[-1] - recent_df['close'].iloc[0]) / recent_df['close'].iloc[0]
            
            # Calculate volatility strength
            volatility = recent_df['high'].max() - recent_df['low'].min()
            avg_range = (recent_df['high'] - recent_df['low']).mean()
            volatility_strength = volatility / avg_range if avg_range > 0 else 1
            
            # Overall strength score
            strength_score = 0
            
            # Price movement strength
            if price_change > 0.005:  # 0.5% movement
                strength_score += 2
            elif price_change > 0.002:  # 0.2% movement
                strength_score += 1
            
            # Volatility strength
            if volatility_strength > 2.0:
                strength_score += 2
            elif volatility_strength > 1.5:
                strength_score += 1
            
            # Classify market strength
            if strength_score >= 3:
                market_strength = "strong"
            elif strength_score >= 1:
                market_strength = "moderate"
            else:
                market_strength = "weak"
            
            logger.info(f"Market Strength: {market_strength} (Score: {strength_score}, Price Change: {price_change:.3f})")
            return market_strength
            
        except Exception as e:
            logger.error(f"Error detecting market strength: {e}")
            return "weak"

    def calculate_trade_strength_score(self, signal, confidence, trend, atr, momentum, atr_mean):
        """Calculate trade strength score for quality filtering - BEAR MARKET EDITION"""
        score = 0
        
        # BEAR MARKET STRATEGY: Look for reversals, not trend following
        if trend == "bearish":
            # In bear market, look for BUY reversals (counter-trend)
            if signal == "BUY" and confidence > 95:
                score += 3  # Strong reversal signals
            elif signal == "SELL" and confidence > 98:
                score += 1  # Only very strong SELL signals
        elif trend == "ranging":
            # In ranging markets, mean reversion is key
            if confidence > 94:  # High confidence for ranging
                score += 2
        elif signal == "BUY" and trend == "bullish":
            score += 2
        elif signal == "SELL" and trend == "bearish":
            score += 2
        
        # REVERSAL MOMENTUM (Critical for bear market)
        if trend == "bearish" and signal == "BUY":
            # Look for strong upward momentum in bear market (reversal)
            if momentum > 0.002:  # Strong upward momentum
                score += 3
            elif momentum > 0.001:
                score += 2
        elif trend == "ranging":
            # Mean reversion momentum
            if abs(momentum) > 0.002:
                score += 2
        
        # VOLATILITY (Important for reversals)
        if atr > atr_mean * 1.3:  # High volatility = good for reversals
            score += 2
        elif atr > atr_mean:
            score += 1
        
        logger.info(f"BEAR MARKET Strength Score: {score} (Signal: {signal}, Trend: {trend}, Confidence: {confidence:.1f}%)")
        return score

    def detect_trend(self, df, current_index: int) -> str:
        """Improved trend detection - less strict, more practical"""
        try:
            if not self.trend_filter_enabled:
                return "neutral"
            
            # Get recent candles for trend analysis
            start_idx = max(0, current_index - self.ema_trend_period)
            recent_df = df.iloc[start_idx:current_index + 1]
            
            if len(recent_df) < 20:
                return "neutral"
            
            # Calculate EMAs
            ema_fast = recent_df['close'].ewm(span=20).mean()
            ema_slow = recent_df['close'].ewm(span=self.ema_trend_period).mean()
            
            # Get current EMA values
            current_ema_fast = ema_fast.iloc[-1]
            current_ema_slow = ema_slow.iloc[-1]
            current_price = recent_df['close'].iloc[-1]
            
            # Calculate EMA difference as percentage (NEW LOGIC)
            ema_diff_pct = (current_ema_fast - current_ema_slow) / current_ema_slow * 100
            
            # IMPROVED: More practical trend classification
            if abs(ema_diff_pct) < 0.02:  # Very flat = ranging
                trend = "ranging"
            elif ema_diff_pct > 0:  # Fast above slow = bullish
                trend = "bullish"
            else:  # Fast below slow = bearish
                trend = "bearish"
            
            logger.info(f"Trend: {trend} (EMA diff: {ema_diff_pct:.4f}%, Price: {current_price:.5f})")
            return trend
            
        except Exception as e:
            logger.error(f"Error detecting trend: {e}")
            return "neutral"
    
    def is_trend_aligned(self, signal: str, trend: str) -> bool:
        """Improved trend alignment - more practical"""
        if not self.trend_filter_enabled:
            return True
        
        # Allow strong ML signals to override trend
        # This will be handled in the main logic
        
        # Basic trend alignment check
        if trend == "bullish" and signal == "BUY":
            return True
        elif trend == "bearish" and signal == "SELL":
            return True
        elif trend == "ranging":
            # Allow ranging markets but with higher confidence requirement
            return True  # Will be filtered in main logic
        else:
            return False
    
    def is_overtrading_controlled(self, current_index: int) -> bool:
        """Control overtrading by enforcing minimum candle gap"""
        if current_index - self.last_trade_candle < self.min_candles_between_trades:
            logger.info(f"Overtrading control: Only {current_index - self.last_trade_candle} candles since last trade")
            return False
        
        return True
    
    def backtest_strategy(self, df, model):
        """Professional backtest with proper risk management"""
        try:
            initial_balance = 1000
            balance = initial_balance
            trades = []
            trade_count = 0
            max_trades_per_day = 1000
            skipped_reasons = {}
            
            # Add ATR to dataframe for dynamic SL/TP
            df['ATR'] = self.calculate_atr(df)
            atr_mean = df['ATR'].mean()
            
            for i in range(50, len(df)-1):
                # RISK CONTROL: Max drawdown protection
                if balance < initial_balance * 0.7:
                    logger.warning("Max drawdown reached. Stopping trading.")
                    break
                
                if trade_count >= max_trades_per_day:
                    logger.info(f"Max trades reached ({trade_count}/{max_trades_per_day})")
                    skipped_reasons['max_trades'] = skipped_reasons.get('max_trades', 0) + 1
                    break
                    
                row = df.iloc[i]
                
                # Get ML prediction
                signal, prob = self.predict_signal(row)
                
                if signal is None:
                    logger.info(f"Prediction failed")
                    skipped_reasons['prediction_failed'] = skipped_reasons.get('prediction_failed', 0) + 1
                    continue
                
                confidence_pct = prob * 100
                
                # TREND FILTER (IMPROVED)
                trend = self.detect_trend(df, i)
                
                # Get current indicators for strength scoring
                current_atr = df.iloc[i]['ATR']
                current_momentum = df.iloc[i]['momentum']
                
                # TRADE STRENGTH SCORE (NEW FILTERING SYSTEM)
                strength_score = self.calculate_trade_strength_score(
                    signal, confidence_pct, trend, current_atr, current_momentum, atr_mean
                )
                
                # BEAR MARKET FILTER (EMERGENCY FIX)
                if trend == "bearish" and confidence_pct < 98:
                    logger.info(f"Bear market filter: Confidence too low ({confidence_pct:.1f}% < 98%)")
                    skipped_reasons['bear_market_filter'] = skipped_reasons.get('bear_market_filter', 0) + 1
                    continue
                
                # HIGH-QUALITY SETUP FILTER (BALANCED APPROACH)
                minimum_score = 3 if trend == "ranging" else 4  # Balanced thresholds
                
                if strength_score < minimum_score:
                    logger.info(f"Low strength score: {strength_score} < {minimum_score} ({trend} market - skipping trade)")
                    skipped_reasons['low_strength'] = skipped_reasons.get('low_strength', 0) + 1
                    continue
                
                # OVERTRADING CONTROL
                if not self.is_overtrading_controlled(i):
                    skipped_reasons['overtrading'] = skipped_reasons.get('overtrading', 0) + 1
                    continue
                
                # EXECUTE TRADE WITH PROFESSIONAL POSITION SIZING
                trade_count += 1
                self.last_trade_candle = i
                
                entry = df.iloc[i]['close']
                atr = df.iloc[i]['ATR']
                
                # DYNAMIC STOP LOSS AND TAKE PROFIT (WITH MARKET ADAPTATION)
                stop_loss, take_profit = self.calculate_dynamic_sl_tp(entry, atr, signal, trend=trend)
                
                # PROPER POSITION SIZING (REDUCED RISK FOR LOSING STREAK)
                sl_pips = abs(entry - stop_loss) * 10000
                risk_percent = 0.5 if balance < 800 else 1.0  # Reduce risk when losing
                lot_size = self.calculate_lot_size(balance, risk_percent, sl_pips)
                risk_amount = balance * (risk_percent / 100)  # Dynamic risk
                
                # ADVANCED TRADE SIMULATION WITH DYNAMIC MANAGEMENT
                profit = 0
                trade_open = True
                j = i + 1
                initial_sl = stop_loss
                max_profit_pips = 0
                
                while trade_open and j < len(df):
                    current_candle = df.iloc[j]
                    high = current_candle['high']
                    low = current_candle['low']
                    close = current_candle['close']
                    
                    # Calculate current profit in pips
                    if signal == "BUY":
                        current_pips = (close - entry) * 10000
                    else:
                        current_pips = (entry - close) * 10000
                    
                    max_profit_pips = max(max_profit_pips, current_pips)
                    
                    # ADVANCED TRADE MANAGEMENT
                    stop_loss, take_profit = self.manage_trade_dynamically(
                        signal, entry, close, atr, stop_loss, take_profit, lot_size, current_pips
                    )
                    
                    # Check if stop loss hit
                    if signal == "BUY" and low <= stop_loss:
                        exit_price = stop_loss
                        profit = (exit_price - entry) * lot_size * 100000
                        trade_open = False
                        logger.info(f"Stop Loss Hit: BUY at {entry:.5f}, SL at {stop_loss:.5f}")
                    elif signal == "SELL" and high >= stop_loss:
                        exit_price = stop_loss
                        profit = (entry - exit_price) * lot_size * 100000
                        trade_open = False
                        logger.info(f"Stop Loss Hit: SELL at {entry:.5f}, SL at {stop_loss:.5f}")
                    
                    # Check if take profit hit
                    elif signal == "BUY" and high >= take_profit:
                        exit_price = take_profit
                        profit = (exit_price - entry) * lot_size * 100000
                        trade_open = False
                        logger.info(f"Take Profit Hit: BUY at {entry:.5f}, TP at {take_profit:.5f}")
                    elif signal == "SELL" and low <= take_profit:
                        exit_price = take_profit
                        profit = (entry - exit_price) * lot_size * 100000
                        trade_open = False
                        logger.info(f"Take Profit Hit: SELL at {entry:.5f}, TP at {take_profit:.5f}")
                    
                    j += 1
                
                # If trade reaches end of data
                if trade_open:
                    final_price = df.iloc[-1]['close']
                    if signal == "BUY":
                        profit = (final_price - entry) * lot_size * 100000
                    else:
                        profit = (entry - final_price) * lot_size * 100000
                    logger.info(f"Trade Closed: {signal} at {entry:.5f} → {final_price:.5f}")
                
                balance += profit
                trades.append(profit)
                
                # PROFESSIONAL TRADE LOGGING
                logger.info(f"""
ADVANCED TRADE EXECUTED
Signal: {signal}
Confidence: {confidence_pct:.1f}%
Trend: {trend}
Strength Score: {strength_score}/6
Entry: {entry:.5f}
SL: {initial_sl:.5f} → {stop_loss:.5f}
TP: {take_profit:.5f}
Lot: {lot_size:.2f}
Max Profit: {max_profit_pips:.1f} pips
Profit: ${profit:+.2f}
Balance: ${balance:.2f}
""")
            
            # Results
            win_rate = sum(1 for t in trades if t > 0) / len(trades) if trades else 0
            total_return = (balance - initial_balance) / initial_balance
            
            self.backtest_results = {
                "final_balance": balance,
                "total_return": total_return,
                "win_rate": win_rate,
                "total_trades": len(trades),
                "avg_profit": sum(trades) / len(trades) if trades else 0,
                "skipped_trades": (len(df) - 50) - len(trades)
            }
            
            logger.info(f"BACKTEST RESULTS:")
            logger.info(f"   Final Balance: ${balance:,.2f}")
            logger.info(f"   Total Return: {total_return:.1%}")
            logger.info(f"   Win Rate: {win_rate:.1%}")
            logger.info(f"   Total Trades: {len(trades)}")
            logger.info(f"   Avg Profit: ${self.backtest_results['avg_profit']:.2f}")
            
            return self.backtest_results
            
        except Exception as e:
            logger.error(f"Error backtesting: {e}")
            return {}
    
    def backtest_strategy_debug(self, df, model):
        """DEBUG: Force trades to test if ML works"""
        try:
            balance = 1000
            trades = []
            trade_count = 0
            max_trades_per_day = 50  # High limit for debug
            
            print("🔧 DEBUG MODE: FORCING ALL TRADES")
            
            for i in range(50, len(df)-1):
                if trade_count >= max_trades_per_day:
                    print(f"🚫 DEBUG: Max trades reached ({trade_count})")
                    break
                    
                row = df.iloc[i]
                
                # Get ML prediction
                signal, prob = self.predict_signal(row)
                
                if signal is None:
                    print(f"🚫 DEBUG: Prediction failed")
                    continue
                
                # CONVERT PREDICTION
                prediction = 1 if signal == "BUY" else 0
                
                # FORCE TRADE (no filters!)
                if True:  # FORCE EXECUTION
                    trade_count += 1
                    
                    entry = df.iloc[i]['close']
                    exit_price = df.iloc[i+1]['close']
                    
                    # Calculate profit
                    if prediction == 1:  # BUY
                        profit = (exit_price - entry) / entry
                    else:  # SELL
                        profit = (entry - exit_price) / entry
                    
                    profit_pct = profit * 100
                    balance += profit_pct
                    trades.append(profit_pct)
                    
                    print(f"✅ DEBUG TRADE #{trade_count}: {signal} ({prob:.1%}) → {profit_pct:+.3f}%")
            
            # Results
            win_rate = sum(1 for t in trades if t > 0) / len(trades) if trades else 0
            total_return = (balance - 1000) / 1000
            
            print(f"\n🔧 DEBUG RESULTS:")
            print(f"   Total Trades: {len(trades)}")
            print(f"   Win Rate: {win_rate:.1%}")
            print(f"   Total Return: {total_return:.1%}")
            print(f"   Final Balance: ${balance:,.2f}")
            
            return {
                "final_balance": balance,
                "total_return": total_return,
                "win_rate": win_rate,
                "total_trades": len(trades),
                "avg_profit": sum(trades) / len(trades) if trades else 0,
                "skipped_trades": 0
            }
            
        except Exception as e:
            print(f"❌ DEBUG Error: {e}")
            return {}
    
    def optimize_strategy(self, df):
        """Auto-optimize strategy parameters"""
        try:
            best_score = -999
            best_params = None
            
            # Test different confidence thresholds and risk/reward ratios
            for conf in [60, 65, 70, 75]:
                for rr in [1.5, 2.0, 2.5]:
                    score = self._run_simulation(df, conf, rr)
                    
                    if score > best_score:
                        best_score = score
                        best_params = {"confidence": conf, "risk_reward": rr}
            
            if best_params:
                self.optimized_params = best_params
                logger.info(f"🎯 Strategy Optimized: {best_params}")
            
            return best_params
            
        except Exception as e:
            logger.error(f"❌ Error optimizing strategy: {e}")
            return self.optimized_params
    
    def _run_simulation(self, df, confidence, risk_reward):
        """Run simulation with specific parameters"""
        # Simplified simulation - would need full implementation
        return 0.65  # Placeholder score
    
    def save_trades_to_csv(self):
        """Save trade history to CSV for analysis"""
        try:
            import pandas as pd
            
            if not self.trade_memory:
                logger.info("📊 No trades to save")
                return
            
            df_trades = pd.DataFrame(self.trade_memory)
            df_trades.to_csv(self.trade_log_file, index=False)
            logger.info(f"📊 {len(self.trade_memory)} trades saved to {self.trade_log_file}")
            
        except Exception as e:
            logger.error(f"❌ Error saving trades: {e}")
    
    def generate_weekly_report(self):
        """Generate weekly performance report"""
        try:
            import pandas as pd
            import matplotlib.pyplot as plt
            
            # Load trades from CSV
            df = pd.read_csv(self.trade_log_file)
            
            if df.empty:
                logger.info("� No trades for weekly report")
                return
            
            # Calculate statistics
            wins = df[df['result'] == 'WIN']
            losses = df[df['result'] == 'LOSS']
            
            win_rate = len(wins) / len(df)
            total_profit = df['profit'].sum()
            avg_profit = df['profit'].mean()
            
            # Generate report
            report = f"""
📊 WEEKLY TRADING REPORT
=======================
Total Trades: {len(df)}
Win Rate: {win_rate:.1%}
Total Profit: {total_profit:.2f}%
Average Profit: {avg_profit:.2f}%
Best Trade: {df['profit'].max():.2f}%
Worst Trade: {df['profit'].min():.2f}%

Market Mode Performance:
{df.groupby('market_mode')['result'].value_counts(normalize=True).unstack()}
"""
            
            logger.info(report)
            
            # Create equity curve
            df['cumulative_profit'] = df['profit'].cumsum()
            plt.figure(figsize=(12, 6))
            plt.plot(df['cumulative_profit'])
            plt.title("Equity Curve")
            plt.xlabel("Trade Number")
            plt.ylabel("Cumulative Profit (%)")
            plt.grid(True)
            plt.savefig("equity_curve.png")
            plt.close()
            
            logger.info("📊 Equity curve saved as equity_curve.png")
            
            # Send to Telegram if available
            if self.telegram_bot:
                try:
                    with open("equity_curve.png", "rb") as photo:
                        self.telegram_bot.send_photo(
                            chat_id=self.telegram_bot.chat_id,
                            photo=photo,
                            caption=report
                        )
                    logger.info("📱 Weekly report sent to Telegram")
                except Exception as e:
                    logger.error(f"❌ Error sending report to Telegram: {e}")
            
        except Exception as e:
            logger.error(f"❌ Error generating weekly report: {e}")
    
    def integrate_ml_prediction(self, signal_data):
        """Integrate ML prediction into signal analysis"""
        if not self.ml_enabled or self.ml_model is None:
            return signal_data
        
        # Get ML prediction
        ml_signal, ml_confidence = self.predict_signal(signal_data.get('latest_data', {}))
        
        if ml_signal and ml_confidence > self.prediction_threshold:
            # Dual filter: Both ML and traditional must agree
            traditional_signal = signal_data.get('signal', '')
            traditional_confidence = signal_data.get('confidence', 0)
            
            # Enhanced dual filtering
            if self.dual_filter_enabled:
                # Both must agree AND have high confidence
                if (ml_signal == traditional_signal and 
                    ml_confidence > self.high_confidence_threshold and 
                    traditional_confidence > self.config.min_confidence):
                    
                    # Weighted combination (60% traditional, 40% ML for agreement)
                    combined_confidence = (traditional_confidence * 0.6 + ml_confidence * 100 * 0.4)
                    
                    signal_data['ml_signal'] = ml_signal
                    signal_data['ml_confidence'] = ml_confidence
                    signal_data['combined_confidence'] = combined_confidence
                    signal_data['dual_filter_passed'] = True
                    
                    logger.info(f"DUAL FILTER PASSED: {ml_signal} ({ml_confidence:.1%}) × {traditional_signal} ({traditional_confidence:.1%}) → {combined_confidence:.1f}%")
                else:
                    signal_data['dual_filter_passed'] = False
                    logger.info(f"DUAL FILTER BLOCKED: ML={ml_signal} ({ml_confidence:.1%}) ≠ Traditional={traditional_signal} ({traditional_confidence:.1%})")
                    return signal_data
            else:
                # Traditional single filter
                if ml_confidence > self.prediction_threshold:
                    signal_data['ml_signal'] = ml_signal
                    signal_data['ml_confidence'] = ml_confidence
                    signal_data['combined_confidence'] = ml_confidence * 100
                    signal_data['dual_filter_passed'] = True
                    
                    logger.info(f"ML FILTER PASSED: {ml_signal} ({ml_confidence:.1%})")
                else:
                    signal_data['dual_filter_passed'] = False
                    logger.info(f"ML FILTER BLOCKED: {ml_signal} ({ml_confidence:.1%} < {self.prediction_threshold * 100:.1f}%)")
                    return signal_data
        
        # Track model performance
        self._update_model_accuracy(ml_signal, signal_data.get('actual_result', None))
        
        return signal_data
    
    def _update_model_accuracy(self, prediction, actual_result):
        """Track model performance for adaptive confidence"""
        if actual_result is not None:
            correct = 1 if prediction == actual_result else 0
            self.model_accuracy.append(correct)
            
            # Keep only recent predictions
            if len(self.model_accuracy) > self.max_accuracy_history:
                self.model_accuracy = self.model_accuracy[-self.max_accuracy_history:]
            
            # Calculate current accuracy
            if len(self.model_accuracy) >= 10:
                current_accuracy = sum(self.model_accuracy) / len(self.model_accuracy)
                
                # Adaptive confidence adjustment
                if current_accuracy < 0.5:
                    logger.warning(f"📉 Model accuracy low ({current_accuracy:.1%}) - Consider retraining")
                    # Could trigger model retraining here
                elif current_accuracy > 0.7:
                    logger.info(f"📈 Model accuracy high ({current_accuracy:.1%}) - Performance good")
    
    def should_trade_today(self) -> bool:
        """Control trade frequency to prevent overtrading"""
        today = datetime.now().date()
        
        # Reset daily count if new day
        if not hasattr(self, 'last_trade_date') or self.last_trade_date != today:
            self.daily_trade_count = 0
            self.last_trade_date = today
        
        # Check if under daily limit
        if self.daily_trade_count >= self.max_trades_per_day:
            logger.warning(f"🚫 Daily trade limit reached: {self.daily_trade_count}/{self.max_trades_per_day}")
            return False
        
        return True
    
    def increment_trade_count(self):
        """Increment daily trade count"""
        self.daily_trade_count += 1
        logger.info(f"📊 Daily trade count: {self.daily_trade_count}/{self.max_trades_per_day}")
    
    def check_correlation_conflict(self, symbol: str) -> bool:
        """Check for correlated pair conflicts"""
        for p1, p2 in self.correlated_pairs:
            if symbol == p1:
                # Check if p2 has active trades
                active_trades = self.trade_manager.get_active_trades()
                for trade in active_trades:
                    if trade.get('symbol') == p2:
                        logger.warning(f"� Correlation conflict: {symbol} blocked by {p2} position")
                        return True
            elif symbol == p2:
                # Check if p1 has active trades
                for trade in active_trades:
                    if trade.get('symbol') == p1:
                        logger.warning(f"🔗 Correlation conflict: {symbol} blocked by {p1} position")
                        return True
        
        return False
    
    def calculate_trade_quality_score(self, signal_data: Dict) -> float:
        """Calculate comprehensive trade quality score"""
        try:
            # Basic signal strength (30% weight)
            basic_strength = signal_data.get('confidence', 0) * 0.3
            
            # Higher timeframe alignment (30% weight)
            htf_alignment = 0.3 if signal_data.get('strong_trend', False) else 0.0
            
            # Entry confirmation (20% weight)
            entry_confirmation = 0.2 if signal_data.get('entry_confirmed', False) else 0.0
            
            # Market condition score (20% weight)
            market_condition = signal_data.get('market_condition_score', 0.5) * 0.2
            
            # Calculate total quality score
            quality_score = (
                basic_strength +
                htf_alignment +
                entry_confirmation +
                market_condition
            ) * 100
            
            logger.info(f"📊 Trade Quality Score for {signal_data.get('symbol')}: {quality_score:.1f}/100")
            logger.info(f"   Basic Strength: {basic_strength:.1f}")
            logger.info(f"   HTF Alignment: {htf_alignment:.1f}")
            logger.info(f"   Entry Confirmation: {entry_confirmation:.1f}")
            logger.info(f"   Market Condition: {market_condition:.1f}")
            
            return quality_score
            
        except Exception as e:
            logger.error(f"❌ Error calculating quality score: {e}")
            return 0.0
    
    def update_daily_profit(self, profit_amount: float):
        """Update daily profit tracking"""
        self.daily_profit += profit_amount
        logger.info(f"� Daily Profit Updated: {profit_amount:+.2f}% (Total: {self.daily_profit:+.2f}%)")
    
    def log_trade_execution(self, symbol: str, confidence: float, result: str, profit: float = 0.0):
        """Log trade execution for performance tracking"""
        trade_log = {
            "timestamp": datetime.now().isoformat(),
            "symbol": symbol,
            "result": result,
            "confidence": confidence,
            "profit": profit
        }
        
        # Add to trade history (would need to initialize this in __init__)
        if not hasattr(self, 'trade_log'):
            self.trade_log = []
        
        self.trade_log.append(trade_log)
        
        logger.info(f"📊 Trade Logged: {symbol} {result} ({confidence}% confidence, {profit:+.2f}% profit)")
    
    def execute_auto_trade(self, signal_data: Dict) -> bool:
        """
        Execute automatic trade with full validation
        
        Args:
            signal_data: Signal analysis data
            
        Returns:
            bool: True if trade executed successfully
        """
        with self.execution_lock:  # Thread safety
            try:
                # Validate trade
                should_execute, reason = self.should_execute_trade(signal_data)
                
                if not should_execute:
                    logger.info(f"🚫 Trade blocked: {reason}")
                    return False
                
                # Extract trade parameters
                symbol = signal_data.get('symbol', '')
                signal = signal_data.get('signal', '')
                confidence = signal_data.get('confidence', 0)
                structure_sl = signal_data.get('structure_sl', 0)
                structure_tp = signal_data.get('structure_tp', 0)
                
                # Calculate lot size
                current_price = signal_data.get('current_price', 0)
                if signal == 'BUY':
                    stop_loss_pips = abs(current_price - structure_sl) * 10000
                else:
                    stop_loss_pips = abs(structure_sl - current_price) * 10000
                
                lot_size = self.calculate_lot_size(symbol, stop_loss_pips)
                
                if not self.apply_all_filters(symbol, signal, confidence, signal_data):
                    logger.info(f"🚫 Trade blocked by professional filters")
                    return False
                
                logger.info(f"🤖 Executing auto trade:")
                logger.info(f"   Symbol: {symbol}")
                logger.info(f"   Type: {signal}")
                logger.info(f"   Confidence: {confidence}%")
                logger.info(f"   Lot Size: {lot_size}")
                logger.info(f"   SL: {structure_sl}")
                logger.info(f"   TP: {structure_tp}")
                
                # Execute trade
                result = self.trade_manager.place_trade(
                    symbol=symbol,
                    trade_type=signal,
                    lot_size=lot_size,
                    sl=structure_sl,
                    tp=structure_tp,
                    current_price=current_price
                )
                
                if result.get('success', False):
                    # Update tracking
                    self.last_trade_time[symbol] = datetime.now()
                    self.active_trades.append({
                        'symbol': symbol,
                        'type': signal,
                        'confidence': confidence,
                        'lot_size': lot_size,
                        'sl': structure_sl,
                        'tp': structure_tp,
                        'time': datetime.now()
                    })
                    
                    self.stats['total_trades'] += 1
                    self.stats['successful_trades'] += 1
                    
                    # Send Telegram notification
                    self._send_trade_execution_notification(signal_data, lot_size, True)
                    
                    logger.info(f"✅ Auto trade executed successfully for {symbol}")
                    return True
                    
                else:
                    self.stats['failed_trades'] += 1
                    error_msg = result.get('error', 'Unknown error')
                    logger.error(f"❌ Auto trade failed for {symbol}: {error_msg}")
                    
                    # Send failure notification
                    self._send_trade_execution_notification(signal_data, lot_size, False, error_msg)
                    return False
                    
            except Exception as e:
                self.stats['failed_trades'] += 1
                logger.error(f"❌ Auto trade execution error: {e}")
                return False
    
    def _send_trade_execution_notification(self, signal_data: Dict, lot_size: float, success: bool, error: str = None):
        """Send Telegram notification for trade execution"""
        if not self.telegram_assistant:
            return
        
        try:
            symbol = signal_data.get('symbol', '')
            signal = signal_data.get('signal', '')
            confidence = signal_data.get('confidence', 0)
            sl = signal_data.get('structure_sl', 0)
            tp = signal_data.get('structure_tp', 0)
            
            if success:
                message = f"""🤖 **AUTO TRADE EXECUTED**

💱 **Pair:** {symbol}
📈 **Type:** {signal}
🎯 **Confidence:** {confidence}%
📊 **Lot Size:** {lot_size}
🛡️ **SL:** {sl}
🎯 **TP:** {tp}

⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}"""
            else:
                message = f"""❌ **AUTO TRADE FAILED**

💱 **Pair:** {symbol}
📈 **Type:** {signal}
🎯 **Confidence:** {confidence}%
📊 **Lot Size:** {lot_size}

❌ **Error:** {error}

⏰ **Time:** {datetime.now().strftime('%H:%M:%S')}"""
            
            # Send notification
            self.telegram_assistant.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending trade notification: {e}")
    
    def update_active_trades(self):
        """Update active trades list from MT5"""
        try:
            positions = self.mt5_connector.get_positions()
            self.active_trades = []
            
            for position in positions:
                self.active_trades.append({
                    'symbol': position.get('symbol', ''),
                    'type': 'BUY' if position.get('type', 0) == 0 else 'SELL',
                    'lot_size': position.get('volume', 0),
                    'sl': position.get('sl', 0),
                    'tp': position.get('tp', 0),
                    'time': position.get('open_time', datetime.now())
                })
                
        except Exception as e:
            logger.error(f"Error updating active trades: {e}")
    
    def monitor_trades(self):
        """Monitor active trades for break-even and trailing stop management"""
        try:
            if not self.active_trades:
                return
            
            for trade in self.active_trades:
                try:
                    symbol = trade['symbol']
                    trade_type = trade['type']
                    entry_price = trade.get('entry_price', 0)
                    
                    if not entry_price:
                        continue
                    
                    # Get current price
                    current_price = self._get_current_price(symbol)
                    if not current_price:
                        continue
                    
                    # Calculate profit in pips
                    if trade_type == 'BUY':
                        profit_pips = (current_price - entry_price) * 10000
                    else:  # SELL
                        profit_pips = (entry_price - current_price) * 10000
                    
                    trade_id = f"{symbol}_{trade.get('ticket', 'unknown')}"
                    
                    # 1. CHECK BREAK-EVEN CONDITION
                    if (trade_id not in self.break_even_trades and 
                        profit_pips >= self.break_even_pips):
                        
                        new_sl = entry_price
                        success = self._modify_trade_sl(trade, new_sl)
                        
                        if success:
                            self.break_even_trades[trade_id] = {
                                'original_sl': trade.get('sl'),
                                'break_even_sl': new_sl,
                                'profit_pips': profit_pips,
                                'applied_at': datetime.now()
                            }
                            logger.info(f"🛡️ Break-Even Applied:")
                            logger.info(f"   Symbol: {symbol}")
                            logger.info(f"   Entry: {entry_price:.5f}")
                            logger.info(f"   Profit: {profit_pips:.1f} pips")
                            logger.info(f"   SL Moved: {trade.get('sl', 0):.5f} → {new_sl:.5f}")
                    
                    # 2. CHECK TRAILING STOP CONDITION
                    elif (trade_id in self.break_even_trades and 
                          trade_id not in self.trailing_trades and
                          profit_pips >= self.trailing_start_pips):
                        
                        # Start trailing - activate trailing mode
                        self.trailing_trades[trade_id] = {
                            'start_price': current_price,
                            'start_pips': profit_pips,
                            'activated_at': datetime.now()
                        }
                        logger.info(f"📈 Trailing Stop Activated:")
                        logger.info(f"   Symbol: {symbol}")
                        logger.info(f"   Entry: {entry_price:.5f}")
                        logger.info(f"   Current: {current_price:.5f}")
                        logger.info(f"   Profit: {profit_pips:.1f} pips")
                        logger.info(f"   Trailing Distance: {self.trailing_distance_pips} pips")
                    
                    # 3. UPDATE TRAILING STOP CONTINUOUSLY
                    elif trade_id in self.trailing_trades:
                        # Calculate new trailing stop loss
                        if trade_type == 'BUY':
                            new_sl = current_price - (self.trailing_distance_pips / 10000)
                        else:  # SELL
                            new_sl = current_price + (self.trailing_distance_pips / 10000)
                        
                        # Only move SL up (for BUY) or down (for SELL)
                        current_sl = trade.get('sl', 0)
                        if ((trade_type == 'BUY' and new_sl > current_sl) or
                            (trade_type == 'SELL' and new_sl < current_sl)):
                            
                            success = self._modify_trade_sl(trade, new_sl)
                            
                            if success:
                                self.trailing_trades[trade_id]['last_update'] = {
                                    'new_sl': new_sl,
                                    'current_price': current_price,
                                    'profit_pips': profit_pips,
                                    'updated_at': datetime.now()
                                }
                                logger.info(f"� Trailing Stop Updated:")
                                logger.info(f"   Symbol: {symbol}")
                                logger.info(f"   Current: {current_price:.5f}")
                                logger.info(f"   Profit: {profit_pips:.1f} pips")
                                logger.info(f"   SL Moved: {current_sl:.5f} → {new_sl:.5f}")
                        
                except Exception as e:
                    logger.error(f"❌ Error monitoring trade {trade}: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error in trade monitoring: {e}")
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        try:
            tick = self.trade_manager.mt5.get_symbol_info(symbol)
            if tick and 'bid' in tick and 'ask' in tick:
                return (tick['bid'] + tick['ask']) / 2
            return 0.0
        except Exception as e:
            logger.error(f"❌ Error getting current price for {symbol}: {e}")
            return 0.0
    
    def _modify_trade_sl(self, trade: Dict, new_sl: float) -> bool:
        """Modify stop loss for a trade"""
        try:
            ticket = trade.get('ticket')
            if not ticket:
                return False
            
            # Use trade manager's modify stop loss method
            result = self.trade_manager._modify_stop_loss(trade, new_sl, "Break-Even")
            
            return result.get('success', False) if isinstance(result, dict) else False
            
        except Exception as e:
            logger.error(f"❌ Error modifying SL for trade {trade.get('ticket')}: {e}")
            return False
    
    def get_stats(self) -> Dict:
        """Get trading statistics"""
        return {
            'total_trades': self.stats['total_trades'],
            'successful_trades': self.stats['successful_trades'],
            'failed_trades': self.stats['failed_trades'],
            'success_rate': (self.stats['successful_trades'] / max(1, self.stats['total_trades'])) * 100,
            'break_even_applied': len(self.break_even_trades),
            'trailing_active': len(self.trailing_trades)
        }
    
    def get_statistics(self) -> Dict:
        """Get trading statistics"""
        self.update_active_trades()
        
        return {
            'config': {
                'enabled': self.config.enabled,
                'min_confidence': self.config.min_confidence,
                'max_trades': self.config.max_trades,
                'cooldown_minutes': self.config.cooldown_minutes
            },
            'stats': self.stats.copy(),
            'active_trades': len(self.active_trades),
            'last_trades': dict(self.last_trade_time)
        }
    
    def disable_auto_trading(self):
        """Disable auto trading immediately"""
        self.config.enabled = False
        logger.warning("Auto trading DISABLED")
    
    def enable_auto_trading(self):
        """Enable auto trading"""
        self.config.enabled = True
        logger.info("Auto trading ENABLED")
