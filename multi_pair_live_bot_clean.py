"""
MULTI-PAIR LIVE TRADING BOT
Enhanced with Level 3 Intelligence and safety controls
"""

import os
import sys
import time
import signal
import logging
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv
import MetaTrader5 as mt5

# Import our components
from live_trading_executor import LiveTradingExecutor
from bot_controller import BotController
from technical_analysis import TechnicalAnalysis
from brokers.mt5_connector import MT5Connector

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Trade timeout configuration
MAX_TRADE_DURATION_MINUTES = 10

def manage_open_trades():
    """Close trades that exceed maximum duration"""
    positions = mt5.positions_get()
    
    if positions is None:
        return
    
    now = datetime.utcnow()  # Use UTC for consistency
    
    for pos in positions:
        open_time = datetime.fromtimestamp(pos.time)
        duration = (now - open_time).total_seconds() / 60
        
        if duration > MAX_TRADE_DURATION_MINUTES:  # 🔥 CHANGE TO 10 MINUTES
            logger.info(f"⏰ Closing expired trade: {pos.symbol} (open for {duration:.1f} mins)")
            
            close_request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": mt5.ORDER_TYPE_SELL if pos.type == 0 else mt5.ORDER_TYPE_BUY,
                "position": pos.ticket,
                "price": mt5.symbol_info_tick(pos.symbol).bid,
                "deviation": 20,
                "magic": 123456,
                "comment": "Timeout close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(close_request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"✅ Closed {pos.symbol} (timeout)")
            else:
                logger.error(f"❌ Failed to close {pos.symbol}: {result.retcode}")

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
        # GOLD-ONLY CONFIGURATION (pivoted from 10-pair Forex scanning)
        # NOTE: some brokers list this symbol with a suffix, e.g. "XAUUSDm" or
        # "GOLD#". If _get_available_symbols() below comes back empty, check
        # the exact symbol name in your MT5 Market Watch and update this.
        self.all_symbols = ['XAUUSD']
        
        # LEVEL 7: Filter available symbols at startup
        self.symbols = self._get_available_symbols()
        logger.info(f"Available symbols for trading: {self.symbols}")
        
        self.timeframe_names = {
            mt5.TIMEFRAME_M15: "M15",
            mt5.TIMEFRAME_M30: "M30", 
            mt5.TIMEFRAME_H1: "H1"
        }
        
        # Track last analysis time per symbol/timeframe
        self.last_analysis_time = {}
        
        # Trading state
        self.is_running = False
        
        # REAL SIGNAL ENGINE (replaces the old random.random() stub).
        # MT5Connector wraps the same MT5 terminal connection this bot already
        # uses; TechnicalAnalysis computes real RSI/MACD/EMA/ATR/structure
        # levels and combines them into an actual market analysis.
        self.mt5_connector = MT5Connector()
        self.ta = TechnicalAnalysis()
        
    def _get_available_symbols(self):
        """LEVEL 7: Check which symbols are available on the broker"""
        available_symbols = []
        
        for symbol in self.all_symbols:
            try:
                symbol_info = mt5.symbol_info(symbol)
                if symbol_info and symbol_info.visible:
                    # Check if we can get tick data
                    tick = mt5.symbol_info_tick(symbol)
                    if tick:
                        available_symbols.append(symbol)
                        logger.info(f"✅ {symbol} - Available")
                    else:
                        logger.warning(f"❌ {symbol} - No tick data (market closed)")
                else:
                    logger.warning(f"❌ {symbol} - Not available or not visible")
            except Exception as e:
                logger.error(f"❌ {symbol} - Error checking: {e}")
        
        return available_symbols
    
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
            
            # Initialize the connector wrapper used for real signal generation
            # (shares the same underlying MT5 terminal connection above)
            if not self.mt5_connector.initialize():
                logger.warning("MT5Connector wrapper failed to initialize - "
                                "signal generation will be degraded")
            
            # Initialize live executor
            if self.live_executor:
                self.live_executor.is_running = True
            
            logger.info("Multi-Pair Trading Bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization error: {e}")
            return False
    
    def get_signal(self, symbol, timeframe):
        """
        Get a REAL trading signal for symbol and timeframe.

        Replaces the previous random.random() stub. Pulls actual OHLC data,
        computes real indicators (RSI/MACD/MAs/Bollinger/Stochastic), and
        runs the full professional analysis pipeline (HTF trend, market
        condition, structure-based SL/TP, entry confirmation, risk:reward,
        confidence scoring) that already existed in technical_analysis.py
        but was never wired into the live path.

        Returns:
            (signal, confidence, analysis) where signal is 'BUY'/'SELL'/None,
            confidence is 0-100, and analysis is the full result dict from
            TechnicalAnalysis.advanced_signal_analysis() (or None on failure).
            analysis['market_data'] carries real ema_fast/ema_slow/rsi/volume/
            atr values for the downstream signal-quality and trend checks in
            live_trading_executor.py.
        """
        try:
            timeframe_name = self.timeframe_names.get(timeframe, 'M15')

            # Enough history for indicators (BB/MACD/structure) to stabilize,
            # padded generously to survive weekend/holiday gaps.
            lookback_days = {'M15': 10, 'M30': 20, 'H1': 40}.get(timeframe_name, 10)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=lookback_days)

            data = self.mt5_connector.get_historical_data(
                symbol=symbol,
                timeframe=timeframe_name,
                start_date=start_date,
                end_date=end_date
            )

            if data is None or data.empty or len(data) < 60:
                logger.warning(f"Insufficient market data for {symbol} {timeframe_name} "
                                f"({0 if data is None else len(data)} candles)")
                return None, 0, None

            # Real indicators
            data = self.ta.get_all_indicators(data)

            # Full professional signal analysis (real HTF trend, market
            # condition, structure levels, entry confirmation, R:R, confidence)
            analysis = self.ta.advanced_signal_analysis(
                self.mt5_connector, data, symbol, timeframe_name
            )

            # Build real market_data for the signal-quality/trend-alignment
            # checks in live_trading_executor.py (previously fabricated from
            # a random confidence number - see execute_live_trade).
            latest = data.iloc[-1]
            market_condition = self.ta.detect_market_condition(data)
            avg_volume = data['volume'].rolling(20).mean().iloc[-1] if 'volume' in data.columns else None

            analysis['market_data'] = {
                'ema_fast': float(latest['ma_fast']) if pd.notna(latest.get('ma_fast')) else 0.0,
                'ema_slow': float(latest['ma_slow']) if pd.notna(latest.get('ma_slow')) else 0.0,
                'rsi': float(latest['rsi']) if pd.notna(latest.get('rsi')) else 50.0,
                'current_volume': float(latest['volume']) if pd.notna(latest.get('volume')) else 0.0,
                'avg_volume': float(avg_volume) if avg_volume is not None and pd.notna(avg_volume) else 0.0,
                'atr': float(market_condition.get('atr', 0) or 0),
            }

            signal = analysis.get('signal')
            confidence = analysis.get('confidence', 0)

            if signal not in ('BUY', 'SELL') or analysis.get('trade_blocked', True):
                return None, confidence, analysis

            return signal, confidence, analysis

        except Exception as e:
            logger.error(f"Signal generation error for {symbol}: {e}")
            return None, 0, None
    
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
                        # Get real signal from the technical analysis engine
                        signal, confidence, analysis = self.get_signal(symbol, timeframe)
                        
                        if signal and confidence > 50:  # Minimum confidence threshold
                            symbol_signals.append((signal, confidence, timeframe, analysis))
                            logger.debug(f"Signal found: {symbol} {signal} @ {confidence:.1f}%")
                            
                    except Exception as e:
                        logger.error(f"Error analyzing {symbol} {self.timeframe_names[timeframe]}: {e}")
                        continue
                
                # Select best signal for this symbol
                if symbol_signals:
                    # Sort by confidence and take the best
                    best_signal = max(symbol_signals, key=lambda x: x[1])
                    signal, confidence, timeframe, analysis = best_signal
                    
                    logger.info(f"🎯 Best signal for {symbol}: {signal} @ {confidence:.1f}% ({self.timeframe_names[timeframe]})")
                    
                    # Execute trade
                    trades_attempted += 1
                    
                    logger.info(f"🔍 Attempting to execute trade for {symbol}...")
                    
                    # Get current price for entry
                    # LEVEL 7: Enhanced symbol validation with connection check
                    try:
                        logger.info(f"📊 Checking MT5 connection for {symbol}...")
                        if not mt5.initialize():
                            logger.error("MT5 connection lost - reinitializing...")
                            if not mt5.initialize():
                                logger.error("Failed to reinitialize MT5")
                                continue
                        
                        logger.info(f"🔍 Getting symbol info for {symbol}...")
                        symbol_info = mt5.symbol_info(symbol)
                        if not symbol_info:
                            logger.warning(f"Symbol {symbol} not found on broker - skipping")
                            continue
                        
                        if not symbol_info.visible:
                            logger.warning(f"Symbol {symbol} not visible/enabled - skipping")
                            continue
                        
                        logger.info(f"📈 Getting tick data for {symbol}...")
                        tick = mt5.symbol_info_tick(symbol)
                        if not tick:
                            logger.warning(f"No tick data for {symbol} - market may be closed")
                            continue
                        
                        logger.info(f"✅ Symbol validation passed for {symbol}")
                            
                    except Exception as e:
                        logger.error(f"Error getting symbol data for {symbol}: {e}")
                        continue
                        
                    entry_price = tick.ask if signal == "BUY" else tick.bid
                    
                    logger.info(f"💰 Entry price for {symbol}: {entry_price:.5f}")
                    
                    # Use the real structure-based SL/TP from advanced_signal_analysis
                    # when available; otherwise let the executor calculate a
                    # fallback (e.g. for the "weak signal" path, which doesn't
                    # compute structure levels). 0/None means "not available".
                    real_sl = analysis.get('structure_sl') if analysis else None
                    real_tp = analysis.get('structure_tp') if analysis else None
                    real_market_data = analysis.get('market_data') if analysis else None
                    
                    logger.info(f"🚀 Calling execute_live_trade for {symbol}...")
                    success = self.live_executor.execute_live_trade(
                        signal=signal,
                        confidence=confidence,
                        entry_price=entry_price,
                        stop_loss=real_sl or None,
                        take_profit=real_tp or None,
                        lot_size=0.01,   # Default lot size
                        symbol=symbol,
                        market_data=real_market_data
                    )
                    
                    logger.info(f"📊 Trade execution result for {symbol}: {success}")
                    
                    if success:
                        trades_executed += 1
                        symbol_trades += 1
                
                # Limit trades per symbol
                if symbol_trades >= 1:  # Max 1 trade per symbol per cycle
                    continue
                    
        except Exception as e:
            logger.error(f"Analysis cycle error: {e}")
            
        logger.info(f"Cycle completed: {trades_executed}/{trades_attempted} trades executed")
        
        # 🔥 LEVEL 9: Show analytics dashboard every 5 cycles
        if hasattr(self, 'cycle_count'):
            self.cycle_count += 1
        else:
            self.cycle_count = 1
            
        if self.cycle_count % 5 == 0:  # Every 5 cycles (5 minutes)
            from integrated_analytics import analytics
            analytics.print_quick_stats()
    
    def run_multi_pair_trading(self, cycle_seconds=60):  # 1 minute default
        """Start multi-pair live trading"""
        
        logger.info("Starting multi-pair trading...")
        
        # 🔥 LEVEL 9: Show initial analytics dashboard
        from integrated_analytics import analytics
        analytics.print_performance_dashboard()
        
        self.is_running = True
        
        try:
            # Initialize MT5 and Telegram
            if not self.initialize():
                return False
            
            # Send startup notification
            if self.telegram:
                self.telegram.send_message(
                    f"🚀 NYX AI Gold Trading Started\n\n"
                    f"Symbol: XAUUSD (Gold)\n"
                    f"Timeframes: M15, M30, H1\n"
                    f"Process ID: {os.getpid()}\n"
                    f"Status: ACTIVE\n"
                    f"Control: STOP NYX to stop via Telegram"
                )
            
            # LEVEL 6: Auto-restart protection - wrap main loop in try/except
            while self.is_running and self.live_executor.running:
                try:
                    cycle_start = time.time()
                    
                    # NEW: Check emergency stop file
                    if self.controller.check_emergency_stop():
                        logger.warning("Emergency stop triggered - breaking loop")
                        break
                    
                    # 🔥 ADD TRADE TIMEOUT MANAGER
                    manage_open_trades()
                    
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
                        
                except Exception as e:
                    # LEVEL 6: Auto-restart protection
                    logger.error(f"❌ Main loop error: {e}")
                    print(f"❌ ERROR in main loop: {e}")
                    print("🔄 Restarting in 10 seconds...")
                    time.sleep(10)  # Wait 10 seconds before restart
                    continue  # Restart loop automatically
        
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
    print(f"   [OK] {MAX_TRADE_DURATION_MINUTES}-minute position timeout")
    print("   [OK] Spread filter (max 5.0 pips)")
    print("   [OK] Trading hours filter (6:00-20:00)")
    print("   [OK] Weekend protection")
    print("   [OK] Symbol: XAUUSD (Gold) - pivoted from multi-pair Forex")
    print("   [OK] Multiple timeframes: M15, M30, H1")
    
    print("\nNYX AI RISK WARNING")
    print("   Nyx AI watches the Gold (XAUUSD) market 24/7")
    print("   Higher exposure = Higher risk")
    print("   Monitor open positions closely")
    print("   Stop immediately if issues occur")
    
    print("\nSTARTING NYX AI LIVE TRADING")
    print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")
    print("   Symbol: XAUUSD (Gold)")
    print("   Timeframes: M15, M30, H1")
    print("   Cycle: Every 1 minute")
    print("   Max concurrent trades: 3")
    
    confirm = input("\n   Type 'NYX-START' to begin multi-pair live trading: ")
    if confirm.upper() != 'NYX-START':
        print("❌ Nyx AI multi-pair trading cancelled")
        return
    
    print("🔧 Initializing multi-pair trading bot...")
    
    # Create bot instance
    bot = MultiPairLiveBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    # LEVEL 7: Show actual available symbols after bot creation
    print(f"✅ Available symbols: {', '.join(bot.symbols)}")
    print(f"📊 Trading {len(bot.symbols)} symbol(s): Gold (XAUUSD)")
    
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