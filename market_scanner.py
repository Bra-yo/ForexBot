"""
Advanced Multi-Pair Multi-Timeframe Market Scanner
Independent scanning engine that monitors all pairs and timeframes
"""

import pandas as pd
import numpy as np
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass

from technical_analysis import TechnicalAnalysis
from brokers.mt5_connector import MT5Connector
from advanced_telegram_assistant import AdvancedTelegramAssistant

logger = logging.getLogger(__name__)

@dataclass
class ScanResult:
    """Data class for scan results"""
    symbol: str
    timeframe: str
    signal: str
    confidence: float
    market_state: str
    htf_trend: str
    entry_price: float
    structure_sl: float
    structure_tp: float
    risk_reward_ratio: float
    reasons: List[str]
    timestamp: datetime
    entry_confirmed: bool
    trade_blocked: bool

class MarketScanner:
    """Advanced multi-pair multi-timeframe market scanner"""
    
    def __init__(self, mt5_connector: MT5Connector, telegram_assistant: AdvancedTelegramAssistant):
        self.mt5_connector = mt5_connector
        self.telegram_assistant = telegram_assistant
        self.technical_analysis = TechnicalAnalysis()
        
        # Scanner configuration
        self.pairs = {
            'majors': ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD"],
            'crosses': ["EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY"],
            'metals': ["XAUUSD"]
        }
        
        self.timeframes = {
            'low': ['M5', 'M15'],      # Entry timeframes
            'mid': ['M30', 'H1'],      # Mid timeframes
            'high': ['H4']             # Trend confirmation
        }
        
        # All timeframes for scanning
        self.all_timeframes = self.timeframes['low'] + self.timeframes['mid'] + self.timeframes['high']
        
        # Anti-spam control
        self.signal_history = {}  # Track sent signals
        self.cooldown_minutes = 15  # Cooldown period per pair/timeframe
        self.max_signals_per_hour = 20  # Rate limiting
        
        # Scanner state
        self.scanning = False
        self.scan_thread = None
        self.stats = {
            'total_scans': 0,
            'signals_found': 0,
            'signals_sent': 0,
            'last_scan_time': None,
            'scan_duration_avg': 0
        }
        
        # Performance settings
        self.max_workers = 5  # Concurrent scans
        self.scan_delay = 2   # Seconds between scans
        self.error_delay = 5  # Seconds on error
        
        logger.info("MarketScanner initialized")
    
    def start_scanning(self):
        """Start the continuous scanning engine"""
        if self.scanning:
            logger.warning("Scanner already running")
            return
        
        self.scanning = True
        self.scan_thread = threading.Thread(target=self._scan_loop, daemon=True)
        self.scan_thread.start()
        logger.info("Market scanner started")
    
    def stop_scanning(self):
        """Stop the scanning engine"""
        self.scanning = False
        if self.scan_thread:
            self.scan_thread.join(timeout=10)
        logger.info("Market scanner stopped")
    
    def _scan_loop(self):
        """Main scanning loop"""
        logger.info("Starting continuous market scanning...")
        
        while self.scanning:
            try:
                scan_start = time.time()
                
                # Get all pairs
                all_pairs = self._get_all_pairs()
                
                # Scan all pairs and timeframes
                results = self._scan_market(all_pairs, self.all_timeframes)
                
                # Process results and send alerts
                self._process_scan_results(results)
                
                # Update stats
                self._update_stats(time.time() - scan_start, len(results))
                
                # Sleep between scans
                time.sleep(self.scan_delay)
                
            except Exception as e:
                logger.error(f"Error in scan loop: {e}")
                time.sleep(self.error_delay)
    
    def _get_all_pairs(self) -> List[str]:
        """Get all configured pairs"""
        all_pairs = []
        for category in self.pairs.values():
            all_pairs.extend(category)
        return all_pairs
    
    def _scan_market(self, pairs: List[str], timeframes: List[str]) -> List[ScanResult]:
        """Scan all pairs and timeframes"""
        results = []
        
        # Use thread pool for concurrent scanning
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all scan tasks
            future_to_pair_tf = {}
            
            for pair in pairs:
                for tf in timeframes:
                    future = executor.submit(self._scan_pair_timeframe, pair, tf)
                    future_to_pair_tf[future] = (pair, tf)
            
            # Collect results
            for future in as_completed(future_to_pair_tf):
                pair, tf = future_to_pair_tf[future]
                try:
                    result = future.result(timeout=30)
                    if result:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Error scanning {pair} {tf}: {e}")
        
        return results
    
    def _scan_pair_timeframe(self, symbol: str, timeframe: str) -> Optional[ScanResult]:
        """Scan a specific pair and timeframe"""
        try:
            # Get historical data
            historical_data = self.mt5_connector.get_historical_data(
                symbol=symbol,
                timeframe=timeframe,
                count=200  # Get enough data for analysis
            )
            
            if historical_data is None or historical_data.empty:
                return None
            
            # Perform advanced signal analysis
            advanced_signal = self.technical_analysis.advanced_signal_analysis(historical_data)
            
            # Check if this is a valid signal
            if not self._is_valid_signal(advanced_signal, symbol, timeframe):
                return None
            
            # Create scan result
            result = ScanResult(
                symbol=symbol,
                timeframe=timeframe,
                signal=advanced_signal['signal'],
                confidence=advanced_signal['confidence'],
                market_state=advanced_signal['market_state'],
                htf_trend=advanced_signal['htf_trend'],
                entry_price=historical_data['close'].iloc[-1],
                structure_sl=advanced_signal.get('structure_sl', 0),
                structure_tp=advanced_signal.get('structure_tp', 0),
                risk_reward_ratio=advanced_signal['risk_reward'].get('ratio', 0),
                reasons=advanced_signal['reasons'],
                timestamp=datetime.now(),
                entry_confirmed=advanced_signal['entry_confirmed'],
                trade_blocked=advanced_signal['trade_blocked']
            )
            
            logger.debug(f"Signal found: {symbol} {timeframe} {result.signal} ({result.confidence:.0f}%)")
            return result
            
        except Exception as e:
            logger.error(f"Error scanning {symbol} {timeframe}: {e}")
            return None
    
    def _is_valid_signal(self, signal_data: Dict, symbol: str, timeframe: str) -> bool:
        """Check if signal meets all criteria"""
        # Must be BUY or SELL (not WAIT)
        if signal_data['signal'] not in ['BUY', 'SELL']:
            return False
        
        # Must not be blocked
        if signal_data.get('trade_blocked', True):
            return False
        
        # Must have entry confirmation
        if not signal_data.get('entry_confirmed', False):
            return False
        
        # Must have valid risk:reward (>= 1:2)
        risk_reward = signal_data.get('risk_reward', {})
        if not risk_reward.get('valid', False) or risk_reward.get('ratio', 0) < 1.5:
            return False
        
        # Must have minimum confidence
        if signal_data.get('confidence', 0) < 50:
            return False
        
        # Check cooldown
        signal_key = f"{symbol}_{timeframe}_{signal_data['signal']}"
        if not self._check_cooldown(signal_key):
            return False
        
        return True
    
    def _check_cooldown(self, signal_key: str) -> bool:
        """Check if signal is still in cooldown period"""
        if signal_key not in self.signal_history:
            return True
        
        last_signal_time = self.signal_history[signal_key]
        time_since = datetime.now() - last_signal_time
        
        return time_since >= timedelta(minutes=self.cooldown_minutes)
    
    def _process_scan_results(self, results: List[ScanResult]):
        """Process scan results and send alerts"""
        for result in results:
            try:
                # Check cooldown again (in case of concurrent scans)
                signal_key = f"{result.symbol}_{result.timeframe}_{result.signal}"
                if not self._check_cooldown(signal_key):
                    continue
                
                # Prepare data for Telegram
                telegram_data = {
                    'symbol': result.symbol,
                    'signal': result.signal,
                    'confidence': result.confidence,
                    'market_state': result.market_state,
                    'htf_trend': result.htf_trend,
                    'entry_price': result.entry_price,
                    'structure_sl': result.structure_sl,
                    'structure_tp': result.structure_tp,
                    'risk_reward': {'ratio': result.risk_reward_ratio, 'valid': True},
                    'reasons': result.reasons,
                    'entry_confirmed': result.entry_confirmed,
                    'trade_blocked': result.trade_blocked,
                    'timeframe': result.timeframe  # Add timeframe for display
                }
                
                # Send Telegram alert
                alert_sent = self.telegram_assistant.send_trade_alert_with_chart(telegram_data)
                
                if alert_sent:
                    # Update signal history
                    self.signal_history[signal_key] = result.timestamp
                    self.stats['signals_sent'] += 1
                    
                    logger.info(f"Alert sent: {result.symbol} {result.timeframe} {result.signal}")
                else:
                    logger.debug(f"Alert blocked by cooldown for {signal_key}")
                
                self.stats['signals_found'] += 1
                
            except Exception as e:
                logger.error(f"Error processing result for {result.symbol}: {e}")
    
    def _update_stats(self, scan_duration: float, results_count: int):
        """Update scanning statistics"""
        self.stats['total_scans'] += 1
        self.stats['last_scan_time'] = datetime.now()
        
        # Update average scan duration
        if self.stats['total_scans'] == 1:
            self.stats['scan_duration_avg'] = scan_duration
        else:
            alpha = 0.1  # Smoothing factor
            self.stats['scan_duration_avg'] = (
                alpha * scan_duration + 
                (1 - alpha) * self.stats['scan_duration_avg']
            )
        
        # Log periodic stats
        if self.stats['total_scans'] % 50 == 0:
            self._log_stats()
    
    def _log_stats(self):
        """Log current statistics"""
        logger.info(f"""
Scanner Statistics:
- Total Scans: {self.stats['total_scans']}
- Signals Found: {self.stats['signals_found']}
- Signals Sent: {self.stats['signals_sent']}
- Avg Scan Duration: {self.stats['scan_duration_avg']:.2f}s
- Signal Rate: {self.stats['signals_sent'] / max(1, self.stats['total_scans']) * 100:.1f}%
        """)
    
    def get_stats(self) -> Dict:
        """Get current scanner statistics"""
        return self.stats.copy()
    
    def add_pair(self, symbol: str, category: str = 'custom'):
        """Add a new pair to scan"""
        if category not in self.pairs:
            self.pairs[category] = []
        
        if symbol not in self.pairs[category]:
            self.pairs[category].append(symbol)
            logger.info(f"Added {symbol} to {category} pairs")
    
    def remove_pair(self, symbol: str):
        """Remove a pair from scanning"""
        for category, pairs in self.pairs.items():
            if symbol in pairs:
                pairs.remove(symbol)
                logger.info(f"Removed {symbol} from {category} pairs")
                break
    
    def set_scan_delay(self, seconds: int):
        """Set delay between scans"""
        self.scan_delay = max(1, seconds)
        logger.info(f"Scan delay set to {self.scan_delay}s")
    
    def set_cooldown_minutes(self, minutes: int):
        """Set cooldown period for signals"""
        self.cooldown_minutes = max(5, minutes)
        logger.info(f"Signal cooldown set to {self.cooldown_minutes} minutes")
