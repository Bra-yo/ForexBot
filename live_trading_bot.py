"""
LIVE TRADING BOT
Integrates our professional backtested system with real MT5 execution
"""

import logging
import time
from datetime import datetime
from mt5_data import connect_mt5, get_data, shutdown_mt5
from auto_trading_manager import AutoTradingManager
from live_trading_executor import LiveTradingExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LiveTradingBot:
    """Live trading bot with professional risk management"""
    
    def __init__(self, telegram_token=None, telegram_chat_id=None):
        self.telegram_token = telegram_token
        self.telegram_chat_id = telegram_chat_id
        
        # Initialize components
        self.trading_manager = None
        self.live_executor = None
        
        # Trading settings
        self.symbol = "EURUSD"
        self.timeframe = "M15"
        self.is_running = False
        
    def initialize(self):
        """Initialize the live trading bot"""
        try:
            logger.info("🚀 Initializing Live Trading Bot...")
            
            # Connect to MT5
            if not connect_mt5():
                logger.error("❌ Failed to connect to MT5")
                return False
            
            # Initialize trading manager (backtested system)
            self.trading_manager = AutoTradingManager(None, None)
            
            # Initialize live executor
            self.live_executor = LiveTradingExecutor(
                telegram_token=self.telegram_token,
                telegram_chat_id=self.telegram_chat_id
            )
            
            logger.info("✅ Live Trading Bot initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            return False
    
    def analyze_market(self):
        """Analyze current market conditions"""
        try:
            # Get real market data
            df = get_data(self.symbol, bars=200)  # Recent data for analysis
            
            # Prepare ML data
            df = self.trading_manager.prepare_ml_data(df)
            
            # Train/update model if needed
            if not hasattr(self.trading_manager, 'ml_model') or self.trading_manager.ml_model is None:
                logger.info("🧠 Training ML model...")
                self.trading_manager.train_model(df)
            
            # Get latest data for prediction
            latest_data = df.iloc[-1].to_dict()
            
            # Make prediction
            signal, confidence = self.trading_manager.predict_signal(latest_data)
            
            if signal is None:
                logger.info("📊 No signal generated")
                return None
            
            # Detect trend
            trend = self.trading_manager.detect_trend(df, len(df) - 1)
            
            # Calculate ATR
            atr = self.trading_manager.calculate_atr(df)
            current_atr = atr.iloc[-1]
            
            # Calculate dynamic SL/TP
            entry_price = latest_data['close']
            stop_loss, take_profit = self.trading_manager.calculate_dynamic_sl_tp(
                entry_price, current_atr, signal, trend=trend
            )
            
            # Calculate position size
            sl_pips = abs(entry_price - stop_loss) * 10000
            account_info = self.trading_manager.mt5_connector.get_account_info() if self.trading_manager.mt5_connector else None
            
            if account_info:
                balance = account_info.get('balance', 1000)
            else:
                balance = 1000  # Default
            
            lot_size = self.trading_manager.calculate_lot_size(balance, 1.0, sl_pips)
            
            # Calculate strength score
            current_momentum = latest_data.get('momentum', 0)
            atr_mean = atr.mean()
            strength_score = self.trading_manager.calculate_trade_strength_score(
                signal, confidence * 100, trend, current_atr, current_momentum, atr_mean
            )
            
            # Apply filters
            minimum_score = 3 if trend == "ranging" else 4
            valid_trade = strength_score >= minimum_score
            
            # Bear market filter
            if trend == "bearish" and confidence * 100 < 98:
                valid_trade = False
            
            analysis_result = {
                'signal': signal,
                'confidence': confidence * 100,
                'trend': trend,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'lot_size': lot_size,
                'strength_score': strength_score,
                'valid_trade': valid_trade,
                'reason': f"Score: {strength_score}/{minimum_score}, Trend: {trend}"
            }
            
            logger.info(f"📊 Market Analysis:")
            logger.info(f"   Signal: {signal} ({confidence:.1%})")
            logger.info(f"   Trend: {trend}")
            logger.info(f"   Strength Score: {strength_score}")
            logger.info(f"   Valid Trade: {'✅' if valid_trade else '❌'}")
            logger.info(f"   Entry: {entry_price:.5f}")
            logger.info(f"   SL: {stop_loss:.5f}")
            logger.info(f"   TP: {take_profit:.5f}")
            logger.info(f"   Lot: {lot_size:.2f}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"❌ Market analysis failed: {e}")
            return None
    
    def execute_trade_if_valid(self, analysis):
        """Execute trade if analysis is valid"""
        if not analysis or not analysis.get('valid_trade', False):
            logger.info(f"🚫 Trade not valid: {analysis.get('reason', 'Unknown')}")
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
                symbol=self.symbol
            )
            
            if success:
                logger.info("✅ Live trade executed successfully!")
            else:
                logger.error("❌ Live trade execution failed!")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Trade execution error: {e}")
            return False
    
    def run_trading_cycle(self):
        """Run one complete trading cycle"""
        try:
            logger.info("🔄 Starting trading cycle...")
            
            # Analyze market
            analysis = self.analyze_market()
            
            # Execute trade if valid
            if analysis:
                self.execute_trade_if_valid(analysis)
            
            # Check open positions
            self.live_executor.check_open_trades()
            
            logger.info("✅ Trading cycle completed")
            
        except Exception as e:
            logger.error(f"❌ Trading cycle error: {e}")
    
    def start_live_trading(self, cycle_seconds=300):  # 5 minutes default
        """Start live trading with continuous cycles"""
        self.is_running = True
        
        logger.info(f"🚀 Starting Live Trading!")
        logger.info(f"📊 Symbol: {self.symbol}")
        logger.info(f"⏰ Cycle: Every {cycle_seconds} seconds")
        
        if self.telegram_token:
            self.live_executor.telegram.send_message(
                f"🚀 **LIVE TRADING STARTED**\n\n"
                f"📊 Symbol: {self.symbol}\n"
                f"⏰ Cycle: Every {cycle_seconds} seconds\n"
                f"💡 Bot is now LIVE and trading!\n"
                f"⏰ Started: {datetime.now().strftime('%H:%M:%S')}"
            )
        
        try:
            while self.is_running:
                cycle_start = time.time()
                
                # Run trading cycle
                self.run_trading_cycle()
                
                # Wait for next cycle
                elapsed = time.time() - cycle_start
                wait_time = max(0, cycle_seconds - elapsed)
                
                if wait_time > 0:
                    logger.info(f"⏰ Waiting {wait_time:.0f} seconds for next cycle...")
                    time.sleep(wait_time)
                
        except KeyboardInterrupt:
            logger.info("🛑 Trading stopped by user")
        except Exception as e:
            logger.error(f"❌ Trading loop error: {e}")
        finally:
            self.stop_live_trading()
    
    def stop_live_trading(self):
        """Stop live trading"""
        self.is_running = False
        
        logger.info("🛑 Stopping Live Trading...")
        
        if self.telegram_token:
            self.live_executor.telegram.send_message(
                f"🛑 **LIVE TRADING STOPPED**\n\n"
                f"⏰ Stopped: {datetime.now().strftime('%H:%M:%S')}\n"
                f"💡 Bot is now offline"
            )
        
        # Emergency close all positions
        self.live_executor.emergency_close_all()
        
        # Shutdown MT5
        shutdown_mt5()
        
        logger.info("✅ Live Trading stopped")

def main():
    """Main function to run live trading"""
    
    # Configuration
    TELEGRAM_TOKEN = None  # Add your token here
    TELEGRAM_CHAT_ID = None  # Add your chat ID here
    
    # Create and start bot
    bot = LiveTradingBot(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
    
    if bot.initialize():
        try:
            # Start live trading (5-minute cycles)
            bot.start_live_trading(cycle_seconds=300)
        except KeyboardInterrupt:
            print("\n🛑 Stopping trading...")
            bot.stop_live_trading()
    else:
        print("❌ Failed to initialize bot")

if __name__ == "__main__":
    main()
