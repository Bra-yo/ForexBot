"""
Continuous Multi-Pair, Multi-Timeframe Scanner with Telegram Support
Runs independently from Streamlit UI
"""

import threading
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'brokers'))

from technical_analysis import TechnicalAnalysis
from mt5_connector import MT5Connector
from advanced_telegram_assistant import AdvancedTelegramAssistant
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler
from telegram import Update

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
TIMEFRAMES = ["M5", "M15", "M30", "H1"]
SCAN_INTERVAL = 30  # seconds between scans

class ContinuousScanner:
    """Continuous scanner for multiple symbols and timeframes"""
    
    def __init__(self):
        self.mt5_connector = MT5Connector()
        self.technical_analysis = TechnicalAnalysis()
        self.telegram_assistant = AdvancedTelegramAssistant()
        
        # Track last signals to avoid duplicates
        self.last_signals = {}
        for symbol in SYMBOLS:
            self.last_signals[symbol] = {}
            for timeframe in TIMEFRAMES:
                self.last_signals[symbol][timeframe] = None
        
        self.running = False
        
    def initialize_mt5(self):
        """Initialize MT5 connection"""
        try:
            if self.mt5_connector.connect():
                logger.info("✅ MT5 Connected successfully")
                return True
            else:
                logger.error("❌ Failed to connect to MT5")
                return False
        except Exception as e:
            logger.error(f"❌ MT5 connection error: {e}")
            return False
    
    def analyze_symbol_timeframe(self, symbol, timeframe):
        """Analyze single symbol and timeframe"""
        try:
            logger.info(f"📊 Scanning {symbol} {timeframe}...")
            
            # Get historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            historical_data = self.mt5_connector.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if historical_data is None or 'error' in historical_data:
                logger.warning(f"⚠️ No data for {symbol} {timeframe}")
                return None
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(historical_data)
            
            # Perform advanced signal analysis
            signal_analysis = self.technical_analysis.advanced_signal_analysis(
                self.mt5_connector, df, symbol, timeframe
            )
            
            if signal_analysis:
                return signal_analysis
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error analyzing {symbol} {timeframe}: {e}")
            return None
    
    def should_send_alert(self, symbol, timeframe, signal_analysis):
        """Check if alert should be sent (new or changed signal)"""
        if not signal_analysis:
            return False
            
        current_signal = signal_analysis.get('signal', 'WAIT')
        last_signal = self.last_signals[symbol][timeframe]
        
        # Send if new signal or signal changed
        if current_signal != last_signal and current_signal in ['BUY', 'SELL']:
            logger.info(f"🚀 New signal: {symbol} {timeframe} → {current_signal}")
            return True
            
        return False
    
    def send_telegram_alert(self, symbol, timeframe, signal_analysis):
        """Send Telegram alert with interactive buttons"""
        try:
            # Prepare signal data for Telegram
            telegram_data = {
                'symbol': symbol,
                'timeframe': timeframe,
                'signal': signal_analysis.get('signal', 'WAIT'),
                'confidence': signal_analysis.get('confidence', 0),
                'market_state': signal_analysis.get('market_state', 'UNKNOWN'),
                'htf_trend': signal_analysis.get('htf_trend', 'SIDEWAYS'),
                'trade_blocked': signal_analysis.get('trade_blocked', False),
                'block_reason': signal_analysis.get('block_reason', ''),
                'entry_confirmed': signal_analysis.get('entry_confirmed', False),
                'risk_reward': signal_analysis.get('risk_reward', {}),
                'structure_sl': signal_analysis.get('structure_sl', 0),
                'structure_tp': signal_analysis.get('structure_tp', 0),
                'reasons': signal_analysis.get('reasons', []),
                'factors': signal_analysis.get('factors', {}),
                'timestamp': datetime.now().isoformat()
            }
            
            # Send alert with chart
            chart_data = {
                'symbol': symbol,
                'timeframe': timeframe,
                'data': signal_analysis.get('factors', {})
            }
            
            success = self.telegram_assistant.send_trade_alert_with_chart(
                telegram_data, chart_data
            )
            
            if success:
                logger.info(f"✅ Telegram alert sent for {symbol} {timeframe}")
                # Update last signal
                self.last_signals[symbol][timeframe] = current_signal
            else:
                logger.warning(f"⚠️ Telegram alert failed for {symbol} {timeframe}")
                
        except Exception as e:
            logger.error(f"❌ Error sending Telegram alert: {e}")
    
    def scan_all_pairs(self):
        """Scan all symbols and timeframes"""
        if not self.mt5_connector.connected:
            logger.warning("⚠️ MT5 not connected - attempting reconnection...")
            if not self.initialize_mt5():
                return
        
        total_scans = len(SYMBOLS) * len(TIMEFRAMES)
        current_scan = 0
        
        for symbol in SYMBOLS:
            for timeframe in TIMEFRAMES:
                current_scan += 1
                logger.info(f"📊 [{current_scan}/{total_scans}] Scanning {symbol} {timeframe}")
                
                # Analyze signal
                signal_analysis = self.analyze_symbol_timeframe(symbol, timeframe)
                
                # Check if alert should be sent
                if self.should_send_alert(symbol, timeframe, signal_analysis):
                    self.send_telegram_alert(symbol, timeframe, signal_analysis)
                
                # Small delay to prevent overwhelming MT5
                time.sleep(0.1)
        
        logger.info(f"✅ Scan cycle completed - {total_scans} pairs analyzed")
    
    def run_scanner(self):
        """Main scanner loop"""
        logger.info("🚀 Starting continuous scanner...")
        self.running = True
        
        # Initialize MT5 connection
        if not self.initialize_mt5():
            logger.error("❌ Cannot start scanner without MT5 connection")
            return
        
        try:
            while self.running:
                start_time = time.time()
                
                # Run full scan cycle
                self.scan_all_pairs()
                
                # Calculate remaining time and sleep
                elapsed = time.time() - start_time
                sleep_time = max(0, SCAN_INTERVAL - elapsed)
                
                logger.info(f"⏳ Waiting {sleep_time:.1f}s until next scan...")
                time.sleep(sleep_time)
                
        except KeyboardInterrupt:
            logger.info("🛑 Scanner stopped by user")
        except Exception as e:
            logger.error(f"❌ Scanner error: {e}")
            time.sleep(10)  # Wait before retry
        finally:
            self.running = False
            logger.info("🛑 Scanner stopped")
    
    def stop(self):
        """Stop the scanner"""
        self.running = False

