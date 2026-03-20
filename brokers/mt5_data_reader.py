"""
MT5 Data Reader for BrayoForexBot
Real-time and historical forex data from MetaTrader 5
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import time
import threading
import queue
import logging
from typing import Dict, List, Optional, Callable
from .mt5_connector import MT5Connector

logger = logging.getLogger(__name__)

class MT5DataReader:
    """
    Advanced MT5 data reader with real-time streaming and caching
    """
    
    def __init__(self, mt5_connector: MT5Connector):
        self.mt5 = mt5_connector
        self.data_cache = {}
        self.real_time_queue = queue.Queue()
        self.streaming = False
        self.streaming_thread = None
        self.subscribers = {}
        self.update_callbacks = []
        
        # Cache settings
        self.cache_timeout = 60  # seconds
        self.max_cache_size = 1000
        
        # Supported timeframes
        self.timeframes = {
            'M1': '1 minute',
            'M5': '5 minutes',
            'M15': '15 minutes',
            'M30': '30 minutes',
            'H1': '1 hour',
            'H4': '4 hours',
            'D1': '1 day',
            'W1': '1 week',
            'MN1': '1 month'
        }
        
    def get_historical_data(self, symbol: str, timeframe: str, 
                           start_date: datetime, end_date: datetime,
                           use_cache: bool = True) -> pd.DataFrame:
        """
        Get historical data with caching
        
        Args:
            symbol: Currency pair (e.g., 'EURUSD')
            timeframe: Timeframe string
            start_date: Start date
            end_date: End date
            use_cache: Whether to use cached data
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Check cache first
            cache_key = f"{symbol}_{timeframe}_{start_date}_{end_date}"
            
            if use_cache and cache_key in self.data_cache:
                cached_data, timestamp = self.data_cache[cache_key]
                if time.time() - timestamp < self.cache_timeout:
                    logger.debug(f"Using cached data for {cache_key}")
                    return cached_data.copy()
            
            # Get data from MT5
            data = self.mt5.get_historical_data(symbol, timeframe, start_date, end_date)
            
            if data.empty:
                logger.warning(f"No data returned for {symbol} {timeframe}")
                return pd.DataFrame()
            
            # Cache the data
            if use_cache:
                self._cache_data(cache_key, data)
            
            logger.info(f"Retrieved {len(data)} candles for {symbol} {timeframe}")
            return data
            
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return pd.DataFrame()
    
    def get_latest_data(self, symbol: str, timeframe: str, 
                       bars: int = 100) -> pd.DataFrame:
        """
        Get latest N bars for a symbol
        
        Args:
            symbol: Currency pair
            timeframe: Timeframe
            bars: Number of bars to retrieve
            
        Returns:
            DataFrame with latest data
        """
        try:
            # Calculate start date based on timeframe
            timeframe_minutes = {
                'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30,
                'H1': 60, 'H4': 240, 'D1': 1440
            }
            
            minutes = timeframe_minutes.get(timeframe, 60)
            start_date = datetime.now() - timedelta(minutes=minutes * bars)
            end_date = datetime.now()
            
            return self.get_historical_data(symbol, timeframe, start_date, end_date)
            
        except Exception as e:
            logger.error(f"Error getting latest data: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> Dict:
        """Get current bid/ask price"""
        try:
            return self.mt5.get_current_price(symbol)
        except Exception as e:
            logger.error(f"Error getting current price: {e}")
            return {'error': str(e)}
    
    def get_multiple_symbols(self, symbols: List[str], timeframe: str,
                           start_date: datetime, end_date: datetime) -> Dict[str, pd.DataFrame]:
        """
        Get data for multiple symbols
        
        Args:
            symbols: List of currency pairs
            timeframe: Timeframe
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary of DataFrames
        """
        try:
            data_dict = {}
            
            for symbol in symbols:
                data = self.get_historical_data(symbol, timeframe, start_date, end_date)
                if not data.empty:
                    data_dict[symbol] = data
                else:
                    logger.warning(f"No data for {symbol}")
            
            logger.info(f"Retrieved data for {len(data_dict)}/{len(symbols)} symbols")
            return data_dict
            
        except Exception as e:
            logger.error(f"Error getting multiple symbols: {e}")
            return {}
    
    def start_real_time_stream(self, symbols: List[str], timeframe: str = 'M1'):
        """
        Start real-time data streaming
        
        Args:
            symbols: List of symbols to stream
            timeframe: Timeframe for data
        """
        try:
            if self.streaming:
                logger.warning("Streaming already active")
                return
            
            self.streaming = True
            self.subscribers = {symbol: {'timeframe': timeframe} for symbol in symbols}
            
            # Start streaming thread
            self.streaming_thread = threading.Thread(
                target=self._stream_data_loop,
                daemon=True
            )
            self.streaming_thread.start()
            
            logger.info(f"Started real-time streaming for {len(symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Error starting real-time stream: {e}")
            self.streaming = False
    
    def stop_real_time_stream(self):
        """Stop real-time data streaming"""
        try:
            self.streaming = False
            if self.streaming_thread:
                self.streaming_thread.join(timeout=5)
            
            logger.info("Stopped real-time streaming")
            
        except Exception as e:
            logger.error(f"Error stopping stream: {e}")
    
    def _stream_data_loop(self):
        """Main streaming loop"""
        while self.streaming:
            try:
                for symbol, config in self.subscribers.items():
                    # Get latest tick data
                    tick_data = self.get_current_price(symbol)
                    
                    if 'error' not in tick_data:
                        # Add to queue
                        self.real_time_queue.put({
                            'symbol': symbol,
                            'data': tick_data,
                            'timestamp': datetime.now()
                        })
                        
                        # Notify subscribers
                        self._notify_subscribers(symbol, tick_data)
                
                # Sleep to prevent excessive CPU usage
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Error in streaming loop: {e}")
                time.sleep(1)
    
    def _notify_subscribers(self, symbol: str, data: Dict):
        """Notify subscribers of new data"""
        try:
            for callback in self.update_callbacks:
                try:
                    callback(symbol, data)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")
        except Exception as e:
            logger.error(f"Error notifying subscribers: {e}")
    
    def subscribe_to_updates(self, callback: Callable[[str, Dict], None]):
        """
        Subscribe to real-time data updates
        
        Args:
            callback: Function to call when new data arrives
        """
        self.update_callbacks.append(callback)
        logger.info(f"Added subscriber (total: {len(self.update_callbacks)})")
    
    def unsubscribe_from_updates(self, callback: Callable[[str, Dict], None]):
        """Unsubscribe from real-time updates"""
        try:
            self.update_callbacks.remove(callback)
            logger.info(f"Removed subscriber (total: {len(self.update_callbacks)})")
        except ValueError:
            logger.warning("Callback not found in subscribers")
    
    def get_latest_tick(self, symbol: str, timeout: float = 5.0) -> Optional[Dict]:
        """
        Get latest tick from queue
        
        Args:
            symbol: Symbol to get tick for
            timeout: Maximum wait time
            
        Returns:
            Latest tick data or None
        """
        try:
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                try:
                    item = self.real_time_queue.get(timeout=0.1)
                    if item['symbol'] == symbol:
                        return item['data']
                    else:
                        # Put back in queue for other symbols
                        self.real_time_queue.put(item)
                except queue.Empty:
                    continue
            
            logger.warning(f"No tick received for {symbol} within {timeout}s")
            return None
            
        except Exception as e:
            logger.error(f"Error getting latest tick: {e}")
            return None
    
    def get_market_overview(self, symbols: List[str]) -> Dict:
        """
        Get market overview for multiple symbols
        
        Args:
            symbols: List of symbols
            
        Returns:
            Market overview dictionary
        """
        try:
            overview = {}
            
            for symbol in symbols:
                # Get current price
                price_data = self.get_current_price(symbol)
                
                if 'error' not in price_data:
                    # Get latest daily data for daily change
                    daily_data = self.get_latest_data(symbol, 'D1', bars=2)
                    
                    if not daily_data.empty and len(daily_data) >= 2:
                        prev_close = daily_data['close'].iloc[-2]
                        current_price = price_data['bid']
                        daily_change = (current_price - prev_close) / prev_close * 100
                    else:
                        daily_change = 0
                    
                    # Get symbol info
                    symbol_info = self.mt5.get_symbol_info(symbol)
                    
                    overview[symbol] = {
                        'bid': price_data['bid'],
                        'ask': price_data['ask'],
                        'spread': price_data['ask'] - price_data['bid'],
                        'daily_change': daily_change,
                        'volume': price_data.get('volume', 0),
                        'digits': symbol_info.get('digits', 5),
                        'point': symbol_info.get('point', 0.00001),
                        'market_open': self.mt5.is_market_open(symbol),
                        'last_update': price_data['time']
                    }
                else:
                    overview[symbol] = {'error': price_data['error']}
            
            return overview
            
        except Exception as e:
            logger.error(f"Error getting market overview: {e}")
            return {}
    
    def calculate_spread_statistics(self, symbol: str, samples: int = 100) -> Dict:
        """
        Calculate spread statistics for a symbol
        
        Args:
            symbol: Currency pair
            samples: Number of samples to collect
            
        Returns:
            Spread statistics
        """
        try:
            spreads = []
            
            for _ in range(samples):
                price_data = self.get_current_price(symbol)
                if 'error' not in price_data:
                    spread = price_data['ask'] - price_data['bid']
                    spreads.append(spread)
                time.sleep(0.1)  # Small delay between samples
            
            if not spreads:
                return {'error': 'No spread data collected'}
            
            return {
                'symbol': symbol,
                'samples': len(spreads),
                'avg_spread': np.mean(spreads),
                'min_spread': np.min(spreads),
                'max_spread': np.max(spreads),
                'std_spread': np.std(spreads),
                'current_spread': spreads[-1] if spreads else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating spread statistics: {e}")
            return {'error': str(e)}
    
    def validate_data_quality(self, data: pd.DataFrame, symbol: str) -> Dict:
        """
        Validate data quality and detect issues
        
        Args:
            data: DataFrame to validate
            symbol: Symbol name for logging
            
        Returns:
            Validation results
        """
        try:
            if data.empty:
                return {'valid': False, 'errors': ['Empty dataset']}
            
            errors = []
            warnings = []
            
            # Check for missing values
            missing_values = data.isnull().sum()
            if missing_values.any():
                errors.append(f"Missing values: {missing_values.to_dict()}")
            
            # Check for duplicate timestamps
            duplicates = data.index.duplicated().sum()
            if duplicates > 0:
                warnings.append(f"{duplicates} duplicate timestamps")
            
            # Check for price anomalies
            for col in ['open', 'high', 'low', 'close']:
                if col in data.columns:
                    # Check for zero or negative prices
                    if (data[col] <= 0).any():
                        errors.append(f"Zero/negative {col} values")
                    
                    # Check for extreme price changes
                    if len(data) > 1:
                        pct_change = data[col].pct_change().abs()
                        extreme_changes = (pct_change > 0.1).sum()  # >10% changes
                        if extreme_changes > 0:
                            warnings.append(f"{extreme_changes} extreme price changes in {col}")
            
            # Check OHLC consistency
            if all(col in data.columns for col in ['open', 'high', 'low', 'close']):
                # High should be >= all other prices
                invalid_high = (data['high'] < data['open']).any() or \
                              (data['high'] < data['low']).any() or \
                              (data['high'] < data['close']).any()
                
                # Low should be <= all other prices
                invalid_low = (data['low'] > data['open']).any() or \
                             (data['low'] > data['high']).any() or \
                             (data['low'] > data['close']).any()
                
                if invalid_high:
                    errors.append("Invalid high prices (lower than other OHLC)")
                if invalid_low:
                    errors.append("Invalid low prices (higher than other OHLC)")
            
            return {
                'valid': len(errors) == 0,
                'errors': errors,
                'warnings': warnings,
                'total_records': len(data),
                'date_range': f"{data.index.min()} to {data.index.max()}"
            }
            
        except Exception as e:
            logger.error(f"Error validating data quality: {e}")
            return {'valid': False, 'errors': [str(e)]}
    
    def _cache_data(self, key: str, data: pd.DataFrame):
        """Cache data with LRU eviction"""
        try:
            # Remove oldest data if cache is full
            if len(self.data_cache) >= self.max_cache_size:
                oldest_key = min(self.data_cache.keys(), 
                              key=lambda k: self.data_cache[k][1])
                del self.data_cache[oldest_key]
            
            self.data_cache[key] = (data.copy(), time.time())
            
        except Exception as e:
            logger.error(f"Error caching data: {e}")
    
    def clear_cache(self):
        """Clear all cached data"""
        try:
            self.data_cache.clear()
            logger.info("Data cache cleared")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def get_cache_info(self) -> Dict:
        """Get cache statistics"""
        try:
            return {
                'cached_items': len(self.data_cache),
                'max_size': self.max_cache_size,
                'cache_timeout': self.cache_timeout,
                'streaming_active': self.streaming,
                'subscribers': len(self.update_callbacks),
                'monitored_symbols': list(self.subscribers.keys())
            }
        except Exception as e:
            logger.error(f"Error getting cache info: {e}")
            return {}
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.stop_real_time_stream()
        except:
            pass
