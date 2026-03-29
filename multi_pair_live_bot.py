"""
MULTI-PAIR LIVE TRADING BOT
Trades across multiple currency pairs and timeframes
"""

import os
import sys
import time
import logging
import signal
from datetime import datetime
from dotenv import load_dotenv

# NEW: Import bot controller
from bot_controller import BotController
import MetaTrader5 as mt5  # ENSURE MT5 IS IMPORTED AT TOP LEVEL
from concurrent.futures import ThreadPoolExecutor

from live_trading_executor import LiveTradingExecutor

# Configure logging with basic formatting to avoid Unicode issues
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MultiPairLiveBot:
    """Multi-pair, multi-timeframe live trading bot"""
    
    def __init__(self, telegram_token=None, telegram_chat_id=None):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        
        # Initialize components
        self.live_executor = LiveTradingExecutor(self.telegram_token, self.telegram_chat_id)
        
        # NEW: Initialize bot controller
        self.controller = BotController()
        
        # NEW: Set up signal handler for Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.stop()
        sys.exit(0)
        
        # Trading configuration
        
        # Multi-pair configuration
        self.timeframe_names = {
            mt5.TIMEFRAME_M15: "M15",
            mt5.TIMEFRAME_M30: "M30", 
            mt5.TIMEFRAME_H1: "H1"
        }
        
        # Track last analysis time per symbol/timeframe
        self.last_analysis = {}
        
    def initialize(self):
        """Initialize the multi-pair trading bot"""
        try:
            logger.info("Initializing Multi-Pair Live Trading Bot...")
            
            # Connect to MT5
            if not mt5.initialize():
                logger.error("Failed to connect to MT5")
                return False
            
            # Get account info
            account_info = mt5.account_info()
            if account_info:
                logger.info(f"Connected to account: {account_info.login}")
                logger.info(f"Balance: ${account_info.balance:,.2f}")
            
            # Initialize analysis tracking
            for symbol in self.symbols:
                for timeframe in self.timeframes:
                    self.last_analysis[(symbol, timeframe)] = 0
            
            logger.info("Multi-Pair Trading Bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def analyze_symbol_timeframe(self, symbol, timeframe):
        """Analyze a specific symbol and timeframe"""
        try:
            # Get current time
            current_time = time.time()
            last_time = self.last_analysis.get((symbol, timeframe), 0)
            
            # Check if enough time has passed (5 minutes for M15, 10 for M30, 15 for H1)
            if timeframe == mt5.TIMEFRAME_M15:
                interval = 300  # 5 minutes
            elif timeframe == mt5.TIMEFRAME_M30:
                interval = 600  # 10 minutes
            else:  # H1
                interval = 900  # 15 minutes
            
            if current_time - last_time < interval:
                return None  # Not time yet
            
            # Get market data
            rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, 200)
            if rates is None:
                logger.warning(f"Failed to get data for {symbol} {self.timeframe_names[timeframe]}")
                return None
            
            # Convert to DataFrame
            import pandas as pd
            df = pd.DataFrame(rates)
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Simple analysis logic (you can integrate your ML model here)
            latest_candle = df.iloc[-1]
            prev_candle = df.iloc[-2]
            
            # Basic trend detection
            ema_fast = df['close'].ewm(span=20).mean()
            ema_slow = df['close'].ewm(span=50).mean()
            
            current_ema_fast = ema_fast.iloc[-1]
            current_ema_slow = ema_slow.iloc[-1]
            
            # Determine signal
            if current_ema_fast > current_ema_slow:
                signal = "BUY"
                confidence = min(95, 60 + abs(current_ema_fast - current_ema_slow) * 10000)
            else:
                signal = "SELL"
                confidence = min(95, 60 + abs(current_ema_fast - current_ema_slow) * 10000)
            
            # Calculate ATR for SL/TP
            high_low = df['high'] - df['low']
            high_close = abs(df['high'] - df['close'].shift())
            low_close = abs(df['low'] - df['close'].shift())
            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(14).mean().iloc[-1]
            
            # Calculate SL/TP
            entry_price = latest_candle['close']
            if signal == "BUY":
                stop_loss = entry_price - (atr * 1.5)
                take_profit = entry_price + (atr * 2.5)
            else:
                stop_loss = entry_price + (atr * 1.5)
                take_profit = entry_price - (atr * 2.5)
            
            # Calculate lot size (simple fixed for now)
            lot_size = 0.01
            
            # Update last analysis time
            self.last_analysis[(symbol, timeframe)] = current_time
            
            analysis = {
                'symbol': symbol,
                'timeframe': self.timeframe_names[timeframe],
                'signal': signal,
                'confidence': confidence,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'lot_size': lot_size,
                'atr': atr,
                'valid_trade': confidence > 75  # Simple filter
            }
            
            logger.info(f"{symbol} {self.timeframe_names[timeframe]}: {signal} ({confidence:.1f}%)")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol} {self.timeframe_names[timeframe]}: {e}")
            return None
    
    def execute_trade_if_valid(self, analysis):
        """Execute trade if analysis is valid"""
        if not analysis or not analysis.get('valid_trade', False):
            return False
        
        try:
            # Execute live trade
            success = self.live_executor.execute_live_trade(
                signal=analysis['signal'],
                confidence=analysis['confidence'],
                entry_price=analysis['entry_price'],
                stop_loss=analysis['stop_loss'],
                take_profit=analysis['take_profit'],
                lot_size=analysis['lot_size'],
                symbol=analysis['symbol']
            )
            
            return success
            
        except Exception as e:
            logger.error(f"Trade execution error for {analysis['symbol']}: {e}")
            return False
    
    def run_analysis_cycle(self):
        """Run multi-pair analysis cycle"""
        trades_executed = 0
        trades_attempted = 0
        
        try:
            logger.info("Starting multi-pair analysis cycle...")
            
            # Check open positions
            self.live_executor.check_open_trades()
            
            # Analyze each symbol
            for symbol in self.symbols:
                symbol_trades = 0
                symbol_signals = []
                
                # Analyze each timeframe
                for timeframe in [mt5.TIMEFRAME_M15, mt5.TIMEFRAME_M30, mt5.TIMEFRAME_H1]:
                    try:
                        # Get signal from your signal generation system
                        signal, confidence = self.get_signal(symbol, timeframe)
                        
                        if signal and confidence > 50:  # Minimum confidence threshold
                            symbol_signals.append((signal, confidence, timeframe))
                            
                    except Exception as e:
                        logger.error(f"Error analyzing {symbol} {self.timeframe_names[timeframe]}: {e}")
                        continue
                
                # Select best signal for this symbol
                if symbol_signals:
                    # Sort by confidence and take the best
                    best_signal = max(symbol_signals, key=lambda x: x[1])
                    signal, confidence, timeframe = best_signal
                    
                    # Execute trade
                    trades_attempted += 1
                    success = self.live_executor.execute_live_trade(
                        signal=signal,
                        confidence=confidence,
                        entry_price=None,  # Will be calculated in executor
                        stop_loss=None,    # Will be calculated in executor
                        take_profit=None, # Will be calculated in executor
                        lot_size=0.01,   # Default lot size
                        symbol=symbol
                    )
                    
                    if success:
                        trades_executed += 1
                        symbol_trades += 1
                
                # Limit trades per symbol
                if symbol_trades >= 1:  # Max 1 trade per symbol per cycle
                    continue
                    
        except Exception as e:
            logger.error(f"Analysis cycle error: {e}")
            
        logger.info(f"Cycle completed: {trades_executed}/{trades_attempted} trades executed")
    
    def run_multi_pair_trading(self, cycle_seconds=60):  # 1 minute default
        """Start multi-pair live trading"""
        
        logger.info("Starting multi-pair trading...")
        self.is_running = True
        
    
    if self.live_executor:
        self.live_executor.stop()
        
    self.stop()
    sys.exit(0)

def stop(self):
    """Stop the bot and cleanup"""
    logger.info("Stopping multi-pair bot...")
    if self.live_executor:
        self.live_executor.stop()
    self.is_running = False
    
    logger.info("Multi-Pair Trading stopped")
    
    # NEW: Clean up control files
    self.controller.cleanup_lock_files()

def stop_multi_pair_trading(self):
    """Stop multi-pair trading"""
    self.is_running = False
    
    logger.info("Stopping Multi-Pair Trading...")
    self.live_executor.emergency_close_all()
    
    # Shutdown MT5
    mt5.shutdown()
    
    logger.info("Multi-Pair Trading stopped")
    
    # NEW: Clean up control files
    self.controller.cleanup_lock_files()

def main():
    """Main function to run multi-pair live trading"""
    
    # Load environment variables
    load_dotenv()
    
    # Configuration
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Create and start bot
    bot = MultiPairLiveBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    if bot.initialize():
        try:
            # Start multi-pair trading (1-minute cycles)
            bot.start_multi_pair_trading(cycle_seconds=60)
        except KeyboardInterrupt:
            print("Stopping trading...")
            bot.stop_multi_pair_trading()
    else:
        print("Failed to initialize bot")

if __name__ == "__main__":
    main()