# Telegram bot setup
def setup_telegram_bot():
    """Setup and start Telegram bot with callback handling"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("❌ TELEGRAM_BOT_TOKEN not found in environment variables")
            return None
        
        updater = Updater(token=bot_token)
        dispatcher = updater.dispatcher
        
        # Setup callback handler for interactive buttons
        telegram_assistant = AdvancedTelegramAssistant()
        telegram_assistant.setup_callback_handler(dispatcher)
        
        # Add command handlers
        dispatcher.add_handler(CommandHandler("start", lambda update, context: 
            update.message.reply_text("🤖 BrayoForexBot Scanner Active!\n\nMonitoring:\n" + 
            "\n".join([f"• {symbol}" for symbol in SYMBOLS]) +
            f"\n\nTimeframes: {', '.join(TIMEFRAMES)}")))
        
        dispatcher.add_handler(CommandHandler("status", lambda update, context:
            update.message.reply_text("📊 Scanner Status: ✅ Running\n" +
            f"Symbols: {len(SYMBOLS)}\n" +
            f"Timeframes: {len(TIMEFRAMES)}\n" +
            f"Scan Interval: {SCAN_INTERVAL}s")))
        
        # Start polling
        updater.start_polling()
        logger.info("✅ Telegram bot started with interactive features")
        
        return updater
        
    except Exception as e:
        logger.error(f"❌ Telegram bot setup error: {e}")
        return None

# Main execution
def main():
    """Main function to run scanner and Telegram bot"""
    logger.info("🚀 Starting BrayoForexBot Continuous Scanner")
    
    # Start Telegram bot in separate thread
    telegram_thread = threading.Thread(target=setup_telegram_bot, daemon=True)
    telegram_thread.start()
    
    # Give Telegram bot time to start
    time.sleep(2)
    
    # Start scanner in main thread
    scanner = ContinuousScanner()
    
    try:
        scanner.run_scanner()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down scanner...")
        scanner.stop()
    
    logger.info("✅ Scanner shutdown complete")

if __name__ == "__main__":
    main()
