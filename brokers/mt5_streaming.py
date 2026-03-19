"""
MT5 Real-Time Market Data Streaming
Professional tick-by-tick data streaming for BrayoForexBot
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import time
import threading
import queue
import asyncio
import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from collections import defaultdict, deque
from mt5_connector import MT5Connector

logger = logging.getLogger(__name__)

@dataclass
class TickData:
    """Tick data structure"""
    symbol: str
    bid: float
    ask: float
    last: float
    volume: int
    time: datetime
    spread: float

@dataclass
class BarData:
    """Bar/candlestick data structure"""
    symbol: str
    timeframe: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    time: datetime

class MT5Streamer:
    """
    Professional MT5 real-time data streaming
    Handles tick data, bar updates, and real-time analytics
    """
    
    def __init__(self, mt5_connector: MT5Connector):
        self.mt5 = mt5_connector
        self.streaming = False
        self.subscribers = defaultdict(list)
        self.tick_queues = defaultdict(queue.Queue)
        self.bar_queues = defaultdict(queue.Queue)
        
        # Streaming threads
        self.tick_thread = None
        self.bar_thread = None
        self.analytics_thread = None
        
        # Data storage
        self.latest_ticks = {}
        self.latest_bars = defaultdict(dict)
        self.tick_history = defaultdict(lambda: deque(maxlen=1000))
        self.bar_history = defaultdict(lambda: deque(maxlen=500))
        
        # Analytics
        self.analytics_cache = {}
        self.analytics_callbacks = []
        
        # Performance tracking
        self.stats = {
            'ticks_received': 0,
            'bars_generated': 0,
            'last_update': None,
            'subscribers_count': 0,
            'errors_count': 0
        }
        
        # Rate limiting
        self.max_updates_per_second = 100
        self.last_update_time = 0
        
    def start_streaming(self, symbols: List[str], timeframes: List[str] = None):
        """
        Start real-time streaming for symbols
        
        Args:
            symbols: List of symbols to stream
            timeframes: List of timeframes for bar generation
        """
        try:
            if self.streaming:
                logger.warning("Streaming already active")
                return
            
            if timeframes is None:
                timeframes = ['M1', 'M5', 'M15', 'H1']
            
            # Initialize subscribers
            for symbol in symbols:
                self.subscribers[symbol] = {
                    'active': True,
                    'timeframes': timeframes.copy(),
                    'callbacks': []
                }
            
            # Start streaming threads
            self.streaming = True
            
            # Tick streaming thread
            self.tick_thread = threading.Thread(
                target=self._tick_streaming_loop,
                daemon=True
            )
            self.tick_thread.start()
            
            # Bar generation thread
            self.bar_thread = threading.Thread(
                target=self._bar_generation_loop,
                daemon=True
            )
            self.bar_thread.start()
            
            # Analytics thread
            self.analytics_thread = threading.Thread(
                target=self._analytics_loop,
                daemon=True
            )
            self.analytics_thread.start()
            
            logger.info(f"Started streaming for {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Error starting streaming: {e}")
            self.streaming = False
    
    def stop_streaming(self):
        """Stop all streaming"""
        try:
            self.streaming = False
            
            # Wait for threads to finish
            if self.tick_thread:
                self.tick_thread.join(timeout=5)
            if self.bar_thread:
                self.bar_thread.join(timeout=5)
            if self.analytics_thread:
                self.analytics_thread.join(timeout=5)
            
            logger.info("Stopped streaming")
            
        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")
    
    def subscribe_to_ticks(self, symbol: str, callback: Callable[[TickData], None]):
        """
        Subscribe to tick updates for a symbol
        
        Args:
            symbol: Currency pair
            callback: Function to call on each tick
        """
        try:
            if symbol not in self.subscribers:
                self.subscribers[symbol] = {'active': True, 'timeframes': [], 'callbacks': []}
            
            self.subscribers[symbol]['callbacks'].append(callback)
            self.stats['subscribers_count'] += 1
            
            logger.info(f"Added tick subscriber for {symbol}")
            
        except Exception as e:
            logger.error(f"Error subscribing to ticks: {e}")
    
    def subscribe_to_bars(self, symbol: str, timeframe: str, 
                         callback: Callable[[BarData], None]):
        """
        Subscribe to bar updates for a symbol and timeframe
        
        Args:
            symbol: Currency pair
            timeframe: Timeframe (M1, M5, M15, H1, etc.)
            callback: Function to call on each bar
        """
        try:
            if symbol not in self.subscribers:
                self.subscribers[symbol] = {'active': True, 'timeframes': [], 'callbacks': []}
            
            # Add timeframe if not present
            if timeframe not in self.subscribers[symbol]['timeframes']:
                self.subscribers[symbol]['timeframes'].append(timeframe)
            
            # Store callback with timeframe
            callback_data = {
                'type': 'bar',
                'timeframe': timeframe,
                'callback': callback
            }
            self.subscribers[symbol]['callbacks'].append(callback_data)
            self.stats['subscribers_count'] += 1
            
            logger.info(f"Added bar subscriber for {symbol} {timeframe}")
            
        except Exception as e:
            logger.error(f"Error subscribing to bars: {e}")
    
    def get_latest_tick(self, symbol: str) -> Optional[TickData]:
        """Get latest tick for a symbol"""
        try:
            return self.latest_ticks.get(symbol)
        except Exception as e:
            logger.error(f"Error getting latest tick: {e}")
            return None
    
    def get_latest_bar(self, symbol: str, timeframe: str) -> Optional[BarData]:
        """Get latest bar for a symbol and timeframe"""
        try:
            return self.latest_bars[symbol].get(timeframe)
        except Exception as e:
            logger.error(f"Error getting latest bar: {e}")
            return None
    
    def get_tick_history(self, symbol: str, limit: int = 100) -> List[TickData]:
        """Get recent tick history"""
        try:
            history = list(self.tick_history[symbol])
            return history[-limit:] if len(history) > limit else history
        except Exception as e:
            logger.error(f"Error getting tick history: {e}")
            return []
    
    def get_bar_history(self, symbol: str, timeframe: str, 
                       limit: int = 100) -> List[BarData]:
        """Get recent bar history"""
        try:
            history = list(self.bar_history[symbol])
            # Filter by timeframe
            filtered = [bar for bar in history if bar.timeframe == timeframe]
            return filtered[-limit:] if len(filtered) > limit else filtered
        except Exception as e:
            logger.error(f"Error getting bar history: {e}")
            return []
    
    def calculate_real_time_indicators(self, symbol: str, timeframe: str) -> Dict:
        """Calculate real-time technical indicators"""
        try:
            cache_key = f"{symbol}_{timeframe}"
            
            # Check cache
            if cache_key in self.analytics_cache:
                cached_data, timestamp = self.analytics_cache[cache_key]
                if time.time() - timestamp < 5:  # 5 second cache
                    return cached_data
            
            # Get bar history
            bars = self.get_bar_history(symbol, timeframe, limit=100)
            if len(bars) < 20:
                return {}
            
            # Extract prices
            closes = [bar.close for bar in bars]
            highs = [bar.high for bar in bars]
            lows = [bar.low for bar in bars]
            volumes = [bar.volume for bar in bars]
            
            # Calculate indicators
            indicators = {}
            
            # Moving averages
            if len(closes) >= 20:
                indicators['sma_20'] = np.mean(closes[-20:])
            if len(closes) >= 50:
                indicators['sma_50'] = np.mean(closes[-50:])
            
            # RSI
            if len(closes) >= 14:
                rsi = self._calculate_rsi(closes)
                indicators['rsi'] = rsi[-1] if rsi else None
            
            # Bollinger Bands
            if len(closes) >= 20:
                bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(closes)
                indicators['bb_upper'] = bb_upper[-1] if bb_upper else None
                indicators['bb_middle'] = bb_middle[-1] if bb_middle else None
                indicators['bb_lower'] = bb_lower[-1] if bb_lower else None
            
            # Volume indicators
            indicators['volume_avg'] = np.mean(volumes[-20:]) if len(volumes) >= 20 else None
            indicators['volume_ratio'] = volumes[-1] / indicators['volume_avg'] if indicators['volume_avg'] and volumes[-1] > 0 else None
            
            # Cache results
            self.analytics_cache[cache_key] = (indicators, time.time())
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return {}
    
    def _tick_streaming_loop(self):
        """Main tick streaming loop"""
        while self.streaming:
            try:
                # Rate limiting
                self._enforce_rate_limit()
                
                # Get ticks for all subscribed symbols
                for symbol in self.subscribers.keys():
                    if not self.subscribers[symbol]['active']:
                        continue
                    
                    try:
                        # Get current tick
                        tick_data = self.mt5.get_current_price(symbol)
                        
                        if 'error' not in tick_data:
                            # Create tick object
                            tick = TickData(
                                symbol=symbol,
                                bid=tick_data['bid'],
                                ask=tick_data['ask'],
                                last=tick_data.get('last', tick_data['bid']),
                                volume=tick_data.get('volume', 0),
                                time=tick_data['time'],
                                spread=tick_data['ask'] - tick_data['bid']
                            )
                            
                            # Store latest tick
                            self.latest_ticks[symbol] = tick
                            
                            # Add to history
                            self.tick_history[symbol].append(tick)
                            
                            # Add to queue
                            self.tick_queues[symbol].put(tick)
                            
                            # Update stats
                            self.stats['ticks_received'] += 1
                            self.stats['last_update'] = datetime.now()
                            
                            # Notify subscribers
                            self._notify_tick_subscribers(symbol, tick)
                        
                    except Exception as e:
                        self.stats['errors_count'] += 1
                        logger.error(f"Error getting tick for {symbol}: {e}")
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in tick streaming loop: {e}")
                time.sleep(1)
    
    def _bar_generation_loop(self):
        """Generate bars from tick data"""
        while self.streaming:
            try:
                for symbol in self.subscribers.keys():
                    if not self.subscribers[symbol]['active']:
                        continue
                    
                    # Process each timeframe
                    for timeframe in self.subscribers[symbol]['timeframes']:
                        try:
                            # Get timeframe duration in seconds
                            duration = self._get_timeframe_duration(timeframe)
                            if duration is None:
                                continue
                            
                            # Check if we need to generate a new bar
                            latest_bar = self.get_latest_bar(symbol, timeframe)
                            current_time = datetime.now()
                            
                            if latest_bar is None:
                                # Create first bar
                                self._create_new_bar(symbol, timeframe, current_time, duration)
                            else:
                                # Check if bar period has ended
                                bar_end = self._get_bar_end_time(latest_bar.time, duration)
                                
                                if current_time >= bar_end:
                                    # Close current bar and create new one
                                    self._close_bar(symbol, timeframe, latest_bar)
                                    self._create_new_bar(symbol, timeframe, current_time, duration)
                                else:
                                    # Update current bar
                                    self._update_bar(symbol, timeframe, latest_bar)
                        
                        except Exception as e:
                            logger.error(f"Error generating bar for {symbol} {timeframe}: {e}")
                
                time.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in bar generation loop: {e}")
                time.sleep(1)
    
    def _analytics_loop(self):
        """Analytics processing loop"""
        while self.streaming:
            try:
                # Process analytics for all symbols and timeframes
                for symbol in self.subscribers.keys():
                    for timeframe in self.subscribers[symbol]['timeframes']:
                        # Calculate indicators
                        indicators = self.calculate_real_time_indicators(symbol, timeframe)
                        
                        if indicators:
                            # Notify analytics callbacks
                            self._notify_analytics_callbacks(symbol, timeframe, indicators)
                
                time.sleep(2)  # Update every 2 seconds
                
            except Exception as e:
                logger.error(f"Error in analytics loop: {e}")
                time.sleep(1)
    
    def _create_new_bar(self, symbol: str, timeframe: str, current_time: datetime, 
                       duration: int):
        """Create a new bar"""
        try:
            # Get latest tick for open price
            latest_tick = self.get_latest_tick(symbol)
            if latest_tick is None:
                return
            
            # Calculate bar start time
            bar_start = self._get_bar_start_time(current_time, duration)
            
            # Create new bar
            bar = BarData(
                symbol=symbol,
                timeframe=timeframe,
                open=latest_tick.bid,
                high=latest_tick.ask,
                low=latest_tick.bid,
                close=latest_tick.bid,
                volume=latest_tick.volume,
                time=bar_start
            )
            
            # Store latest bar
            self.latest_bars[symbol][timeframe] = bar
            
        except Exception as e:
            logger.error(f"Error creating new bar: {e}")
    
    def _update_bar(self, symbol: str, timeframe: str, bar: BarData):
        """Update existing bar with new tick"""
        try:
            latest_tick = self.get_latest_tick(symbol)
            if latest_tick is None:
                return
            
            # Update OHLC
            bar.high = max(bar.high, latest_tick.ask)
            bar.low = min(bar.low, latest_tick.bid)
            bar.close = latest_tick.bid
            bar.volume += latest_tick.volume
            
        except Exception as e:
            logger.error(f"Error updating bar: {e}")
    
    def _close_bar(self, symbol: str, timeframe: str, bar: BarData):
        """Close a bar and add to history"""
        try:
            # Add to history
            self.bar_history[symbol].append(bar)
            
            # Notify bar subscribers
            self._notify_bar_subscribers(symbol, bar)
            
            # Update stats
            self.stats['bars_generated'] += 1
            
        except Exception as e:
            logger.error(f"Error closing bar: {e}")
    
    def _notify_tick_subscribers(self, symbol: str, tick: TickData):
        """Notify tick subscribers"""
        try:
            if symbol not in self.subscribers:
                return
            
            for callback_data in self.subscribers[symbol]['callbacks']:
                if isinstance(callback_data, dict) and callback_data['type'] == 'bar':
                    continue  # Skip bar callbacks
                
                try:
                    callback_data(tick) if callable(callback_data) else None
                except Exception as e:
                    logger.error(f"Error in tick callback: {e}")
                    
        except Exception as e:
            logger.error(f"Error notifying tick subscribers: {e}")
    
    def _notify_bar_subscribers(self, symbol: str, bar: BarData):
        """Notify bar subscribers"""
        try:
            if symbol not in self.subscribers:
                return
            
            for callback_data in self.subscribers[symbol]['callbacks']:
                if isinstance(callback_data, dict) and callback_data['type'] == 'bar':
                    if callback_data['timeframe'] == bar.timeframe:
                        try:
                            callback_data['callback'](bar)
                        except Exception as e:
                            logger.error(f"Error in bar callback: {e}")
                            
        except Exception as e:
            logger.error(f"Error notifying bar subscribers: {e}")
    
    def _notify_analytics_callbacks(self, symbol: str, timeframe: str, indicators: Dict):
        """Notify analytics callbacks"""
        try:
            for callback in self.analytics_callbacks:
                try:
                    callback(symbol, timeframe, indicators)
                except Exception as e:
                    logger.error(f"Error in analytics callback: {e}")
        except Exception as e:
            logger.error(f"Error notifying analytics callbacks: {e}")
    
    def _get_timeframe_duration(self, timeframe: str) -> Optional[int]:
        """Get timeframe duration in seconds"""
        timeframe_map = {
            'M1': 60,
            'M5': 300,
            'M15': 900,
            'M30': 1800,
            'H1': 3600,
            'H4': 14400,
            'D1': 86400
        }
        return timeframe_map.get(timeframe)
    
    def _get_bar_start_time(self, current_time: datetime, duration: int) -> datetime:
        """Get bar start time"""
        timestamp = int(current_time.timestamp())
        bar_start = (timestamp // duration) * duration
        return datetime.fromtimestamp(bar_start)
    
    def _get_bar_end_time(self, bar_start: datetime, duration: int) -> datetime:
        """Get bar end time"""
        return bar_start + timedelta(seconds=duration)
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting"""
        try:
            current_time = time.time()
            time_since_last = current_time - self.last_update_time
            
            min_interval = 1.0 / self.max_updates_per_second
            
            if time_since_last < min_interval:
                time.sleep(min_interval - time_since_last)
            
            self.last_update_time = time.time()
            
        except Exception as e:
            logger.error(f"Error in rate limiting: {e}")
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> List[float]:
        """Calculate RSI"""
        try:
            if len(prices) < period + 1:
                return []
            
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = pd.Series(gains).rolling(window=period).mean()
            avg_loss = pd.Series(losses).rolling(window=period).mean()
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.fillna(0).tolist()
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return []
    
    def _calculate_bollinger_bands(self, prices: List[float], period: int = 20, 
                                 std_dev: int = 2) -> Tuple[List[float], List[float], List[float]]:
        """Calculate Bollinger Bands"""
        try:
            if len(prices) < period:
                return [], [], []
            
            prices_series = pd.Series(prices)
            sma = prices_series.rolling(window=period).mean()
            std = prices_series.rolling(window=period).std()
            
            upper = sma + (std * std_dev)
            lower = sma - (std * std_dev)
            
            return upper.fillna(0).tolist(), sma.fillna(0).tolist(), lower.fillna(0).tolist()
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return [], [], []
    
    def add_analytics_callback(self, callback: Callable[[str, str, Dict], None]):
        """Add analytics callback"""
        self.analytics_callbacks.append(callback)
    
    def get_streaming_stats(self) -> Dict:
        """Get streaming statistics"""
        try:
            return {
                **self.stats,
                'active_symbols': len([s for s in self.subscribers.keys() if self.subscribers[s]['active']]),
                'total_symbols': len(self.subscribers),
                'cache_size': len(self.analytics_cache),
                'streaming': self.streaming
            }
        except Exception as e:
            logger.error(f"Error getting streaming stats: {e}")
            return {}
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.stop_streaming()
        except:
            pass
