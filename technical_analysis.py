"""
Technical Analysis Module for BrayoForexBot
Implements various technical indicators and analysis functions
"""

import pandas as pd
import numpy as np
import talib
from config import Config
import logging

logger = logging.getLogger(__name__)

class TechnicalAnalysis:
    """Class for technical analysis calculations"""
    
    def __init__(self):
        self.rsi_period = Config.RSI_PERIOD
        self.rsi_oversold = Config.RSI_OVERSOLD
        self.rsi_overbought = Config.RSI_OVERBOUGHT
        self.ma_fast = Config.MA_FAST_PERIOD
        self.ma_slow = Config.MA_SLOW_PERIOD
        
    def calculate_rsi(self, data, period=None):
        """
        Calculate Relative Strength Index (RSI)
        
        Args:
            data (pd.Series): Price data (usually closing prices)
            period (int): RSI period (default from config)
            
        Returns:
            pd.Series: RSI values
        """
        try:
            if period is None:
                period = self.rsi_period
                
            rsi = talib.RSI(data.values, timeperiod=period)
            return pd.Series(rsi, index=data.index)
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return pd.Series(np.nan, index=data.index)
    
    def calculate_moving_averages(self, data, fast_period=None, slow_period=None):
        """
        Calculate Moving Averages (SMA)
        
        Args:
            data (pd.Series): Price data
            fast_period (int): Fast MA period
            slow_period (int): Slow MA period
            
        Returns:
            tuple: (fast_ma, slow_ma)
        """
        try:
            if fast_period is None:
                fast_period = self.ma_fast
            if slow_period is None:
                slow_period = self.ma_slow
                
            fast_ma = talib.SMA(data.values, timeperiod=fast_period)
            slow_ma = talib.SMA(data.values, timeperiod=slow_period)
            
            fast_ma = pd.Series(fast_ma, index=data.index)
            slow_ma = pd.Series(slow_ma, index=data.index)
            
            return fast_ma, slow_ma
            
        except Exception as e:
            logger.error(f"Error calculating moving averages: {e}")
            return pd.Series(np.nan, index=data.index), pd.Series(np.nan, index=data.index)
    
    def calculate_macd(self, data, fastperiod=12, slowperiod=26, signalperiod=9):
        """
        Calculate MACD (Moving Average Convergence Divergence)
        
        Args:
            data (pd.Series): Price data
            fastperiod (int): Fast EMA period
            slowperiod (int): Slow EMA period
            signalperiod (int): Signal line period
            
        Returns:
            tuple: (macd, signal, histogram)
        """
        try:
            macd, signal, histogram = talib.MACD(
                data.values, 
                fastperiod=fastperiod, 
                slowperiod=slowperiod, 
                signalperiod=signalperiod
            )
            
            macd = pd.Series(macd, index=data.index)
            signal = pd.Series(signal, index=data.index)
            histogram = pd.Series(histogram, index=data.index)
            
            return macd, signal, histogram
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            return (pd.Series(np.nan, index=data.index), 
                   pd.Series(np.nan, index=data.index),
                   pd.Series(np.nan, index=data.index))
    
    def calculate_bollinger_bands(self, data, period=20, std_dev=2):
        """
        Calculate Bollinger Bands
        
        Args:
            data (pd.Series): Price data
            period (int): Period for calculation
            std_dev (int): Standard deviations
            
        Returns:
            tuple: (upper_band, middle_band, lower_band)
        """
        try:
            upper_band, middle_band, lower_band = talib.BBANDS(
                data.values, 
                timeperiod=period, 
                nbdevup=std_dev, 
                nbdevdn=std_dev
            )
            
            upper_band = pd.Series(upper_band, index=data.index)
            middle_band = pd.Series(middle_band, index=data.index)
            lower_band = pd.Series(lower_band, index=data.index)
            
            return upper_band, middle_band, lower_band
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            return (pd.Series(np.nan, index=data.index),
                   pd.Series(np.nan, index=data.index),
                   pd.Series(np.nan, index=data.index))
    
    def calculate_stochastic(self, high, low, close, k_period=14, d_period=3):
        """
        Calculate Stochastic Oscillator
        
        Args:
            high (pd.Series): High prices
            low (pd.Series): Low prices
            close (pd.Series): Close prices
            k_period (int): %K period
            d_period (int): %D period
            
        Returns:
            tuple: (slowk, slowd)
        """
        try:
            slowk, slowd = talib.STOCH(
                high.values, 
                low.values, 
                close.values,
                fastk_period=k_period,
                slowk_period=d_period,
                slowd_period=d_period
            )
            
            slowk = pd.Series(slowk, index=close.index)
            slowd = pd.Series(slowd, index=close.index)
            
            return slowk, slowd
            
        except Exception as e:
            logger.error(f"Error calculating Stochastic: {e}")
            return pd.Series(np.nan, index=close.index), pd.Series(np.nan, index=close.index)
    
    def get_all_indicators(self, data):
        """
        Calculate all technical indicators for the given data
        
        Args:
            data (pd.DataFrame): OHLCV data
            
        Returns:
            pd.DataFrame: Data with all indicators added
        """
        try:
            df = data.copy()
            
            if 'close' not in df.columns:
                logger.error("Data must have 'close' column")
                return df
            
            # RSI
            df['rsi'] = self.calculate_rsi(df['close'])
            
            # Moving Averages
            df['ma_fast'], df['ma_slow'] = self.calculate_moving_averages(df['close'])
            
            # MACD
            macd, signal, histogram = self.calculate_macd(df['close'])
            df['macd'] = macd
            df['macd_signal'] = signal
            df['macd_histogram'] = histogram
            
            # Bollinger Bands
            upper_bb, middle_bb, lower_bb = self.calculate_bollinger_bands(df['close'])
            df['bb_upper'] = upper_bb
            df['bb_middle'] = middle_bb
            df['bb_lower'] = lower_bb
            
            # Stochastic
            if all(col in df.columns for col in ['high', 'low', 'close']):
                slowk, slowd = self.calculate_stochastic(df['high'], df['low'], df['close'])
                df['stoch_k'] = slowk
                df['stoch_d'] = slowd
            
            logger.info(f"Calculated {len(df.columns) - len(data.columns)} indicators")
            return df
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return data
    
    def analyze_signals(self, data):
        """
        Analyze technical indicators and generate trading signals
        
        Args:
            data (pd.DataFrame): Data with indicators
            
        Returns:
            dict: Trading signals and analysis
        """
        try:
            if data.empty:
                return {'signal': 'WAIT', 'strength': 0, 'reasons': []}
            
            latest = data.iloc[-1]
            previous = data.iloc[-2] if len(data) > 1 else latest
            
            signals = []
            reasons = []
            
            # RSI Analysis
            if pd.notna(latest.get('rsi')):
                if latest['rsi'] < self.rsi_oversold:
                    signals.append('BUY')
                    reasons.append(f"RSI oversold ({latest['rsi']:.2f})")
                elif latest['rsi'] > self.rsi_overbought:
                    signals.append('SELL')
                    reasons.append(f"RSI overbought ({latest['rsi']:.2f})")
            
            # Moving Average Crossover
            if all(pd.notna(latest.get(col)) for col in ['ma_fast', 'ma_slow']):
                if (latest['ma_fast'] > latest['ma_slow'] and 
                    previous['ma_fast'] <= previous['ma_slow']):
                    signals.append('BUY')
                    reasons.append("MA bullish crossover")
                elif (latest['ma_fast'] < latest['ma_slow'] and 
                      previous['ma_fast'] >= previous['ma_slow']):
                    signals.append('SELL')
                    reasons.append("MA bearish crossover")
            
            # MACD Analysis
            if all(pd.notna(latest.get(col)) for col in ['macd', 'macd_signal']):
                if (latest['macd'] > latest['macd_signal'] and 
                    previous['macd'] <= previous['macd_signal']):
                    signals.append('BUY')
                    reasons.append("MACD bullish crossover")
                elif (latest['macd'] < latest['macd_signal'] and 
                      previous['macd'] >= previous['macd_signal']):
                    signals.append('SELL')
                    reasons.append("MACD bearish crossover")
            
            # Bollinger Bands
            if all(pd.notna(latest.get(col)) for col in ['bb_upper', 'bb_lower', 'close']):
                if latest['close'] < latest['bb_lower']:
                    signals.append('BUY')
                    reasons.append("Price below lower Bollinger Band")
                elif latest['close'] > latest['bb_upper']:
                    signals.append('SELL')
                    reasons.append("Price above upper Bollinger Band")
            
            # Determine final signal
            if not signals:
                final_signal = 'WAIT'
                strength = 0
            elif signals.count('BUY') > signals.count('SELL'):
                final_signal = 'BUY'
                strength = signals.count('BUY') / len(signals) * 100
            elif signals.count('SELL') > signals.count('BUY'):
                final_signal = 'SELL'
                strength = signals.count('SELL') / len(signals) * 100
            else:
                final_signal = 'WAIT'
                strength = 50
            
            return {
                'signal': final_signal,
                'strength': strength,
                'reasons': reasons,
                'all_signals': signals
            }
            
        except Exception as e:
            logger.error(f"Error analyzing signals: {e}")
            return {'signal': 'WAIT', 'strength': 0, 'reasons': [f"Error: {str(e)}"]}
