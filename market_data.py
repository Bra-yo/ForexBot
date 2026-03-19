"""
Market Data Reader Module for BrayoForexBot
Handles fetching and processing forex market data
"""

import pandas as pd
import numpy as np
import yfinance as yf
import requests
import time
from datetime import datetime, timedelta
from config import Config
import logging

logger = logging.getLogger(__name__)

class MarketDataReader:
    """Class for reading and managing forex market data"""
    
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 60  # Cache data for 60 seconds
        
    def get_forex_data(self, pair, timeframe='1h', period='7d'):
        """
        Get forex data for a specific pair and timeframe
        
        Args:
            pair (str): Currency pair (e.g., 'EUR/USD')
            timeframe (str): Timeframe ('1m', '5m', '15m', '1h', '4h', '1d')
            period (str): Period to fetch ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
            
        Returns:
            pd.DataFrame: OHLCV data
        """
        try:
            # Convert pair format for yfinance (EURUSD instead of EUR/USD)
            yf_pair = pair.replace('/', '') + '=X'
            
            # Map timeframes to yfinance intervals
            interval_map = {
                '1m': '1m',
                '5m': '5m', 
                '15m': '15m',
                '1h': '1h',
                '4h': '1h',  # yfinance doesn't have 4h, use 1h and resample
                '1d': '1d'
            }
            
            interval = interval_map.get(timeframe, '1h')
            
            # Check cache
            cache_key = f"{yf_pair}_{interval}_{period}"
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if time.time() - timestamp < self.cache_timeout:
                    logger.debug(f"Using cached data for {pair}")
                    return cached_data
            
            # Fetch data from yfinance
            ticker = yf.Ticker(yf_pair)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"No data found for {pair}")
                return pd.DataFrame()
            
            # Standardize column names
            data.columns = [col.lower() for col in data.columns]
            data = data.rename(columns={
                'open': 'open',
                'high': 'high', 
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # Resample for 4h timeframe
            if timeframe == '4h' and interval == '1h':
                data = self.resample_data(data, '4h')
            
            # Cache the data
            self.cache[cache_key] = (data, time.time())
            
            logger.info(f"Successfully fetched {len(data)} candles for {pair} ({timeframe})")
            return data
            
        except Exception as e:
            logger.error(f"Error fetching data for {pair}: {e}")
            return pd.DataFrame()
    
    def resample_data(self, data, timeframe):
        """Resample data to different timeframe"""
        try:
            # Map resample strings
            resample_map = {
                '4h': '4H',
                '1d': '1D'
            }
            
            resample_str = resample_map.get(timeframe, '1H')
            
            resampled = data.resample(resample_str).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min', 
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            return resampled
            
        except Exception as e:
            logger.error(f"Error resampling data: {e}")
            return data
    
    def get_latest_price(self, pair):
        """Get the latest price for a currency pair"""
        try:
            yf_pair = pair.replace('/', '') + '=X'
            ticker = yf.Ticker(yf_pair)
            data = ticker.history(period='1d', interval='1m')
            
            if data.empty:
                return None
                
            latest_price = data['close'].iloc[-1]
            return latest_price
            
        except Exception as e:
            logger.error(f"Error getting latest price for {pair}: {e}")
            return None
    
    def get_multiple_pairs(self, pairs, timeframe='1h', period='7d'):
        """Get data for multiple currency pairs"""
        data_dict = {}
        
        for pair in pairs:
            data = self.get_forex_data(pair, timeframe, period)
            if not data.empty:
                data_dict[pair] = data
                
        return data_dict
    
    def validate_data(self, data):
        """Validate that data has required columns and no missing values"""
        required_columns = ['open', 'high', 'low', 'close']
        
        if data.empty:
            return False, "Data is empty"
            
        missing_cols = [col for col in required_columns if col not in data.columns]
        if missing_cols:
            return False, f"Missing columns: {missing_cols}"
            
        if data[required_columns].isnull().any().any():
            return False, "Data contains null values"
            
        return True, "Data is valid"
    
    def get_market_summary(self, pairs):
        """Get a summary of current market conditions"""
        summary = {}
        
        for pair in pairs:
            try:
                latest_price = self.get_latest_price(pair)
                daily_data = self.get_forex_data(pair, '1d', '5d')
                
                if not daily_data.empty and latest_price:
                    # Calculate daily change
                    prev_close = daily_data['close'].iloc[-2] if len(daily_data) > 1 else daily_data['close'].iloc[-1]
                    daily_change = (latest_price - prev_close) / prev_close * 100
                    
                    summary[pair] = {
                        'price': latest_price,
                        'daily_change': daily_change,
                        'trend': 'up' if daily_change > 0 else 'down' if daily_change < 0 else 'neutral'
                    }
                    
            except Exception as e:
                logger.error(f"Error getting summary for {pair}: {e}")
                summary[pair] = {'error': str(e)}
                
        return summary
