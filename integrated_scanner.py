"""
Integrated Multi-Pair Scanner - Works with existing trading system
No separate process needed - integrates with current dashboard/engine
"""

import threading
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'brokers'))

from technical_analysis import TechnicalAnalysis
from mt5_connector import MT5Connector
from advanced_telegram_assistant import AdvancedTelegramAssistant
from auto_trading_manager import AutoTradingManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuration
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
TIMEFRAMES = ["M5", "M15", "M30", "H1"]
SCAN_INTERVAL = 60  # seconds between scans (longer for integration)

class IntegratedScanner:
    """Integrated scanner that works with existing trading system"""
    
    def __init__(self):
        self.mt5_connector = MT5Connector()
        self.technical_analysis = TechnicalAnalysis()
        self.telegram_assistant = AdvancedTelegramAssistant()
        self.auto_trading_manager = None  # Will be initialized later
        
        # Track last signals to avoid duplicates
        self.last_signals = {}
        for symbol in SYMBOLS:
            self.last_signals[symbol] = {}
            for timeframe in TIMEFRAMES:
                self.last_signals[symbol][timeframe] = None
        
        self.running = False
        self.scanner_thread = None
        
    def initialize_auto_trading(self, trade_manager):
        """Initialize auto trading manager with trade manager"""
        try:
            self.auto_trading_manager = AutoTradingManager(
                self.mt5_connector, 
                trade_manager, 
                self.telegram_assistant
            )
            logger.info("✅ Auto trading manager initialized")
            
            # Configure auto trading settings
            self.auto_trading_manager.update_config(
                enabled=True,
                min_confidence=60,
                max_trades=3,
                cooldown_minutes=5,
                risk_per_trade=1.0
            )
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize auto trading: {e}")
            return False
    
    def start_background_scanner(self):
        """Start scanner in background thread"""
        if self.scanner_thread and self.scanner_thread.is_alive():
            logger.info("Scanner already running")
            return
            
        self.scanner_thread = threading.Thread(target=self._scanner_loop, daemon=True)
        self.scanner_thread.start()
        logger.info("Background scanner started")
        
    def stop_scanner(self):
        """Stop the scanner"""
        self.running = False
        if self.scanner_thread:
            self.scanner_thread.join(timeout=5)
        logger.info("Background scanner stopped")
        
    def _scanner_loop(self):
        """Main scanner loop"""
        logger.info("Starting integrated scanner loop...")
        self.running = True
        
        try:
            while self.running:
                start_time = time.time()
                
                # Only scan if MT5 is connected
                if self.mt5_connector.connected:
                    self._scan_all_pairs()
                else:
                    logger.warning("MT5 not connected - skipping scan")
                
                # Calculate remaining time and sleep
                elapsed = time.time() - start_time
                sleep_time = max(0, SCAN_INTERVAL - elapsed)
                
                if sleep_time > 0:
                    logger.info(f"Waiting {sleep_time:.1f}s until next scan...")
                    time.sleep(sleep_time)
                    
        except Exception as e:
            logger.error(f"Scanner loop error: {e}")
            time.sleep(10)  # Wait before retry
        finally:
            self.running = False
            logger.info("Scanner loop ended")
    
    def _scan_all_pairs(self):
        """Scan all symbols and timeframes"""
        total_scans = len(SYMBOLS) * len(TIMEFRAMES)
        current_scan = 0
        
        for symbol in SYMBOLS:
            for timeframe in TIMEFRAMES:
                current_scan += 1
                logger.info(f"[{current_scan}/{total_scans}] Scanning {symbol} {timeframe}")
                
                # Analyze signal
                signal_analysis = self._analyze_symbol_timeframe(symbol, timeframe)
                
                # Check if alert should be sent
                if self._should_send_alert(symbol, timeframe, signal_analysis):
                    self._send_telegram_alert(symbol, timeframe, signal_analysis)
                
                # Small delay to prevent overwhelming MT5
                time.sleep(0.1)
        
        logger.info(f"Scan cycle completed - {total_scans} pairs analyzed")
    
    def _analyze_symbol_timeframe(self, symbol, timeframe):
        """Analyze single symbol and timeframe"""
        try:
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
                logger.warning(f"No data for {symbol} {timeframe}")
                return None
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(historical_data)
            
            # Perform advanced signal analysis
            signal_analysis = self.technical_analysis.advanced_signal_analysis(
                self.mt5_connector, df, symbol, timeframe
            )
            
            return signal_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol} {timeframe}: {e}")
            return None
    
    def _should_send_alert(self, symbol, timeframe, signal_analysis):
        """Check if alert should be sent (new or changed signal)"""
        if not signal_analysis:
            return False
            
        current_signal = signal_analysis.get('signal', 'WAIT')
        last_signal = self.last_signals[symbol][timeframe]
        
        # Send if new signal or signal changed
        if current_signal != last_signal and current_signal in ['BUY', 'SELL']:
            logger.info(f"NEW SIGNAL: {symbol} {timeframe} -> {current_signal}")
            return True
            
        return False
    
    def _send_telegram_alert(self, symbol, timeframe, signal_analysis):
        """Send Telegram alert with interactive buttons and execute auto trading"""
        try:
            # Execute auto trading first (only send alerts for executed trades)
            trade_executed = False
            if self.auto_trading_manager:
                logger.info(f"🤖 Checking auto trading for {symbol} {timeframe}...")
                
                # Prepare signal data for auto trading
                signal_data = {
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
                
                # Add current price for auto trading
                factors = signal_analysis.get('factors', {})
                if 'close' in factors:
                    signal_data['current_price'] = factors['close'].iloc[-1]
                else:
                    # Fallback: get current price from MT5
                    try:
                        tick = self.mt5_connector.get_symbol_tick(symbol)
                        if tick:
                            signal_data['current_price'] = tick.get('bid', 0)
                        else:
                            signal_data['current_price'] = 0
                    except:
                        signal_data['current_price'] = 0
                
                # Execute auto trade
                trade_executed = self.auto_trading_manager.execute_auto_trade(signal_data)
                
                if trade_executed:
                    logger.info(f"✅ Auto trade executed for {symbol}")
                else:
                    logger.info(f"🚫 Auto trade blocked for {symbol}")
            else:
                logger.warning("Auto trading manager not initialized")
            
            # Only send Telegram alert if trade was executed
            if trade_executed:
                logger.info(f"📱 Sending Telegram notification for executed trade: {symbol}")
                
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
                    'timestamp': datetime.now().isoformat(),
                    'current_price': signal_data.get('current_price', 0)
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
                    logger.info(f"✅ Telegram alert sent for executed trade: {symbol}")
                else:
                    logger.warning(f"❌ Telegram alert failed for executed trade: {symbol}")
            else:
                logger.info(f"📊 Trade not executed - no Telegram alert sent for {symbol}")
                
            # Update last signal
            self.last_signals[symbol][timeframe] = signal_analysis.get('signal', 'WAIT')
                
        except Exception as e:
            logger.error(f"Error in signal processing: {e}")
    
    def get_scanner_status(self):
        """Get current scanner status"""
        status = {
            'running': self.running,
            'thread_alive': self.scanner_thread.is_alive() if self.scanner_thread else False,
            'last_signals': self.last_signals,
            'symbols_count': len(SYMBOLS),
            'timeframes_count': len(TIMEFRAMES)
        }
        
        # Add auto trading status if available
        if self.auto_trading_manager:
            auto_trading_stats = self.auto_trading_manager.get_statistics()
            status['auto_trading'] = {
                'enabled': auto_trading_stats['config']['enabled'],
                'min_confidence': auto_trading_stats['config']['min_confidence'],
                'max_trades': auto_trading_stats['config']['max_trades'],
                'active_trades': auto_trading_stats['active_trades'],
                'total_trades': auto_trading_stats['stats']['total_trades'],
                'successful_trades': auto_trading_stats['stats']['successful_trades'],
                'failed_trades': auto_trading_stats['stats']['failed_trades']
            }
        else:
            status['auto_trading'] = {
                'enabled': False,
                'initialized': False
            }
        
        return status

# Global scanner instance
_integrated_scanner = None

def get_integrated_scanner():
    """Get the global integrated scanner instance"""
    global _integrated_scanner
    return _integrated_scanner

def start_integrated_scanner():
    """Start the integrated scanner"""
    global _integrated_scanner
    if _integrated_scanner is None:
        _integrated_scanner = IntegratedScanner()
    
    _integrated_scanner.start_background_scanner()
    logger.info("Integrated scanner started successfully")

def stop_integrated_scanner():
    """Stop the integrated scanner"""
    global _integrated_scanner
    if _integrated_scanner:
        _integrated_scanner.stop_scanner()

# Auto-start when imported (only if not already running)
if __name__ != "__main__":
    try:
        # Check if trading engine is running
        from trading_engine import get_global_engine
        engine = get_global_engine()
        
        if engine and engine.running:
            logger.info("Trading engine detected - starting integrated scanner")
            start_integrated_scanner()
        else:
            logger.info("Trading engine not running - scanner on standby")
    except:
        # If trading engine import fails, don't auto-start
        logger.info("Standalone mode - scanner waiting for manual start")
