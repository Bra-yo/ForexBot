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
        
        logger.info("Auto Trading Manager initialized")
        self._log_config()
    
    def _log_config(self):
        """Log current configuration"""
        logger.info("🤖 Auto Trading Configuration:")
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
    
    def should_execute_trade(self, signal_data: Dict) -> tuple[bool, str]:
        """
        Comprehensive trade validation
        
        Returns:
            tuple: (should_execute, reason)
        """
        # 1. Check if auto trading is enabled
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
            logger.warning("🛑 BAD TRADING DAY - Stopping trading to prevent further losses")
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
        
        logger.info(f"🧠 Trade Stored in Memory: {symbol} {result} ({confidence}% confidence)")
    
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
    
    def adapt_confidence_threshold(self) -> int:
        """Dynamically adjust confidence threshold based on performance"""
        if not self.adaptive_confidence:
            return self.config.min_confidence
        
        success_rate = self.get_success_rate(self.config.min_confidence)
        new_confidence = self.config.min_confidence
        
        if success_rate < 0.5:
            new_confidence = 75
            logger.warning(f"📈 Low success rate ({success_rate:.1%}) - Raising confidence to {new_confidence}%")
        elif success_rate > 0.7:
            new_confidence = 60
            logger.info(f"📈 High success rate ({success_rate:.1%}) - Lowering confidence to {new_confidence}%")
        
        return new_confidence
    
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
    
    def calculate_lot_size(self, symbol: str, stop_loss_pips: float) -> float:
        """Calculate dynamic lot size based on risk management"""
        try:
            # Get account balance
            account_info = self.mt5_connector.get_account_info()
            if not account_info or 'balance' not in account_info:
                logger.error("❌ Cannot get account balance for lot sizing")
                return 0.01
            
            balance = account_info['balance']
            risk_percent = 1.0
            pip_value = 10
            
            # Calculate dynamic lot size
            risk_amount = balance * (risk_percent / 100)
            
            if stop_loss_pips == 0:
                return 0.01
            
            lot = risk_amount / (stop_loss_pips * pip_value)
            lot = round(max(0.01, min(lot, 1.0)), 2)
            
            logger.info(f"💰 Dynamic Lot Sizing:")
            logger.info(f"   Balance: ${balance:,.2f}")
            logger.info(f"   Risk: {risk_percent}% = ${risk_amount:,.2f}")
            logger.info(f"   SL Distance: {stop_loss_pips:.1f} pips")
            logger.info(f"   Calculated Lot: {lot}")
            
            return lot
            
        except Exception as e:
            logger.error(f"❌ Error calculating lot size: {e}")
            return 0.01
    
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
        logger.warning("🛑 Auto trading DISABLED")
    
    def enable_auto_trading(self):
        """Enable auto trading"""
        self.config.enabled = True
        logger.info("✅ Auto trading ENABLED")
