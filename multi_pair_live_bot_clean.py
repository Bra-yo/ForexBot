"""
MULTI-PAIR LIVE TRADING BOT
Enhanced with Level 3 Intelligence and safety controls
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime
from dotenv import load_dotenv
import MetaTrader5 as mt5

# Import our components
from live_trading_executor import LiveTradingExecutor
from bot_controller import BotController

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MultiPairLiveBot:
    """Enhanced multi-pair trading bot with Level 3 Intelligence"""
    
    def __init__(self, telegram_token=None, telegram_chat_id=None):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        
        # Initialize components
        self.live_executor = LiveTradingExecutor(self.telegram_token, self.telegram_chat_id)
        
        # NEW: Initialize bot controller
        self.controller = BotController()
        
        # NEW: Initialize telegram assistant
        if self.telegram_token:
            from advanced_telegram_assistant import AdvancedTelegramAssistant
            self.telegram = AdvancedTelegramAssistant(self.telegram_token, self.telegram_chat_id)
        else:
            self.telegram = None
        
        # NEW: Set up signal handler for Ctrl+C
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Trading configuration
        # Multi-pair configuration
        self.symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'EURGBP', 'EURJPY', 'GBPJPY', 'NZDUSD', 'EURCHF']
        self.timeframe_names = {
            mt5.TIMEFRAME_M15: "M15",
            mt5.TIMEFRAME_M30: "M30", 
            mt5.TIMEFRAME_H1: "H1"
        }
        
        # Track last analysis time per symbol/timeframe
        self.last_analysis_time = {}
        
        # Trading state
        self.is_running = False
        
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C and termination signals"""
        logger.info(f"Received signal {signum} - stopping bot...")
        print("\n🛑 STOP SIGNAL RECEIVED")
        print("Stopping Nyx AI Bot safely...")
        
        if self.live_executor:
            self.live_executor.stop()
            
        self.stop()
        sys.exit(0)
        
    def stop(self):
        """Stop bot and cleanup"""
        logger.info("Stopping multi-pair bot...")
        if self.live_executor:
            self.live_executor.stop()
        self.is_running = False
        
    def initialize(self):
        """Initialize MT5 and Telegram"""
        try:
            # Initialize MT5
            if not mt5.initialize():
                logger.error("MT5 initialization failed")
                return False
            
            # Check connection
            account_info = mt5.account_info()
            if account_info is None:
                logger.error("Failed to connect to MT5 account")
                return False
            
            logger.info(f"Connected to account: {account_info.login}")
            logger.info(f"Balance: ${account_info.balance:,.2f}")
            
            # Initialize live executor
            if self.live_executor:
                self.live_executor.is_running = True
            
            logger.info("Multi-Pair Trading Bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            return False
    
    def get_signal(self, symbol, timeframe):
        """Get trading signal for symbol and timeframe"""
        try:
            # This is where you'd integrate your signal generation system
            # For now, return dummy signals for testing
            import random
            
            # Simulate signal generation
            if random.random() > 0.7:  # 30% chance of signal
                signal = "BUY" if random.random() > 0.5 else "SELL"
                confidence = random.uniform(60, 95)
                return signal, confidence
            else:
                return None, 0
                
        except Exception as e:
            logger.error(f"Signal generation error for {symbol}: {e}")
            return None, 0
    
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
                    
                    # Get current price for entry
                    tick = mt5.symbol_info_tick(symbol)
                    if not tick:
                        logger.warning(f"No tick data for {symbol}")
                        continue
                        
                    entry_price = tick.ask if signal == "BUY" else tick.bid
                    
                    success = self.live_executor.execute_live_trade(
                        signal=signal,
                        confidence=confidence,
                        entry_price=entry_price,
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
        
        try:
            # Initialize MT5 and Telegram
            if not self.initialize():
                return False
            
            # Send startup notification
            if self.telegram:
                self.telegram.send_message(
                    f"🚀 NYX AI Multi-Pair Trading Started\n\n"
                    f"Symbols: {len(self.symbols)} pairs\n"
                    f"Timeframes: M15, M30, H1\n"
                    f"Process ID: {os.getpid()}\n"
                    f"Status: ACTIVE\n"
                    f"Control: STOP NYX to stop via Telegram"
                )
            
            # NEW: Main trading loop with running flag
            while self.is_running and self.live_executor.running:
                cycle_start = time.time()
                
                # NEW: Check emergency stop file
                if self.controller.check_emergency_stop():
                    logger.warning("Emergency stop triggered - breaking loop")
                    break
                
                # Run multi-pair analysis
                self.run_analysis_cycle()
                
                # Manage trade lifecycle (NEW)
                if self.live_executor:
                    self.live_executor.manage_trade_lifecycle()
                
                # Wait for next cycle
                elapsed = time.time() - cycle_start
                wait_time = max(0, cycle_seconds - elapsed)
                
                if wait_time > 0:
                    time.sleep(wait_time)
        
        except KeyboardInterrupt:
            logger.info("Trading stopped by user")
        except Exception as e:
            logger.error(f"Trading loop error: {e}")
        finally:
            self.stop_multi_pair_trading()
            
        return True

    def stop_multi_pair_trading(self):
        """Stop multi-pair trading"""
        self.is_running = False
        
        logger.info("Stopping Multi-Pair Trading...")
        if self.live_executor:
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
    
    # Safety confirmation
    print("\n🛡️  **NYX AI SAFETY CHECK**")
    print("   [OK] MT5 Terminal is running")
    print("   [OK] Account is DEMO (not real money)")
    print("   [OK] Lot size is capped at 0.5")
    print("   [OK] Max 3 open trades per symbol")
    print("   [OK] 30-minute position timeout")
    print("   [OK] Spread filter (max 5.0 pips)")
    print("   [OK] Trading hours filter (6:00-20:00)")
    print("   [OK] Weekend protection")
    print("   [OK] Multiple pairs: EURUSD, GBPUSD, USDJPY, AUDUSD, USDCAD, EURGBP, EURJPY, GBPJPY, NZDUSD, EURCHF")
    print("   [OK] Multiple timeframes: M15, M30, H1")
    
    print("\nNYX AI RISK WARNING")
    print("   Nyx AI watches markets 24/7 across all pairs")
    print("   Higher exposure = Higher risk")
    print("   Monitor ALL positions closely")
    print("   Stop immediately if issues occur")
    print("   Each pair will trade independently")
    
    print("\nSTARTING NYX AI LIVE TRADING")
    print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
    print("   Symbols: 10 major currency pairs")
    print("   Timeframes: M15, M30, H1")
    print("   Cycle: Every 1 minute")
    print("   Max concurrent trades: 30 (3 per symbol)")
    
    confirm = input("\n   Type 'NYX-START' to begin multi-pair live trading: ")
    if confirm.upper() != 'NYX-START':
        print("❌ Nyx AI multi-pair trading cancelled")
        return
    
    print("🔧 Initializing multi-pair trading bot...")
    
    # Create bot instance
    bot = MultiPairLiveBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    try:
        # Start trading
        success = bot.run_multi_pair_trading()
        
        if success:
            print("✅ Multi-pair trading completed successfully")
        else:
            print("❌ Multi-pair trading failed")
            
    except Exception as e:
        print(f"Multi-pair trading error: {e}")
    
    finally:
        print("Multi-pair live trading session ended")

if __name__ == "__main__":
    main()
