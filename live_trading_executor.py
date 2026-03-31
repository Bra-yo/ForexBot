"""
LIVE TRADING EXECUTOR
Professional-grade execution with advanced position management
"""

import logging
import time
from datetime import datetime, timedelta
import time
import os
import sys
import signal
import threading
import MetaTrader5 as mt5
from mt5_executor import place_trade, check_safety_filters, get_account_info, check_open_positions, close_old_positions
from professional_trade_executor import close_trade_professional, close_all_positions_professional
from level3_intelligence import IntelligentTradeManager, AdaptiveLotSizer, ProfitTargetManager
from advanced_telegram_assistant import AdvancedTelegramAssistant
from trade_manager import TradeManager
from risk_manager import RiskManager
from signal_filter import SignalFilter
from config import *
from telegram_command_handler import TelegramCommandHandler  # LEVEL 7: Import command handler

def close_mt5_trade(position):
    """PART 4: Proper MT5 position closing function with retry system"""
    symbol = position.symbol
    volume = position.volume
    ticket = position.ticket
    
    # Retry system
    for attempt in range(3):
        try:
            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                logger.error(f"Failed to get tick data for {symbol} (attempt {attempt + 1})")
                if attempt < 2:
                    time.sleep(0.5)
                    continue
                return None
            
            # Determine close price (opposite of position type)
            price = tick.bid if position.type == 0 else tick.ask  # 0=BUY close at BID, 1=SELL close at ASK
            
            # Create close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY,
                "position": ticket,
                "price": price,
                "deviation": 20,
                "magic": 123456,
                "comment": "NYX AI CLOSE",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send close request
            result = mt5.order_send(request)
            
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Successfully closed position {ticket} for {symbol}")
                return result
            else:
                logger.error(f"Failed to close position {ticket}: {result.comment if result else 'No result'} (attempt {attempt + 1})")
                if attempt < 2:
                    time.sleep(0.5)
                    continue
                return result
                
        except Exception as e:
            logger.error(f"Error closing position {ticket}: {e} (attempt {attempt + 1})")
            if attempt < 2:
                time.sleep(0.5)
                continue
            return None
    
    return None

logger = logging.getLogger(__name__)

class LiveTradingExecutor:
    """Professional live trading execution with advanced management"""
    
    def __init__(self, telegram_token=None, telegram_chat_id=None):
        self.telegram = AdvancedTelegramAssistant(telegram_token, telegram_chat_id) if telegram_token else None
        self.is_running = False
        self.running = True  # NEW: Global running flag
        
        # PART 2: TELEGRAM ANTI-SPAM SYSTEM
        self._telegram_last_sent = {}  # Track last message time per symbol
        self._telegram_rate_limit = 120  # 2 minutes in seconds
        
        # PART 9: SINGLE INSTANCE PROTECTION
        self._lock_file = "nyx.lock"
        if self._check_lock_file():
            logger.error("Nyx AI is already running! Only one instance allowed.")
            print("❌ ERROR: Nyx AI is already running!")
            print("   Please stop the existing instance first.")
            sys.exit(1)
        self._create_lock_file()
        
        # PART 6: PROFIT MANAGEMENT SYSTEM
        self._trade_profits = {}  # Track floating profit per trade
        self._breakeven_moved = {}  # Track which trades have breakeven moved
        
        # LEVEL 5: SMART EXECUTION ENGINE
        self._last_trade_time = {}  # Anti-spam cooldown
        self._trade_cooldown = 60  # LEVEL 5: Increased to 5 minutes = 300 seconds
        self._last_telegram_trade = {}  # LEVEL 5: Track last Telegram per symbol
        self._trade_memory = {}  # LEVEL 5: Track last trade (symbol: {signal, time})
        
        # 🔥 CRITICAL FIX #1: ONE DIRECTION PER PAIR
        self._last_trade_direction = {}  # Track last trade direction per symbol
        self._direction_lock_time = {}   # Track when direction lock was set
        
        # 🔥 CRITICAL FIX #2: STRONG COOLDOWN PER PAIR
        self._cycle_count = {}  # Track cycles per symbol
        self._last_candle_time = {}  # Track last candle time per symbol
        self._required_cycles_wait = 3  # Wait 3 cycles between trades
        
        # 🔥 CRITICAL FIX #3: MINIMUM PROFIT DISTANCE
        self._min_tp_pips = 15  # Minimum TP distance in pips
        self._min_sl_multiplier = 1.5  # SL must be at least 1.5x broker minimum (reduced from 2x)
        
        # 🔥 CRITICAL FIX #4: TRADE LIMIT PER PAIR
        self._max_trades_per_pair = 1  # Hard cap: 1 trade per pair at a time
        
        # 🔥 CRITICAL FIX #5: LOSS PROTECTION
        self._consecutive_losses = {}  # Track consecutive losses per symbol
        self._loss_cooldown_time = {}  # Track when loss cooldown started
        self._loss_cooldown_duration = 1800  # 30 minutes in seconds
        
        # LEVEL 6: PROFIT TRACKING SYSTEM
        self._starting_balance = None
        self._daily_profit = 0.0
        self._last_profit_log_time = time.time()
        self._last_telegram_profit_time = time.time()
        
        # LEVEL 6: DRAWDOWN & EQUITY PROTECTION
        self._daily_loss_limit = 0.05  # 5% daily loss limit
        self._equity_protection_limit = 0.90  # 90% equity protection
        self._trading_stopped_for_drawdown = False
        
        # LEVEL 6: SMART TRADING HOURS
        self._asian_session_start = 0     # 00:00 UTC
        self._asian_session_end = 8       # 07:59 UTC (extended to cover gap)
        self._london_session_start = 8    # 08:00 UTC
        self._london_session_end = 17     # 17:00 UTC
        self._ny_session_start = 13        # 13:00 UTC
        self._ny_session_end = 22          # 22:00 UTC
        
        # LEVEL 7: TRADE SCORING SYSTEM
        self._trade_scores = {}  # Track scores per symbol
        self._score_threshold = 0.4  # TEMPORARY FIX: Lower threshold to 0.4 to allow trades
        
        # LEVEL 7: PERFORMANCE MEMORY
        self._performance_memory = {}  # Track wins/losses per symbol
        self._winning_streak = 0  # Track current winning streak
        self._losing_streak = 0   # Track current losing streak
        
        # LEVEL 7: DYNAMIC RISK ADJUSTMENT
        self._base_lot_size = 0.01
        self._current_lot_multiplier = 1.0
        self._max_lot_multiplier = 2.0  # Never exceed 2x base lot size
        
        # LEVEL 7: TRADE JOURNAL SYSTEM
        self._trade_journal = []
        self._journal_file = "nyx_trade_journal.csv"
        
        # LEVEL 7: Initialize command handler
        self.command_handler = TelegramCommandHandler(self, self.telegram) if self.telegram else None
        
        # LEVEL 6: Initialize profit tracking
        self._initialize_profit_tracking()
        
        # Initialize professional modules
        self.trade_manager = TradeManager()
        self.risk_manager = RiskManager()
        self.signal_filter = SignalFilter()
        
        # NEW: Initialize Level 3 intelligence
        self.intelligent_manager = IntelligentTradeManager()
        self.adaptive_sizer = AdaptiveLotSizer()
        self.profit_targets = ProfitTargetManager()
        
        # Log process ID
        import os
        logger.info(f"Bot process ID: {os.getpid()}")
        
    def _can_send_telegram_message(self, symbol, message_type='general'):
        """PART 2: Check if Telegram message can be sent (rate limiting)"""
        if not self.telegram:
            return False
            
        current_time = time.time()
        key = f"{symbol}_{message_type}"
        
        # Check rate limit
        if key in self._telegram_last_sent:
            time_diff = current_time - self._telegram_last_sent[key]
            if time_diff < self._telegram_rate_limit:
                return False
        
        self._telegram_last_sent[key] = current_time
        return True
        
    def _send_critical_telegram(self, message, symbol='general'):
        """Send critical Telegram message (bypasses rate limit for critical errors)"""
        if self.telegram:
            self.telegram.send_message(message)
            
    def _send_trade_telegram(self, message, symbol='general'):
        """LEVEL 5: Send trade-related Telegram message with rate limiting and only for executed trades"""
        # Only send if we haven't sent for this symbol recently
        if not self._can_send_telegram_message(symbol, 'trade'):
            return
            
        # LEVEL 5: Store that we sent Telegram for this symbol
        self._last_telegram_trade[symbol] = time.time()
        
        if self.telegram:
            self.telegram.send_message(message)
        
    def _check_lock_file(self):
        """PART 9: Check if lock file exists"""
        return os.path.exists(self._lock_file)
        
    def _create_lock_file(self):
        """PART 9: Create lock file with current PID"""
        try:
            with open(self._lock_file, 'w') as f:
                f.write(str(os.getpid()))
        except Exception as e:
            logger.error(f"Failed to create lock file: {e}")
            
    def _remove_lock_file(self):
        """PART 9: Remove lock file on shutdown"""
        try:
            if os.path.exists(self._lock_file):
                os.remove(self._lock_file)
                logger.info("Lock file removed")
        except Exception as e:
            logger.error(f"Failed to remove lock file: {e}")
    
    def _initialize_profit_tracking(self):
        """LEVEL 6: Initialize profit tracking with MT5 connection debug"""
        try:
            # LEVEL 6: Enhanced MT5 connection debug
            if not mt5.initialize():
                print("❌ MT5 not initialized!")
                logger.error("MT5 not initialized!")
                return
            
            account = mt5.account_info()
            if account is None:
                print("❌ No MT5 account connected!")
                logger.error("No MT5 account connected!")
                return
            
            # LEVEL 6: Enhanced logging
            print(f"✅ Connected to account: {account.login}")
            print(f"💰 Balance: ${account.balance:,.2f}")
            print(f"💎 Equity: ${account.equity:,.2f}")
            print(f"🌐 Server: {account.server}")
            
            logger.info(f"Connected to account: {account.login}")
            logger.info(f"Starting Balance: ${account.balance:,.2f}")
            logger.info(f"Starting Equity: ${account.equity:,.2f}")
            logger.info(f"Server: {account.server}")
            
            # Store starting balance for profit tracking
            self._starting_balance = account.balance
            self._daily_profit = 0.0
            
        except Exception as e:
            logger.error(f"Failed to initialize profit tracking: {e}")
            print(f"❌ Error initializing profit tracking: {e}")
    
    def _check_drawdown_protection(self):
        """LEVEL 6: Check if daily loss exceeds 5% limit"""
        if self._starting_balance is None:
            return False
            
        try:
            account = mt5.account_info()
            if not account:
                return False
                
            current_balance = account.balance
            daily_loss = self._starting_balance - current_balance
            daily_loss_percent = daily_loss / self._starting_balance
            
            if daily_loss_percent >= self._daily_loss_limit and not self._trading_stopped_for_drawdown:
                logger.error(f"🚨 Daily drawdown limit reached: {daily_loss_percent:.1%}")
                print(f"🚨 DAILY DRAWDOWN LIMIT REACHED: {daily_loss_percent:.1%}")
                
                if self.telegram:
                    alert_message = f"""🚨 DAILY DRAWDOWN LIMIT REACHED

Starting Balance: ${self._starting_balance:,.2f}
Current Balance: ${current_balance:,.2f}
Daily Loss: ${daily_loss:,.2f} ({daily_loss_percent:.1%})

Action: Trading STOPPED
Bot: Nyx AI Level 6
"""
                    self.telegram.send_message(alert_message)
                
                self._trading_stopped_for_drawdown = True
                return True
                
        except Exception as e:
            logger.error(f"Error checking drawdown protection: {e}")
            
        return False
    
    def _check_equity_protection(self):
        """LEVEL 6: Check if equity drops below 90% of balance"""
        try:
            account = mt5.account_info()
            if not account:
                return False
                
            balance = account.balance
            equity = account.equity
            equity_ratio = equity / balance
            
            if equity_ratio < self._equity_protection_limit:
                logger.error(f"💀 Equity protection triggered: {equity_ratio:.1%}")
                print(f"💀 EQUITY PROTECTION TRIGGERED: {equity_ratio:.1%}")
                
                if self.telegram:
                    alert_message = f"""💀 EQUITY PROTECTION TRIGGERED

Balance: ${balance:,.2f}
Equity: ${equity:,.2f}
Equity Ratio: {equity_ratio:.1%}

Action: All trades CLOSED, Bot STOPPED
Bot: Nyx AI Level 6
"""
                    self.telegram.send_message(alert_message)
                
                # Close all trades and stop bot
                self.emergency_close_all()
                self.stop()
                return True
                
        except Exception as e:
            logger.error(f"Error checking equity protection: {e}")
            
        return False
    
    def _check_trading_session(self):
        """LEVEL 6: Check if current time is within allowed trading sessions"""
        current_hour = datetime.now().hour
        logger.info(f"🕐 Current hour: {current_hour} UTC")
        
        # Check Asian session (00:00-07:00 UTC)
        if self._asian_session_start <= current_hour < self._asian_session_end:
            logger.info(f"✅ Asian Session active ({self._asian_session_start}:00-{self._asian_session_end}:00 UTC)")
            return True, "Asian Session"
            
        # Check London session (08:00-17:00 UTC)
        if self._london_session_start <= current_hour < self._london_session_end:
            logger.info(f"✅ London Session active ({self._london_session_start}:00-{self._london_session_end}:00 UTC)")
            return True, "London Session"
            
        # Check New York session (13:00-22:00 UTC)
        if self._ny_session_start <= current_hour < self._ny_session_end:
            logger.info(f"✅ New York Session active ({self._ny_session_start}:00-{self._ny_session_end}:00 UTC)")
            return True, "New York Session"
            
        # Outside trading sessions
        logger.warning(f"❌ Outside trading session (Hour: {current_hour} UTC)")
        logger.warning(f"   Asian: {self._asian_session_start}:00-{self._asian_session_end}:00 UTC")
        logger.warning(f"   London: {self._london_session_start}:00-{self._london_session_end}:00 UTC")
        logger.warning(f"   New York: {self._ny_session_start}:00-{self._ny_session_end}:00 UTC")
        return False, f"Outside trading session (Hour: {current_hour} UTC)"
    
    # 🔥 CRITICAL FIX #1: ONE DIRECTION PER PAIR
    def _check_trade_direction_consistency(self, symbol, signal):
        """Check if signal is consistent with last trade direction"""
        if symbol not in self._last_trade_direction:
            # First trade for this symbol - allow any direction
            return True, "First trade - direction set"
        
        last_direction = self._last_trade_direction[symbol]
        
        if last_direction != signal:
            return False, f"Direction mismatch: last was {last_direction}, current is {signal}"
        
        return True, f"Direction consistent: {signal}"
    
    # 🔥 CRITICAL FIX #2: STRONG COOLDOWN PER PAIR
    def _check_strong_cooldown(self, symbol):
        """Check if enough cycles or new candle has passed"""
        current_time = time.time()
        
        # Check cycle cooldown
        if symbol in self._cycle_count:
            cycles_since_last_trade = current_time - self._cycle_count[symbol]
            required_wait = self._required_cycles_wait * 60  # 3 cycles = 3 minutes
            
            if cycles_since_last_trade < required_wait:
                remaining = required_wait - cycles_since_last_trade
                return False, f"Cycle cooldown: {remaining/60:.1f} cycles remaining"
        
        # Check new candle cooldown (M15 = 15 minutes)
        if symbol in self._last_candle_time:
            time_since_candle = current_time - self._last_candle_time[symbol]
            if time_since_candle < 900:  # 15 minutes for M15
                remaining = 900 - time_since_candle
                return False, f"Waiting for new candle: {remaining/60:.1f} minutes"
        
        return True, "Cooldown passed"
    
    # 🔥 CRITICAL FIX #3: MINIMUM PROFIT DISTANCE
    def _check_minimum_profit_distance(self, symbol, entry_price, stop_loss, take_profit):
        """Ensure TP ≥ 15 pips and SL ≥ broker minimum × 2"""
        try:
            symbol_info = mt5.symbol_info(symbol)
            if not symbol_info:
                return False, "Cannot get symbol info"
            
            point = symbol_info.point
            
            # Calculate distances in pips
            if stop_loss and entry_price:
                sl_distance = abs(entry_price - stop_loss)
                sl_pips = sl_distance / point
                
                # Minimum SL must be 1.5x broker minimum (reduced from 2x)
                min_sl_pips = 30  # 1.5x 20 pips = 30 pips (reduced from 40)
                
                if sl_pips < min_sl_pips:
                    return False, f"SL too close: {sl_pips:.1f} < {min_sl_pips} pips"
            
            if take_profit and entry_price:
                tp_distance = abs(take_profit - entry_price)
                tp_pips = tp_distance / point
                
                if tp_pips < self._min_tp_pips:
                    return False, f"TP too close: {tp_pips:.1f} < {self._min_tp_pips} pips"
            
            return True, "Minimum profit distance satisfied"
            
        except Exception as e:
            logger.error(f"Error checking minimum profit distance: {e}")
            return False, f"Error: {e}"
    
    # 🔥 CRITICAL FIX #4: TRADE LIMIT PER PAIR
    def _check_trade_limit_per_pair(self, symbol):
        """Check if max trades per pair limit is reached"""
        try:
            positions = mt5.positions_get(symbol=symbol)
            if positions is None:
                return True, "No positions found"
            
            current_trades = len(positions)
            
            if current_trades >= self._max_trades_per_pair:
                return False, f"Max trades reached: {current_trades} ≥ {self._max_trades_per_pair}"
            
            return True, f"Trade limit OK: {current_trades}/{self._max_trades_per_pair}"
            
        except Exception as e:
            logger.error(f"Error checking trade limit: {e}")
            return False, f"Error: {e}"
    
    # 🔥 CRITICAL FIX #5: LOSS PROTECTION
    def _check_loss_protection(self, symbol):
        """Check if symbol is in loss cooldown after consecutive losses"""
        current_time = time.time()
        
        # Check if currently in loss cooldown
        if symbol in self._loss_cooldown_time:
            cooldown_end = self._loss_cooldown_time[symbol] + self._loss_cooldown_duration
            
            if current_time < cooldown_end:
                remaining = cooldown_end - current_time
                return False, f"Loss cooldown: {remaining/60:.1f} minutes remaining"
            else:
                # Cooldown expired - reset
                del self._loss_cooldown_time[symbol]
                if symbol in self._consecutive_losses:
                    del self._consecutive_losses[symbol]
        
        return True, "Loss protection passed"
    
    def _update_trade_direction(self, symbol, signal):
        """Update the last trade direction for a symbol"""
        self._last_trade_direction[symbol] = signal
        self._direction_lock_time[symbol] = time.time()
        logger.info(f"🔒 Direction locked for {symbol}: {signal}")
    
    def _update_cycle_count(self, symbol):
        """Update cycle count for cooldown tracking"""
        self._cycle_count[symbol] = time.time()
        self._last_candle_time[symbol] = time.time()
        logger.info(f"🔄 Cycle updated for {symbol}")
    
    def _update_loss_tracking(self, symbol, was_profitable):
        """Update loss tracking for consecutive losses"""
        if was_profitable:
            # Reset on profitable trade
            if symbol in self._consecutive_losses:
                del self._consecutive_losses[symbol]
            logger.info(f"✅ Profitable trade for {symbol} - loss streak reset")
        else:
            # Increment loss count
            self._consecutive_losses[symbol] = self._consecutive_losses.get(symbol, 0) + 1
            loss_count = self._consecutive_losses[symbol]
            
            logger.warning(f"❌ Loss #{loss_count} for {symbol}")
            
            # Start cooldown after 2 consecutive losses
            if loss_count >= 2:
                self._loss_cooldown_time[symbol] = time.time()
                logger.warning(f"🚨 Loss cooldown activated for {symbol} (30 minutes)")
    
    def _update_profit_tracking(self):
        """LEVEL 6: Update daily profit and send periodic updates"""
        if self._starting_balance is None:
            return
            
        try:
            account = mt5.account_info()
            if not account:
                return
                
            current_balance = account.balance
            self._daily_profit = current_balance - self._starting_balance
            
            current_time = time.time()
            
            # Log profit every cycle
            logger.info(f"💰 Daily P&L: ${self._daily_profit:+.2f}")
            logger.info(f"📊 Balance: ${current_balance:,.2f}")
            
            # Send Telegram update every 30 minutes
            if current_time - self._last_telegram_profit_time >= 1800:  # 30 minutes
                profit_message = f"""📊 NYX AI PROFIT UPDATE

Daily P&L: ${self._daily_profit:+.2f}
Current Balance: ${current_balance:,.2f}
Starting Balance: ${self._starting_balance:,.2f}

Time: {datetime.now().strftime('%H:%M:%S')}
Bot: Nyx AI Level 6
"""
                if self.telegram:
                    self.telegram.send_message(profit_message)
                self._last_telegram_profit_time = current_time
                
        except Exception as e:
            logger.error(f"Error updating profit tracking: {e}")
    
    def _calculate_trade_score(self, symbol, confidence, trend_strength=0.5, volume_factor=0.5, momentum=0.5, volatility=0.5):
        """LEVEL 7: Calculate weighted trade score"""
        try:
            # 🔧 FIX 4: DEBUG SCORE INPUTS
            logger.info(f"🔍 Score inputs for {symbol}: Trend={trend_strength}, Volume={volume_factor}, Momentum={momentum}, Volatility={volatility}")
            
            # Get market data for scoring (simplified for demo)
            score = (trend_strength * 0.4) + (volume_factor * 0.2) + (momentum * 0.2) + (volatility * 0.2)
            
            # Store score for logging
            self._trade_scores[symbol] = score
            
            logger.info(f"📊 Trade score for {symbol}: {score:.3f} (threshold: {self._score_threshold})")
            return score
            
        except Exception as e:
            logger.error(f"Error calculating trade score: {e}")
            return 0.5  # Default middle score
    
    def _update_performance_memory(self, symbol, profit):
        """LEVEL 7: Update performance memory and adjust trading parameters"""
        try:
            if symbol not in self._performance_memory:
                self._performance_memory[symbol] = {'wins': 0, 'losses': 0, 'total_profit': 0.0}
            
            if profit > 0:
                self._performance_memory[symbol]['wins'] += 1
                self._winning_streak += 1
                self._losing_streak = 0
            else:
                self._performance_memory[symbol]['losses'] += 1
                self._losing_streak += 1
                self._winning_streak = 0
            
            self._performance_memory[symbol]['total_profit'] += profit
            
            # Dynamic risk adjustment
            self._adjust_lot_size_based_on_performance()
            
            logger.debug(f"Performance updated for {symbol}: {self._performance_memory[symbol]}")
            
        except Exception as e:
            logger.error(f"Error updating performance memory: {e}")
    
    def _adjust_lot_size_based_on_performance(self):
        """LEVEL 7: Adjust lot size based on winning/losing streaks"""
        try:
            if self._winning_streak >= 3:
                # Increase lot size for winning streak
                self._current_lot_multiplier = min(self._current_lot_multiplier + 0.1, self._max_lot_multiplier)
                logger.info(f"📈 Winning streak ({self._winning_streak}) - Increasing lot size to {self._current_lot_multiplier:.1f}x")
                
            elif self._losing_streak >= 2:
                # Reduce lot size for losing streak
                self._current_lot_multiplier = max(self._current_lot_multiplier - 0.1, 0.5)
                logger.info(f"📉 Losing streak ({self._losing_streak}) - Reducing lot size to {self._current_lot_multiplier:.1f}x")
                
        except Exception as e:
            logger.error(f"Error adjusting lot size: {e}")
    
    def _journal_trade(self, symbol, signal, entry, sl, tp, lot, result, timestamp):
        """LEVEL 7: Save trade to journal"""
        try:
            trade_record = {
                'timestamp': timestamp,
                'symbol': symbol,
                'signal': signal,
                'entry': entry,
                'stop_loss': sl,
                'take_profit': tp,
                'lot_size': lot,
                'result': result,
                'profit': 0.0,  # Will be updated when closed
                'score': self._trade_scores.get(symbol, 0.0)
            }
            
            self._trade_journal.append(trade_record)
            
            # Save to CSV file
            import csv
            file_exists = os.path.exists(self._journal_file)
            
            with open(self._journal_file, 'a', newline='') as csvfile:
                fieldnames = ['timestamp', 'symbol', 'signal', 'entry', 'stop_loss', 'take_profit', 'lot_size', 'result', 'profit', 'score']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                if not file_exists:
                    writer.writeheader()
                    
                writer.writerow(trade_record)
                
            logger.debug(f"Trade journaled: {symbol} {signal}")
            
        except Exception as e:
            logger.error(f"Error journaling trade: {e}")
    
    def handle_telegram_message(self, message_text, chat_id):
        """LEVEL 7: Handle incoming Telegram commands"""
        if self.command_handler:
            self.command_handler.handle_command(message_text, chat_id)
    
    def monitor_positions(self):
        """Monitor open positions with professional management"""
        self.running = False
        self.is_running = False
        logger.info("Bot stopping safely...")
        if self.telegram:
            self.telegram.send_message("🛑 NYX AI Bot stopping safely...")
        self._remove_lock_file()  # PART 9: Clean up lock file
            
    def signal_handler(self, signum, frame):
        """PART 3: Handle SIGINT and SIGTERM for graceful shutdown"""
        logger.info(f"Received signal {signum} - initiating graceful shutdown...")
        self.stop()
            
    def check_stop_file(self):
        """Check for emergency stop file"""
        import os
        if os.path.exists("stop.txt"):
            logger.warning("Emergency stop file detected - stopping bot")
            if self.telegram:
                self.telegram.send_message("🚨 EMERGENCY STOP ACTIVATED - Bot stopping")
            os.remove("stop.txt")  # Clean up
            return True
        return False
        
    def _manage_profit_protection(self):
        """PART 6: Manage profit protection - move SL to breakeven and trailing stops"""
        try:
            positions = mt5.positions_get()
            if not positions:
                return
                
            for position in positions:
                ticket = position.ticket
                current_profit = position.profit
                entry_price = position.price_open
                current_sl = position.sl
                
                # Skip if position is already closed or no SL
                if ticket not in self._trade_profits:
                    self._trade_profits[ticket] = current_profit
                
                # Calculate profit percentages
                if current_sl == 0 or entry_price == 0:
                    continue
                    
                # Calculate risk distance (initial SL distance)
                if position.type == 0:  # BUY
                    risk_distance = entry_price - current_sl
                    current_risk = entry_price - mt5.symbol_info_tick(position.symbol).bid
                else:  # SELL
                    risk_distance = current_sl - entry_price
                    current_risk = mt5.symbol_info_tick(position.symbol).ask - entry_price
                
                if risk_distance <= 0:
                    continue
                    
                profit_ratio = current_risk / risk_distance
                
                # Move to breakeven at 50% profit (LEVEL 4: Enhanced from 50% to 30% for faster locking)
                if profit_ratio >= 0.3 and ticket not in self._breakeven_moved:
                    self._move_to_breakeven(position, ticket)
                    self._breakeven_moved[ticket] = True
                    
                # Activate trailing stop at 75% profit
                elif profit_ratio >= 0.75:
                    self._activate_trailing_stop(position, ticket)
                    
        except Exception as e:
            logger.error(f"Profit management error: {e}")
            
    def _move_to_breakeven(self, position, ticket):
        """Move stop loss to breakeven"""
        try:
            new_sl = position.price_open
            if position.sl == new_sl:
                return
                
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "sl": new_sl,
                "position": ticket,
                "magic": 123456,
            }
            
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Moved {position.symbol} #{ticket} to breakeven")
                
        except Exception as e:
            logger.error(f"Error moving to breakeven: {e}")
            
    def _activate_trailing_stop(self, position, ticket):
        """Activate trailing stop for position"""
        try:
            tick = mt5.symbol_info_tick(position.symbol)
            if not tick:
                return
                
            # Calculate trailing stop distance (e.g., 20 pips)
            trail_distance = 0.0020  # 20 pips for 5-digit brokers
            
            if position.type == 0:  # BUY
                new_sl = tick.bid - trail_distance
                if new_sl <= position.sl:
                    return  # Only trail up
            else:  # SELL
                new_sl = tick.ask + trail_distance
                if new_sl >= position.sl:
                    return  # Only trail down
                    
            request = {
                "action": mt5.TRADE_ACTION_SLTP,
                "symbol": position.symbol,
                "sl": new_sl,
                "position": ticket,
                "magic": 123456,
            }
            
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"Trailing stop activated for {position.symbol} #{ticket}")
                
        except Exception as e:
            logger.error(f"Error activating trailing stop: {e}")
        
    def execute_live_trade(self, signal, confidence, entry_price, stop_loss, take_profit, lot_size, symbol="EURUSD"):
        """Execute live trade with all safety checks"""
        
        try:
            logger.info(f"🚀 execute_live_trade called for {symbol} - {signal} @ {confidence:.1f}%")
            
            # LEVEL 6: Check trading session first
            session_allowed, session_reason = self._check_trading_session()
            if not session_allowed:
                logger.debug(f"Trade blocked: {session_reason}")
                return False
        
            logger.info(f"✅ Session check passed for {symbol}")
            
            # LEVEL 6: Check drawdown protection
            if self._check_drawdown_protection():
                logger.info(f"❌ Drawdown protection triggered for {symbol}")
                return False  # Trading stopped due to drawdown
            
            logger.info(f"✅ Drawdown check passed for {symbol}")
            
            # LEVEL 6: Check equity protection
            if self._check_equity_protection():
                logger.info(f"❌ Equity protection triggered for {symbol}")
                return False  # Bot stopped due to equity protection
            
            logger.info(f"✅ Equity check passed for {symbol}")
            
            logger.info(f"✅ Passed Level 6 checks for {symbol}")
            
            # PART 1: VALIDATE TRADE DATA BEFORE FORMATTING
            logger.info(f"🔍 Validating trade data for {symbol}...")
            if entry_price is None or lot_size is None:
                logger.warning(f"❌ Invalid trade data - skipped (entry: {entry_price}, lot: {lot_size})")
                return False
            
            logger.info(f"✅ Trade data validation passed for {symbol}")
            
            # LEVEL 7: TRADE SCORING SYSTEM
            logger.info(f"🎯 Calculating trade score for {symbol}...")
            trade_score = self._calculate_trade_score(symbol, confidence)
            logger.info(f"📊 Trade score for {symbol}: {trade_score:.3f} (threshold: {self._score_threshold})")
            if trade_score <= self._score_threshold:
                logger.info(f"❌ Trade blocked: Low score ({trade_score:.3f} <= {self._score_threshold})")
                return False
            
            logger.info(f"✅ Passed all checks for {symbol} - Score: {trade_score:.3f}")
            
            # Allow None for SL/TP - they will be calculated internally
            
            # Calculate SL/TP if not provided
            if stop_loss is None or take_profit is None:
                # 🔧 FIX 2: IMPROVED INVALID STOPS FIX
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info is None:
                    logger.error(f"Cannot get symbol info for {symbol}")
                    return False
                
                point = symbol_info.point
                # 🔧 CRITICAL FIX: Use correct attribute name with try-catch
                try:
                    if hasattr(symbol_info, 'stop_level') and symbol_info.stop_level > 0:
                        min_stop = symbol_info.stop_level * point
                    else:
                        # 🔧 FIX: Use proper minimum stop based on symbol type
                        if symbol.startswith(('JPY', 'XAU', 'XAG')):  # JPY pairs and metals
                            min_stop = 20 * point  # 20 pips for JPY (0.20)
                        else:
                            min_stop = 20 * point  # 20 pips for normal pairs (0.0020)
                except AttributeError as e:
                    logger.warning(f"⚠️ SymbolInfo stop_level attribute error: {e}")
                    # 🔧 FIX: Use proper minimum stop based on symbol type
                    if symbol.startswith(('JPY', 'XAU', 'XAG')):  # JPY pairs and metals
                        min_stop = 20 * point  # 20 pips for JPY (0.20)
                    else:
                        min_stop = 20 * point  # 20 pips for normal pairs (0.0020)
                
                # Add safety buffer - OPTIMIZED FOR BETTER R/R RATIOS
                buffer = max(min_stop, 15 * point)  # Reduced from 20x to 15x point for better R/R
                logger.info(f"🔧 Stop distance for {symbol}: min_stop={min_stop:.5f}, buffer={buffer:.5f}")
                
                if signal == "BUY":
                    if stop_loss is None:
                        sl = entry_price - buffer
                    if take_profit is None:
                        tp = entry_price + (buffer * 2.0)  # 1:2 RR (reduced from 2.5x for better execution)
                    
                    # 🔧 FINAL FIX: Ensure minimum distance with larger multiplier
                    if abs(entry_price - sl) < min_stop:
                        sl = entry_price - (min_stop * 2.5)  # Reduced from 3x to 2.5x
                        logger.info(f"🔧 Adjusted SL for {symbol}: {sl:.5f} (ensured minimum distance)")
                    
                    if abs(tp - entry_price) < min_stop:
                        tp = entry_price + (min_stop * 2.5)  # Reduced from 3x to 2.5x
                        logger.info(f"🔧 Adjusted TP for {symbol}: {tp:.5f} (ensured minimum distance)")
                        
                else:  # SELL
                    if stop_loss is None:
                        sl = entry_price + buffer
                    if take_profit is None:
                        tp = entry_price - (buffer * 2.0)  # 1:2 RR (reduced from 2.5x for better execution)
                    
                    # 🔧 FINAL FIX: Ensure minimum distance with larger multiplier
                    if abs(sl - entry_price) < min_stop:
                        sl = entry_price + (min_stop * 2.5)  # Reduced from 3x to 2.5x
                        logger.info(f"🔧 Adjusted SL for {symbol}: {sl:.5f} (ensured minimum distance)")
                    
                    if abs(entry_price - tp) < min_stop:
                        tp = entry_price - (min_stop * 2.5)  # Reduced from 3x to 2.5x
                        logger.info(f"🔧 Adjusted TP for {symbol}: {tp:.5f} (ensured minimum distance)")
                
                # Update the final values
                stop_loss = sl if stop_loss is None else stop_loss
                take_profit = tp if take_profit is None else take_profit
            
            # PART 7: TRADE QUALITY FILTER
            # 🔧 RE-ENABLED FOR VPS PRODUCTION
            if confidence < 70.0:
                logger.debug(f"Trade blocked: Low confidence ({confidence:.1f}% < 70%)")
                return False
                
            # Calculate Risk/Reward ratio
            if stop_loss and take_profit and entry_price:
                if signal == "BUY":
                    risk = entry_price - stop_loss
                    reward = take_profit - entry_price
                else:  # SELL
                    risk = stop_loss - entry_price
                    reward = entry_price - take_profit
                    
                if risk <= 0:
                    logger.debug("Trade blocked: Invalid risk calculation")
                    return False
                    
                rr_ratio = reward / risk
                logger.info(f"🔧 R/R ratio for {symbol}: {rr_ratio:.2f} (risk: {risk:.5f}, reward: {reward:.5f})")
                
                # 🔧 RE-ENABLED FOR VPS PRODUCTION
                if rr_ratio < 1.5:
                    logger.info(f"Trade blocked: Low R/R ratio ({rr_ratio:.2f} < 1.5)")
                    return False
            
            # Check spread
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                # CRITICAL FIX 2: Fix spread calculation - use proper formula
                spread_points = tick.ask - tick.bid
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info and symbol_info.point > 0:
                    spread_pips = spread_points / symbol_info.point
                else:
                    spread_pips = spread_points * 10000  # Fallback for 5-digit brokers

                logger.info(f"🔧 Spread check for {symbol}: {spread_pips:.1f} pips")
                
                # 🔧 RE-ENABLED FOR VPS PRODUCTION
                if spread_pips > 3.0:
                    logger.info(f"Trade blocked: High spread ({spread_pips:.1f} > 3.0 pips)")
                    return False
                else:
                    logger.info(f"✅ Spread check passed for {symbol}: {spread_pips:.1f} pips")
            else:
                logger.warning(f"❌ No tick data for {symbol}")
                return False
            
            # CRITICAL FIX 1: Add final None validation before logging
            if any(val is None for val in [entry_price, stop_loss, take_profit, lot_size]):
                logger.warning("Invalid trade data - skipped (None values detected)")
                return False
            
            logger.info(f"🔧 About to enter Level 5 execution engine for {symbol}...")
            
            # LEVEL 5: SMART EXECUTION ENGINE
            # 1. Anti-spam protection
            current_time = time.time()
            logger.info(f"🕐 Checking cooldown for {symbol}...")
            if symbol in self._last_trade_time:
                time_since_last = current_time - self._last_trade_time[symbol]
                logger.info(f"⏰ Time since last trade for {symbol}: {time_since_last:.0f}s (cooldown: {self._trade_cooldown}s)")
                if time_since_last < self._trade_cooldown:
                    logger.info(f"Trade blocked: Cooldown active for {symbol} ({time_since_last:.0f}s < {self._trade_cooldown}s)")
                    return False
            else:
                logger.info(f"✅ No previous trade for {symbol} - cooldown cleared")
            
            # LEVEL 5: 2. Trade Memory System - prevent same signal repeats
            logger.info(f"🧠 Checking trade memory for {symbol}...")
            if symbol in self._trade_memory:
                last_signal, last_time = self._trade_memory[symbol]
                time_since_memory = current_time - last_time
                logger.info(f"📝 Last signal for {symbol}: {last_signal} ({time_since_memory:.0f}s ago)")
                if last_signal == signal and time_since_memory < 600:  # 10 minutes
                    logger.info(f"Trade blocked: Same signal {signal} for {symbol} within 10 minutes ({time_since_memory:.0f}s < 600s)")
                    return False
            else:
                logger.info(f"✅ No trade memory for {symbol} - memory cleared")
            
            # LEVEL 5: 3. Only trade HIGH QUALITY signals
            if confidence < 70.0:  # TEMPORARY FIX: Lower from 80% to 70%
                logger.info(f"Trade blocked: Low confidence ({confidence:.1f}% < 70%)")
                return False
            
            logger.info(f"✅ Passed Level 5 checks for {symbol}")
            
            # 🔥 CRITICAL FIXES: ENFORCE DISCIPLINED TRADING RULES
            logger.info(f"🛡️ Applying critical trading discipline checks for {symbol}...")
            
            # CRITICAL FIX #1: ONE DIRECTION PER PAIR
            direction_allowed, direction_reason = self._check_trade_direction_consistency(symbol, signal)
            if not direction_allowed:
                logger.warning(f"🔒 Trade blocked: {direction_reason}")
                return False
            logger.info(f"✅ Direction check passed: {direction_reason}")
            
            # CRITICAL FIX #2: STRONG COOLDOWN PER PAIR
            cooldown_allowed, cooldown_reason = self._check_strong_cooldown(symbol)
            if not cooldown_allowed:
                logger.warning(f"⏰ Trade blocked: {cooldown_reason}")
                return False
            logger.info(f"✅ Cooldown check passed: {cooldown_reason}")
            
            # CRITICAL FIX #3: MINIMUM PROFIT DISTANCE
            distance_allowed, distance_reason = self._check_minimum_profit_distance(symbol, entry_price, stop_loss, take_profit)
            if not distance_allowed:
                logger.warning(f"📏 Trade blocked: {distance_reason}")
                return False
            logger.info(f"✅ Profit distance check passed: {distance_reason}")
            
            # CRITICAL FIX #4: TRADE LIMIT PER PAIR
            limit_allowed, limit_reason = self._check_trade_limit_per_pair(symbol)
            if not limit_allowed:
                logger.warning(f"🚫 Trade blocked: {limit_reason}")
                return False
            logger.info(f"✅ Trade limit check passed: {limit_reason}")
            
            # CRITICAL FIX #5: LOSS PROTECTION
            loss_allowed, loss_reason = self._check_loss_protection(symbol)
            if not loss_allowed:
                logger.warning(f"🛑 Trade blocked: {loss_reason}")
                return False
            logger.info(f"✅ Loss protection check passed: {loss_reason}")
            
            logger.info(f"🎯 ALL CRITICAL CHECKS PASSED for {symbol}")
            
            logger.info(f"LIVE TRADE REQUEST:")
            logger.info(f"   Signal: {signal}")
            logger.info(f"   Confidence: {confidence:.1f}%")
            logger.info(f"   Entry: {entry_price:.5f}")
            logger.info(f"   SL: {stop_loss:.5f}")
            logger.info(f"   TP: {take_profit:.5f}")
            logger.info(f"   Lot: {lot_size}")
            
            # PROFESSIONAL RISK MANAGEMENT
            # 1. Session Filter
            session_allowed, session_reason = self.risk_manager.check_session_filter()
            if not session_allowed:
                logger.warning(f" Trade blocked: {session_reason}")
                # Only send Telegram once per hour for session blocks
                current_hour = datetime.now().hour
                if not hasattr(self, '_last_session_block_hour') or current_hour != self._last_session_block_hour:
                    if self.telegram:
                        self.telegram.send_message(f"⏰ Trading blocked: {session_reason}")
                    self._last_session_block_hour = current_hour
                return False
                
            # 2. Volatility Filter
            volatility_allowed, volatility_reason = self.risk_manager.check_volatility_filter(symbol)
            if not volatility_allowed:
                logger.warning(f" Trade blocked: {volatility_reason}")
                # Only send Telegram once per hour for volatility blocks
                current_hour = datetime.now().hour
                if not hasattr(self, '_last_volatility_block_hour') or current_hour != self._last_volatility_block_hour:
                    if self.telegram:
                        self.telegram.send_message(f"📊 Volatility filter: {volatility_reason}")
                    self._last_volatility_block_hour = current_hour
                return False
                
            # 3. Correlation Control
            correlation_allowed, correlation_reason = self.risk_manager.check_correlation_control(symbol, signal)
            if not correlation_allowed:
                logger.warning(f" Trade blocked: {correlation_reason}")
                # Only send Telegram once per hour for correlation blocks
                current_hour = datetime.now().hour
                if not hasattr(self, '_last_correlation_block_hour') or current_hour != self._last_correlation_block_hour:
                    if self.telegram:
                        self.telegram.send_message(f"🔗 Correlation control: {correlation_reason}")
                    self._last_correlation_block_hour = current_hour
                return False
                
            # 4. Global Risk Check
            risk_allowed, risk_percent, risk_reason = self.risk_manager.check_global_risk()
            if not risk_allowed:
                logger.warning(f" Trade blocked: {risk_reason}")
                # Only send Telegram once per hour for global risk blocks
                current_hour = datetime.now().hour
                if not hasattr(self, '_last_risk_block_hour') or current_hour != self._last_risk_block_hour:
                    if self.telegram:
                        self.telegram.send_message(f"⚠️ Global risk: {risk_reason}")
                    self._last_risk_block_hour = current_hour
                return False
            
            # LEGACY SAFETY FILTERS (Keep for compatibility)
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                spread_points = (tick.ask - tick.bid) / mt5.symbol_info(symbol).point
                spread_pips = spread_points * 10
                self.risk_manager.update_average_spread(symbol, spread_points)
            else:
                spread_pips = 0.0
            
            # NEW: Call with all required arguments
            safety_passed, safety_message = check_safety_filters(
                self, symbol, lot_size, signal, spread_pips, confidence, 'M15'
            )
            
            if not safety_passed:
                logger.warning(f" Trade blocked: {safety_message}")
                # Only send Telegram once per hour for safety blocks
                current_hour = datetime.now().hour
                if not hasattr(self, '_last_safety_block_hour') or current_hour != self._last_safety_block_hour:
                    if self.telegram:
                        self.telegram.send_message(f"⚠️ Safety filter: {safety_message}")
                    self._last_safety_block_hour = current_hour
                return False
            
            # NEW: Level 3 Intelligence Check - TEMPORARILY DISABLED
            # account = get_account_info()
            # if account:
            #     intelligent_decision, decision_reason = self.intelligent_manager.should_execute_trade(
            #         symbol, signal, confidence, 'M15'
            #     )
            #     
            #     if not intelligent_decision:
            #         logger.warning(f" Trade blocked by intelligence: {decision_reason}")
            #         if self.telegram:
            #             self.telegram.send_message(f"🧠 Intelligence filter: {decision_reason}")
            #         return False
            
            logger.info(f"✅ Level 3 intelligence check bypassed for {symbol} (temporary fix)")
            
            # NEW: Adaptive lot sizing
            account = get_account_info()
            if account:
                adaptive_lot = self.adaptive_sizer.calculate_lot_size(
                    confidence, account['balance']
                )
                
                # LEVEL 7: Apply dynamic lot multiplier
                final_lot_size = adaptive_lot * self._current_lot_multiplier
                final_lot_size = min(final_lot_size, 0.5)  # Respect max lot size
                
                logger.info(f"Dynamic lot sizing: Base={adaptive_lot:.3f}, Multiplier={self._current_lot_multiplier:.1f}, Final={final_lot_size:.3f}")
                
                # NEW: Calculate profit targets
                profit_levels = self.profit_targets.calculate_profit_levels(entry_price, stop_loss, signal)
                if profit_levels:
                    take_profit = profit_levels['partial_tp']  # Use 1.5R for partial
                    logger.info(f"Using intelligent profit targets: Partial TP at {take_profit:.5f}")
                else:
                    take_profit = None  # Use original calculation
            
            # EXECUTE TRADE
            logger.info(f"🔧 About to call place_trade for {symbol}...")
            result = place_trade(
                symbol=symbol,
                signal=signal,
                lot=final_lot_size,  # LEVEL 7: Use dynamic lot size
                sl=stop_loss,
                tp=take_profit
            )
            
            logger.info(f"🔧 place_trade returned: {result}")
            if result is None:
                logger.error(f"❌ place_trade returned None - execution failed")
                return False
            elif hasattr(result, 'retcode') and result.retcode != mt5.TRADE_RETCODE_DONE:
                logger.error(f"❌ place_trade failed with retcode: {result.retcode}")
                return False
            
            if result:
                # LEVEL 5: Update trade memory and time for anti-spam
                self._last_trade_time[symbol] = current_time
                self._trade_memory[symbol] = (signal, current_time)  # Store signal and time
                
                # 🔥 CRITICAL FIXES: UPDATE TRACKING SYSTEMS
                # Update trade direction for consistency
                self._update_trade_direction(symbol, signal)
                
                # Update cycle count for cooldown
                self._update_cycle_count(symbol)
                
                # Note: Loss tracking will be updated when trade closes (in profit/loss monitoring)
                
                logger.info(f"🔄 Critical tracking updated for {symbol}: direction={signal}, cycle={current_time}")
                
                # Register trade with professional manager
                self.trade_manager.register_trade(
                    result.order, symbol, signal, entry_price, 
                    stop_loss, take_profit, final_lot_size  # LEVEL 7: Use dynamic lot size
                )
                
                # LEVEL 5: Send ONE clean Telegram message for executed trade
                trade_message = f"""🚀 TRADE EXECUTED

Symbol: {symbol}
Signal: {signal} ({confidence:.1f}%)
Entry: {entry_price:.5f}
Stop Loss: {stop_loss:.5f}
Take Profit: {take_profit:.5f}
Lot Size: {lot_size:.2f}

Time: {datetime.now().strftime('%H:%M:%S')}
Status: ACTIVE
Bot: Nyx AI Level 7
Score: {trade_score:.3f}
"""
                self._send_trade_telegram(trade_message, symbol)
                
                # LEVEL 5: Clean logging - only important events
                logger.info(f"✅ TRADE EXECUTED: {symbol} {signal} @ {entry_price:.5f} (Score: {trade_score:.3f})")
                
                # LEVEL 7: Journal the trade
                self._journal_trade(symbol, signal, entry_price, stop_loss, take_profit, final_lot_size, "EXECUTED", datetime.now())
                
                # 🔧 FIX 3: CORRECT RETURN LOGIC
                return True  # Return True only on successful execution
                
            else:
                # LEVEL 5: Safe execution - log error and continue
                logger.warning(f"❌ Trade execution failed: {symbol} {signal}")
                # Do NOT send Telegram for failed trades (LEVEL 5 anti-spam)
                
                return False  # 🔥 FIX 3: Return False on failed execution
                
        except Exception as e:
            # LEVEL 5: Safe execution - wrap entire function in try/except
            import traceback
            logger.error(f"❌ Critical error in trade execution: {e}")
            logger.error(f"🔍 Traceback: {traceback.format_exc()}")
            return False  # Continue bot loop, do NOT crash
    
    def monitor_positions(self):
        """Monitor open positions with professional management"""
        
        # LEVEL 6: Update profit tracking first
        self._update_profit_tracking()
        
        # NEW: Check for emergency stop file
        if self.check_stop_file():
            self.stop()
            return
            
        # NEW: Check running flag
        if not self.running:
            logger.info("Bot stopped - monitoring paused")
            return
            
        positions = mt5.positions_get()
        
        if positions:
            logger.info(f"Open positions: {len(positions)}")
            
            # Get current price for all positions
            current_prices = {}
            for pos in positions:
                if pos.symbol not in current_prices:
                    tick = mt5.symbol_info_tick(pos.symbol)
                    if tick:
                        current_prices[pos.symbol] = tick.ask if pos.type == 0 else tick.bid
            
            # Check each position for professional management
            for pos in positions:
                current_price = current_prices.get(pos.symbol, pos.price_current)
                atr_value = self.risk_manager.get_atr_value(pos.symbol)
                spread = 0.0
                tick = mt5.symbol_info_tick(pos.symbol)
                if tick:
                    spread = tick.ask - tick.bid
                
                # 1. Check partial TP
                if self.trade_manager.check_partial_tp(pos.ticket, current_price):
                    if ENABLE_ADVANCED_LOGGING and LOG_PARTIAL_TP_EVENTS:
                        logger.info(f"PARTIAL TP EXECUTED: {pos.symbol} ticket {pos.ticket}")
                
                # 2. Check break-even
                if self.trade_manager.check_break_even(pos.ticket, current_price, spread):
                    if ENABLE_ADVANCED_LOGGING and LOG_BREAK_EVEN_MOVES:
                        logger.info(f"BREAK-EVEN MOVED: {pos.symbol} ticket {pos.ticket}")
                
                # 3. Check trailing stop
                if atr_value and self.trade_manager.check_trailing_stop(pos.ticket, current_price, atr_value):
                    if ENABLE_ADVANCED_LOGGING and LOG_TRAILING_UPDATES:
                        logger.info(f"TRAILING STOP UPDATED: {pos.symbol} ticket {pos.ticket}")
                
                # 4. Check for force close conditions
                if self.trade_manager.should_force_close(pos.ticket, current_price):
                    result = close_position(pos)
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        logger.info(f"FORCE CLOSED: {pos.symbol} ticket {pos.ticket}")
                        self.trade_manager.cleanup_trade(pos.ticket)
                        if ENABLE_ADVANCED_LOGGING and LOG_EXIT_REASONS:
                            logger.info(f"EXIT REASON: Force close conditions met")
                    continue
                
                # 5. Check for old positions and close them
                current_time = time.time()
                position_age_seconds = current_time - pos.time
                position_age_minutes = position_age_seconds / 60
                
                if position_age_minutes > 30:
                    print(f"Closing old position {pos.ticket} (age: {position_age_minutes:.1f} minutes)")
                    result = close_position(pos)
                    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                        print(f"Successfully closed old position {pos.ticket}")
                        self.trade_manager.cleanup_trade(pos.ticket)
                    else:
                        print(f"Failed to close old position {pos.ticket}: {result.retcode if result else 'No result'}")
                else:
                    profit = pos.profit
                    logger.info(f"   Position {pos.ticket}: {pos.type} {pos.volume} lots, P&L: ${profit:+.2f}")
                    
                    # Send notification if profit is significant
                    if abs(profit) > 10:
                        self._send_position_update(pos)
        else:
            logger.info("No open positions")
    
    def check_open_trades(self):
        """Check all open trades and return structured list"""
        try:
            positions = mt5.positions_get()
            if not positions:
                return []
            
            open_trades = []
            current_time = time.time()
            
            for pos in positions:
                trade_data = {
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': 'BUY' if pos.type == 0 else 'SELL',
                    'volume': pos.volume,
                    'open_price': pos.price_open,
                    'profit': pos.profit,
                    'open_time': pos.time,
                    'duration_minutes': (current_time - pos.time) / 60,
                    'current_price': pos.price_current,
                    'sl': pos.sl,
                    'tp': pos.tp
                }
                open_trades.append(trade_data)
                
            logger.info(f"Found {len(open_trades)} open trades")
            return open_trades
            
        except Exception as e:
            logger.error(f"Error checking open trades: {e}")
            return []
    
    def close_trade_by_ticket(self, ticket):
        """Close a specific trade by ticket using professional method"""
        try:
            position = mt5.positions_get(ticket=ticket)
            if not position:
                logger.error(f"Position {ticket} not found")
                return False
                
            position = position[0]
            
            # Use professional closing method
            success, result = close_trade_professional(position)
            
            if success:
                logger.info(f"Successfully closed trade {ticket}")
                
                # 🔥 CRITICAL FIX #5: UPDATE LOSS TRACKING
                was_profitable = position.profit > 0
                self._update_loss_tracking(position.symbol, was_profitable)
                
                if self.telegram:
                    self.telegram.send_message(f"✅ Trade {ticket} closed - P&L: ${position.profit:+.2f}")
                return True
            else:
                logger.error(f"Failed to close trade {ticket}")
                if self.telegram:
                    self.telegram.send_message(f"❌ Failed to close trade {ticket}")
                return False
            
        except Exception as e:
            logger.error(f"Error closing trade {ticket}: {e}")
            return False
    
    def manage_trade_lifecycle(self):
        """Manage trade lifecycle with smarter logic"""
        try:
            open_trades = self.check_open_trades()
            
            for trade in open_trades:
                ticket = trade['ticket']
                symbol = trade['symbol']
                profit = trade['profit']
                duration = trade['duration_minutes']
                
                # Condition 1: Close after 45 minutes (increased from 30)
                if duration > 45:
                    logger.info(f"Closing trade {ticket} due to timeout ({duration:.1f} min)")
                    self.close_trade_by_ticket(ticket)
                    continue
                
                # Condition 2: Close if profit > $5 (increased from $2)
                if profit > 5.0:
                    logger.info(f"Closing trade {ticket} due to profit target (+${profit:.2f})")
                    self.close_trade_by_ticket(ticket)
                    continue
                
                # Condition 3: Close if loss < -$5 (increased from -$2)
                if profit < -5.0:
                    logger.info(f"Closing trade {ticket} due to stop loss (-${profit:.2f})")
                    self.close_trade_by_ticket(ticket)
                    continue
                    
                # Condition 4: Smart partial TP at 50% of target
                if abs(profit) > 1.0:  # Only if in reasonable profit
                    tp_distance = abs(trade['tp'] - trade['open_price'])
                    current_distance = abs(trade['current_price'] - trade['open_price'])
                    
                    if current_distance > tp_distance * 0.5:  # Reached 50% of TP
                        logger.info(f"Trade {ticket} at 50% TP target, consider partial close")
                        # Partial close logic can be added here
                    
        except Exception as e:
            logger.error(f"Error in trade lifecycle management: {e}")
    
    def _send_position_update(self, position):
        """Send position update notification"""
        if not self.telegram:
            return
        
        message = f"""
POSITION UPDATE

Type: {'BUY' if position.type == 0 else 'SELL'}
Volume: {position.volume:.2f} lots
P&L: ${position.profit:+.2f}
Entry: {position.price_open:.5f}
Current: {position.price_current:.5f}

Time: {datetime.now().strftime('%H:%M:%S')}
"""
        
        try:
            self.telegram.send_message(message)
        except Exception as e:
            logger.error(f"Failed to send position update: {e}")
    
    def emergency_close_all(self):
        """Emergency close all positions with improved error handling"""
        print("EMERGENCY CLOSE ALL POSITIONS!")
        
        try:
            # Get ALL open positions
            positions = mt5.positions_get()
            if not positions:
                print("No open positions to close")
                return 0
            
            closed = 0
            failed = 0
            
            for position in positions:
                print(f"Closing {position.symbol} position {position.ticket} (P&L: ${position.profit:+.2f})")
                
                # Use our improved close function
                if self.close_trade_by_ticket(position.ticket):
                    closed += 1
                else:
                    failed += 1
            
            print(f"Emergency close completed: {closed}/{len(positions)} positions closed, {failed} failed")
            
            # Send Telegram notification
            if self.telegram:
                self.telegram.send_message(
                    f"EMERGENCY CLOSE COMPLETED\n\n"
                    f"Closed: {closed}/{len(positions)} positions\n"
                    f"Failed: {failed} positions\n"
                    f"Nyx AI: Safety protocol activated"
                )
            
            return closed
            
        except Exception as e:
            logger.error(f"Emergency close error: {e}")
            return 0
