"""
Technical Analysis Module for BrayoForexBot
Implements various technical indicators and analysis functions
"""

import pandas as pd
import numpy as np
import talib
import logging

# Import Config with fallback
try:
    from config import Config
except ImportError:
    logging.warning("Config module not found, using default values")
    class Config:
        RSI_PERIOD = 14
        RSI_OVERSOLD = 30
        RSI_OVERBOUGHT = 70
        MA_FAST_PERIOD = 20
        MA_SLOW_PERIOD = 50

logger = logging.getLogger(__name__)

class TechnicalAnalysis:
    """Class for technical analysis calculations"""
    
    def __init__(self):
        self.rsi_period = Config.RSI_PERIOD
        self.rsi_oversold = Config.RSI_OVERSOLD
        self.rsi_overbought = Config.RSI_OVERBOUGHT
        self.ma_fast = Config.MA_FAST_PERIOD
        self.ma_slow = Config.MA_SLOW_PERIOD
        
        # Signal stability tracking
        self.last_signals = {}  # Track last signals per symbol
        self.signal_counts = {}  # Count consecutive signals
        self.max_signal_history = 5  # Track last 5 signals
        
    def check_signal_stability(self, symbol, signal):
        """
        Check signal stability to prevent rapid flipping
        
        Args:
            symbol (str): Currency pair symbol
            signal (str): Current signal
            
        Returns:
            dict: {'stable': bool, 'reason': str, 'required_confirmation': bool}
        """
        try:
            # Initialize tracking for symbol if not exists
            if symbol not in self.last_signals:
                self.last_signals[symbol] = []
                self.signal_counts[symbol] = {'BUY': 0, 'SELL': 0, 'WAIT': 0}
            
            # Add current signal to history
            self.last_signals[symbol].append(signal)
            
            # Keep only last N signals
            if len(self.last_signals[symbol]) > self.max_signal_history:
                self.last_signals[symbol] = self.last_signals[symbol][-self.max_signal_history:]
            
            # Count consecutive signals
            recent_signals = self.last_signals[symbol][-3:]  # Last 3 signals
            
            buy_count = recent_signals.count('BUY')
            sell_count = recent_signals.count('SELL')
            
            # Signal stability logic
            if signal == 'BUY':
                self.signal_counts[symbol]['BUY'] += 1
                self.signal_counts[symbol]['SELL'] = 0
                self.signal_counts[symbol]['WAIT'] = 0
                
                # Need 2+ BUY signals in last 3 to be stable
                if buy_count >= 2:
                    return {
                        'stable': True,
                        'reason': f'Stable BUY signal (confirmed {buy_count}/3 times)',
                        'required_confirmation': False
                    }
                else:
                    return {
                        'stable': False,
                        'reason': f'Unstable BUY signal (only {buy_count}/3 confirmations)',
                        'required_confirmation': True
                    }
                    
            elif signal == 'SELL':
                self.signal_counts[symbol]['SELL'] += 1
                self.signal_counts[symbol]['BUY'] = 0
                self.signal_counts[symbol]['WAIT'] = 0
                
                # Need 2+ SELL signals in last 3 to be stable
                if sell_count >= 2:
                    return {
                        'stable': True,
                        'reason': f'Stable SELL signal (confirmed {sell_count}/3 times)',
                        'required_confirmation': False
                    }
                else:
                    return {
                        'stable': False,
                        'reason': f'Unstable SELL signal (only {sell_count}/3 confirmations)',
                        'required_confirmation': True
                    }
                    
            else:  # WAIT signal
                self.signal_counts[symbol]['WAIT'] += 1
                return {
                    'stable': True,
                    'reason': 'WAIT signal - no trade',
                    'required_confirmation': False
                }
                
        except Exception as e:
            logger.error(f"Error checking signal stability: {e}")
            return {
                'stable': True,
                'reason': 'Error in stability check - allowing by default',
                'required_confirmation': False
            }
    
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
            data (pd.DataFrame): Price data with OHLCV
            
        Returns:
            dict: {'signal': 'BUY'/'SELL'/'WAIT', 'strength': 0-100, 'reasons': list}
        """
        try:
            if len(data) < 20:
                return {'signal': 'WAIT', 'strength': 0, 'reasons': ['Insufficient data']}
            
            latest = data.iloc[-1]
            prev = data.iloc[-2]
            
            signals = []
            reasons = []
            
            # 1. HIGHER HIGHS/LOWER LOWS ANALYSIS (Base signal generation)
            # Check if price is making higher highs (potential BUY)
            if len(data) >= 10:
                recent_highs = data['high'].tail(10)
                recent_lows = data['low'].tail(10)
                
                # Higher highs detection
                if latest['high'] > recent_highs.iloc[-2:].max():
                    signals.append('BUY')
                    reasons.append(f"Making higher highs (latest: {latest['high']:.5f})")
                
                # Lower lows detection  
                if latest['low'] < recent_lows.iloc[-2:].min():
                    signals.append('SELL')
                    reasons.append(f"Making lower lows (latest: {latest['low']:.5f})")
            
            # 2. MOMENTUM ANALYSIS
            if len(data) >= 5:
                recent_closes = data['close'].tail(5)
                
                # Upward momentum
                if all(recent_closes.iloc[i] > recent_closes.iloc[i-1] for i in range(1, min(4, len(recent_closes)))):
                    signals.append('BUY')
                    reasons.append("Strong upward momentum")
                elif recent_closes.iloc[-1] > recent_closes.iloc[-2]:
                    signals.append('BUY')
                    reasons.append("Upward momentum")
                
                # Downward momentum
                if all(recent_closes.iloc[i] < recent_closes.iloc[i-1] for i in range(1, min(4, len(recent_closes)))):
                    signals.append('SELL')
                    reasons.append("Strong downward momentum")
                elif recent_closes.iloc[-1] < recent_closes.iloc[-2]:
                    signals.append('SELL')
                    reasons.append("Downward momentum")
            
            # 3. RSI ANALYSIS (for overbought/oversold)
            if 'rsi' in data.columns and pd.notna(latest.get('rsi')):
                if latest['rsi'] < self.rsi_oversold:
                    signals.append('BUY')
                    reasons.append(f"RSI oversold ({latest['rsi']:.2f})")
                elif latest['rsi'] > self.rsi_overbought:
                    signals.append('SELL')
                    reasons.append(f"RSI overbought ({latest['rsi']:.2f})")
            
            # 4. MOVING AVERAGE CROSSOVER
            # NOTE: get_all_indicators() creates columns named 'ma_fast'/'ma_slow'
            # (see calculate_moving_averages above), not 'sma_fast'/'sma_slow'.
            # This mismatch meant this signal component never fired for any
            # data produced by get_all_indicators().
            if 'ma_fast' in data.columns and 'ma_slow' in data.columns:
                if pd.notna(latest.get('ma_fast')) and pd.notna(latest.get('ma_slow')):
                    prev_sma_fast = data['ma_fast'].iloc[-2]
                    prev_sma_slow = data['ma_slow'].iloc[-2]
                    
                    # Golden cross (BUY signal)
                    if (prev_sma_fast <= prev_sma_slow and 
                        latest['ma_fast'] > latest['ma_slow']):
                        signals.append('BUY')
                        reasons.append("Golden cross (Fast MA above Slow MA)")
                    
                    # Death cross (SELL signal)
                    elif (prev_sma_fast >= prev_sma_slow and 
                          latest['ma_fast'] < latest['ma_slow']):
                        signals.append('SELL')
                        reasons.append("Death cross (Fast MA below Slow MA)")
            
            # 5. MACD CROSSOVER
            if 'macd' in data.columns and 'macd_signal' in data.columns:
                if pd.notna(latest.get('macd')) and pd.notna(latest.get('macd_signal')):
                    prev_macd = data['macd'].iloc[-2]
                    prev_signal = data['macd_signal'].iloc[-2]
                    
                    # MACD bullish crossover
                    if (prev_macd <= prev_signal and 
                        latest['macd'] > latest['macd_signal']):
                        signals.append('BUY')
                        reasons.append("MACD bullish crossover")
                    
                    # MACD bearish crossover
                    elif (prev_macd >= prev_signal and 
                          latest['macd'] < latest['macd_signal']):
                        signals.append('SELL')
                        reasons.append("MACD bearish crossover")
            
            # DETERMINE FINAL SIGNAL
            if not signals:
                # If no clear signals, check for weak directional movement
                if len(data) >= 3:
                    price_change = (latest['close'] - data['close'].iloc[-3]) / data['close'].iloc[-3] * 100
                    
                    if price_change > 0.3:  # Small upward movement
                        final_signal = 'WEAK BUY'
                        signal_strength = 25
                        reasons.append(f"Weak upward movement ({price_change:.2f}%)")
                    elif price_change < -0.3:  # Small downward movement
                        final_signal = 'WEAK SELL'
                        signal_strength = 25
                        reasons.append(f"Weak downward movement ({price_change:.2f}%)")
                    else:
                        final_signal = 'WAIT'
                        signal_strength = 0
                        reasons.append("No clear directional movement")
                else:
                    final_signal = 'WAIT'
                    signal_strength = 0
                    reasons.append("Insufficient data for analysis")
            else:
                # Count signal types
                buy_signals = signals.count('BUY')
                sell_signals = signals.count('SELL')
                
                if buy_signals > sell_signals:
                    final_signal = 'BUY'
                    signal_strength = min((buy_signals / len(signals)) * 100, 85)
                elif sell_signals > buy_signals:
                    final_signal = 'SELL'
                    signal_strength = min((sell_signals / len(signals)) * 100, 85)
                else:
                    # Equal signals - use momentum as tiebreaker
                    if len(data) >= 5:
                        recent_closes = data['close'].tail(3)
                        if recent_closes.iloc[-1] > recent_closes.iloc[-2]:
                            final_signal = 'BUY'
                            signal_strength = 40
                        else:
                            final_signal = 'SELL'
                            signal_strength = 40
                    else:
                        final_signal = 'WAIT'
                        signal_strength = 0
            
            logger.debug(f"Basic Signal Analysis:")
            logger.debug(f"  Final Signal: {final_signal}")
            logger.debug(f"  Signal Strength: {signal_strength:.0f}%")
            logger.debug(f"  Reasons: {reasons[:3]}")
            
            return {
                'signal': final_signal,
                'strength': signal_strength,
                'reasons': reasons,
                'all_signals': signals
            }
            
        except Exception as e:
            logger.error(f"Error analyzing signals: {e}")
            return {'signal': 'WAIT', 'strength': 0, 'reasons': ['Analysis error'], 'all_signals': []}
    
    def calculate_volume_profile(self, data, num_bins=24, value_area_pct=0.70):
        """
        Volume Profile / Point of Control (PoC) / Value Area, computed
        purely from OHLCV data already available - no external data needed.

        Real, well-established technique (from Market Profile theory,
        originated at the CBOT in the 1980s): bucket traded volume by price
        level across a window, rather than just by time. The price level
        with the most volume is the PoC - a level the market spent the most
        "effort" at, which often acts as a magnet/reaction zone when price
        returns to it. Value Area is the price band containing
        value_area_pct (conventionally 70%) of the window's total volume,
        centered on the PoC.

        Caveat worth knowing: MT5's 'volume' column here is tick volume
        (count of price changes), not true transacted volume - retail
        forex/CFD brokers don't have visibility into real market-wide
        volume the way a regulated futures exchange does. It's a reasonable
        proxy, especially for a heavily-traded symbol like gold during
        liquid sessions, but it's not the same rigor as Volume Profile
        computed on real CME Gold futures volume.

        This assigns each candle's full volume to the bin containing its
        typical price ((high+low+close)/3) - a standard simplification;
        true Volume Profile tools distribute each candle's volume across
        every bin its range touches, which gives a smoother profile but
        needs tick-level or much finer OHLC data than a bot polling every
        minute realistically has.

        Args:
            data: OHLCV DataFrame window representing the range/session to
                  profile (e.g. the current day's candles, or a detected
                  consolidation range)
            num_bins: number of price buckets to divide the window's
                      high-low range into
            value_area_pct: fraction of total volume the value area should
                             contain (0.70 is the conventional default)

        Returns:
            dict with poc_price, value_area_high, value_area_low,
            current_vs_poc ('ABOVE'/'AT'/'BELOW'), distance_to_poc_pct
        """
        try:
            if data is None or len(data) < 5 or 'volume' not in data.columns:
                return {'available': False}

            price_low = data['low'].min()
            price_high = data['high'].max()
            if price_high <= price_low:
                return {'available': False}

            bin_edges = np.linspace(price_low, price_high, num_bins + 1)
            bin_volumes = np.zeros(num_bins)

            typical_price = (data['high'] + data['low'] + data['close']) / 3
            bin_indices = np.clip(
                np.digitize(typical_price, bin_edges) - 1, 0, num_bins - 1
            )
            for idx, vol in zip(bin_indices, data['volume']):
                bin_volumes[idx] += vol

            total_volume = bin_volumes.sum()
            if total_volume <= 0:
                return {'available': False}

            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
            poc_idx = int(np.argmax(bin_volumes))
            poc_price = bin_centers[poc_idx]

            # Expand outward from the PoC bin until value_area_pct of total
            # volume is captured - the standard Value Area construction.
            included = {poc_idx}
            accumulated = bin_volumes[poc_idx]
            low_idx, high_idx = poc_idx, poc_idx
            while accumulated < total_volume * value_area_pct and (low_idx > 0 or high_idx < num_bins - 1):
                vol_below = bin_volumes[low_idx - 1] if low_idx > 0 else -1
                vol_above = bin_volumes[high_idx + 1] if high_idx < num_bins - 1 else -1
                if vol_above >= vol_below:
                    high_idx += 1
                    accumulated += bin_volumes[high_idx]
                    included.add(high_idx)
                else:
                    low_idx -= 1
                    accumulated += bin_volumes[low_idx]
                    included.add(low_idx)

            value_area_high = bin_centers[high_idx]
            value_area_low = bin_centers[low_idx]

            current_price = data['close'].iloc[-1]
            if current_price > poc_price * 1.0005:
                current_vs_poc = 'ABOVE'
            elif current_price < poc_price * 0.9995:
                current_vs_poc = 'BELOW'
            else:
                current_vs_poc = 'AT'
            distance_to_poc_pct = abs(current_price - poc_price) / poc_price * 100

            return {
                'available': True,
                'poc_price': round(poc_price, 2),
                'value_area_high': round(value_area_high, 2),
                'value_area_low': round(value_area_low, 2),
                'current_vs_poc': current_vs_poc,
                'distance_to_poc_pct': round(distance_to_poc_pct, 3),
            }
        except Exception as e:
            logger.debug(f"Volume profile calculation unavailable: {e}")
            return {'available': False}

    def calculate_vwap(self, data, std_multiplier=2.0):
        """
        Session VWAP (Volume Weighted Average Price) with standard
        deviation bands, computed purely from OHLCV data already available.

        VWAP is arguably the single most-watched institutional benchmark
        for intraday levels - more fundamental than Volume Profile to many
        desks, since it's literally the volume-weighted average price paid
        across the window, and is used both as a fair-value reference and
        a mean-reversion anchor. Research directly supports combining this
        with the PoC above: when a Volume Profile PoC and VWAP sit close
        together, that confluence is considered a stronger reaction zone
        than either alone - this does NOT compute that confluence itself,
        that comparison happens where both are used together.

        Same tick-volume caveat as calculate_volume_profile() applies here.

        Args:
            data: OHLCV DataFrame window representing the session to
                  compute VWAP over (VWAP is meant to reset per session -
                  pass in just the current session's candles, not an
                  arbitrary multi-day window, or the "session" framing
                  stops being meaningful)
            std_multiplier: how many standard deviations the outer bands
                             sit from VWAP (2.0 is a common default)

        Returns:
            dict with vwap, upper_band, lower_band, current_vs_vwap
            ('ABOVE'/'AT'/'BELOW'), distance_to_vwap_pct
        """
        try:
            if data is None or len(data) < 5 or 'volume' not in data.columns:
                return {'available': False}

            typical_price = (data['high'] + data['low'] + data['close']) / 3
            volume = data['volume']
            total_volume = volume.sum()
            if total_volume <= 0:
                return {'available': False}

            vwap = (typical_price * volume).sum() / total_volume

            variance = ((typical_price - vwap) ** 2 * volume).sum() / total_volume
            std_dev = variance ** 0.5

            upper_band = vwap + std_multiplier * std_dev
            lower_band = vwap - std_multiplier * std_dev

            current_price = data['close'].iloc[-1]
            if current_price > vwap * 1.0005:
                current_vs_vwap = 'ABOVE'
            elif current_price < vwap * 0.9995:
                current_vs_vwap = 'BELOW'
            else:
                current_vs_vwap = 'AT'
            distance_to_vwap_pct = abs(current_price - vwap) / vwap * 100

            return {
                'available': True,
                'vwap': round(vwap, 2),
                'upper_band': round(upper_band, 2),
                'lower_band': round(lower_band, 2),
                'current_vs_vwap': current_vs_vwap,
                'distance_to_vwap_pct': round(distance_to_vwap_pct, 3),
            }
        except Exception as e:
            logger.debug(f"VWAP calculation unavailable: {e}")
            return {'available': False}

    def check_dollar_correlation(self, mt5_connector, as_of=None):
        """
        Check USD strength via EURUSD as a proxy, and how it relates to a
        gold trade direction.

        This does NOT exist to block trades - it's a diagnostic factor,
        logged into analysis_result['factors']['dollar_correlation'] but
        never touching trade_blocked or confidence. Gold is well-documented
        as inversely correlated with dollar strength (a strengthening dollar
        is generally a headwind for gold, and vice versa); EURUSD is used as
        the proxy since it's the most liquid pair and moves largely opposite
        to broad dollar strength, and because MT5's Market Watch here almost
        certainly already has it from this bot's pre-Gold-pivot life as a
        10-pair forex bot, unlike a dedicated DXY/USDX symbol which not every
        broker lists.

        This is new, unvalidated logic - it hasn't been through the
        backtesting discipline the rest of this system has, and the right
        next step before ever making it a hard filter is extending
        run_gold_backtest.py to pull EURUSD alongside XAUUSD and measure
        whether "aligned" trades actually outperform "conflicting" ones.
        Guessing at that from live logs alone risks exactly the kind of
        unvalidated assumption this whole project has worked to avoid.

        Returns:
            dict: {'usd_trend': 'BULLISH'/'BEARISH'/'SIDEWAYS', 'available': bool}
        """
        try:
            from datetime import datetime, timedelta
            end_date = as_of if as_of is not None else datetime.now()
            start_date = end_date - timedelta(days=100)

            eurusd_data = mt5_connector.get_historical_data(
                symbol='EURUSD',
                timeframe='H4',
                start_date=start_date,
                end_date=end_date
            )

            if eurusd_data is None or 'error' in eurusd_data or len(eurusd_data) < 50:
                return {'usd_trend': 'UNKNOWN', 'available': False}

            ema50 = talib.EMA(eurusd_data['close'].values, timeperiod=50)
            ema200 = talib.EMA(eurusd_data['close'].values, timeperiod=200)
            current_price = eurusd_data['close'].iloc[-1]

            if current_price > ema50[-1] > ema200[-1]:
                eurusd_trend = 'BULLISH'  # EUR strengthening = USD weakening
            elif current_price < ema50[-1] < ema200[-1]:
                eurusd_trend = 'BEARISH'  # EUR weakening = USD strengthening
            else:
                eurusd_trend = 'SIDEWAYS'

            # USD trend is roughly the inverse of EURUSD's trend
            usd_trend = {'BULLISH': 'BEARISH', 'BEARISH': 'BULLISH', 'SIDEWAYS': 'SIDEWAYS'}[eurusd_trend]

            return {'usd_trend': usd_trend, 'available': True}

        except Exception as e:
            logger.debug(f"Dollar correlation check unavailable: {e}")
            return {'usd_trend': 'UNKNOWN', 'available': False}

    def analyze_higher_timeframe_trend(self, mt5_connector, symbol, current_timeframe='M15', as_of=None):
        """
        Analyze trend on higher timeframe using proper EMA logic
        
        Args:
            mt5_connector: MT5 connector instance
            symbol (str): Currency pair symbol
            current_timeframe (str): Current timeframe for reference
            as_of (datetime, optional): Treat this as "now" instead of the real
                current time. Required for backtesting - without it, this
                method would fetch TODAY's real H4 trend for every historical
                decision being simulated (look-ahead bias), regardless of what
                point in history the backtest is actually evaluating. Live
                trading is unaffected: as_of=None still means "use real now".
            
        Returns:
            dict: {'trend': 'BULLISH'/'BEARISH'/'SIDEWAYS', 'strength': 0-100}
        """
        try:
            # Always use H1 or H4 for trend analysis (not M5/M15)
            if current_timeframe in ['M1', 'M5', 'M15', 'M30']:
                htf_timeframe = 'H4'  # Use H4 for trend confirmation
                htf_period = 100  # 100 periods of H4 data
            else:  # H1, H4
                htf_timeframe = 'D1'  # Use D1 for higher timeframe
                htf_period = 50   # 50 periods of D1 data
            
            # Get higher timeframe data
            from datetime import datetime, timedelta
            end_date = as_of if as_of is not None else datetime.now()
            start_date = end_date - timedelta(days=htf_period * 2)
            
            htf_data = mt5_connector.get_historical_data(
                symbol=symbol,
                timeframe=htf_timeframe,
                start_date=start_date,
                end_date=end_date
            )
            
            if htf_data is None or 'error' in htf_data or len(htf_data) < 50:
                return {'trend': 'SIDEWAYS', 'strength': 0}
            
            # Calculate EMAs for proper trend analysis
            htf_ema50 = talib.EMA(htf_data['close'].values, timeperiod=50)
            htf_ema200 = talib.EMA(htf_data['close'].values, timeperiod=200)
            
            # Get latest values
            current_price = htf_data['close'].iloc[-1]
            latest_ema50 = htf_ema50[-1]
            latest_ema200 = htf_ema200[-1]
            
            # Debug logging
            logger.debug(f"HTF Analysis for {symbol} {htf_timeframe}:")
            logger.debug(f"  Current Price: {current_price:.5f}")
            logger.debug(f"  EMA50: {latest_ema50:.5f}")
            logger.debug(f"  EMA200: {latest_ema200:.5f}")
            
            # Determine trend using EMA logic
            if current_price > latest_ema50 and latest_ema50 > latest_ema200:
                trend = 'BULLISH'
                # Calculate strength based on how far above EMAs
                distance_ema50 = (current_price - latest_ema50) / latest_ema50 * 100
                distance_ema200 = (current_price - latest_ema200) / latest_ema200 * 100
                strength = min(50 + distance_ema50 * 10 + distance_ema200 * 5, 85)
                
            elif current_price < latest_ema50 and latest_ema50 < latest_ema200:
                trend = 'BEARISH'
                # Calculate strength based on how far below EMAs
                distance_ema50 = (latest_ema50 - current_price) / latest_ema50 * 100
                distance_ema200 = (latest_ema200 - current_price) / latest_ema200 * 100
                strength = min(50 + distance_ema50 * 10 + distance_ema200 * 5, 85)
                
            else:
                trend = 'SIDEWAYS'
                # Give sideways some strength based on price position
                if abs(current_price - latest_ema50) / latest_ema50 * 100 < 0.5:
                    strength = 25  # Price is near EMA50
                else:
                    strength = 35  # Price is between EMAs
            
            logger.debug(f"  Trend: {trend} (strength: {strength:.0f})")
            
            return {
                'trend': trend,
                'strength': strength,
                'timeframe': htf_timeframe,
                'ema50': latest_ema50,
                'ema200': latest_ema200,
                'current_price': current_price
            }
            
        except Exception as e:
            logger.error(f"Error analyzing higher timeframe trend: {e}")
            return {'trend': 'SIDEWAYS', 'strength': 0}
    
    def detect_market_condition(self, data):
        """
        Detect if market is trending or ranging using ATR and volatility
        
        Args:
            data (pd.DataFrame): Price data with OHLC
            
        Returns:
            dict: {'condition': 'TRENDING'/'RANGING'/'VOLATILE', 'atr': value, 'volatility': value}
        """
        try:
            if len(data) < 50:
                return {'condition': 'RANGING', 'atr': 0, 'volatility': 0}
            
            # Calculate ATR for volatility measurement
            atr = talib.ATR(data['high'].values, data['low'].values, data['close'].values, timeperiod=14)
            latest_atr = atr[-1]
            
            # Calculate price range over last 20 periods
            high_20 = data['high'].rolling(20).max()
            low_20 = data['low'].rolling(20).min()
            price_range = (high_20.iloc[-1] - low_20.iloc[-1]) / data['close'].iloc[-1] * 100
            
            # Calculate volatility (standard deviation of returns)
            returns = data['close'].pct_change().dropna()
            volatility = returns.rolling(20).std().iloc[-1] * 100
            
            # ATR as percentage of price
            atr_percentage = (latest_atr / data['close'].iloc[-1]) * 100
            
            # Enhanced market condition logic
            if atr_percentage > 0.5 or volatility > 3.0:
                condition = 'VOLATILE'
            elif price_range > 2.0 and atr_percentage > 0.2:
                condition = 'TRENDING'
            elif atr_percentage < 0.08 and volatility < 1.0:
                condition = 'RANGING'  # Only classify as ranging if very low volatility
            else:
                condition = 'ACTIVE'  # Normal market conditions
            
            logger.debug(f"Market Condition: {condition}")
            logger.debug(f"  ATR: {latest_atr:.5f} ({atr_percentage:.2f}%)")
            logger.debug(f"  Volatility: {volatility:.2f}%")
            logger.debug(f"  Price Range: {price_range:.2f}%")
            
            return {
                'condition': condition,
                'atr': latest_atr,
                'atr_percent': atr_percentage,
                'volatility': volatility,
                'price_range': price_range
            }
            
        except Exception as e:
            logger.error(f"Error detecting market condition: {e}")
            return {'condition': 'ACTIVE', 'atr': 0, 'volatility': 0}
    
    def find_structure_levels(self, data, lookback=20):
        """
        Find swing highs and swing lows for structure-based stop loss
        
        Args:
            data (pd.DataFrame): Price data with OHLC
            lookback (int): Number of periods to look back
            
        Returns:
            dict: {'swing_highs': [prices], 'swing_lows': [prices], 'recent_high': price, 'recent_low': price}
        """
        try:
            if len(data) < lookback + 5:
                return {'swing_highs': [], 'swing_lows': [], 'recent_high': 0, 'recent_low': 0}
            
            swing_highs = []
            swing_lows = []
            
            # Find swing highs (price higher than previous and next 2 candles)
            for i in range(2, len(data) - 2):
                if (data['high'].iloc[i] > data['high'].iloc[i-1] and 
                    data['high'].iloc[i] > data['high'].iloc[i-2] and
                    data['high'].iloc[i] > data['high'].iloc[i+1] and
                    data['high'].iloc[i] > data['high'].iloc[i+2]):
                    swing_highs.append(data['high'].iloc[i])
                
                # Find swing lows
                if (data['low'].iloc[i] < data['low'].iloc[i-1] and 
                    data['low'].iloc[i] < data['low'].iloc[i-2] and
                    data['low'].iloc[i] < data['low'].iloc[i+1] and
                    data['low'].iloc[i] < data['low'].iloc[i+2]):
                    swing_lows.append(data['low'].iloc[i])
            
            # Get recent swing levels (within lookback period)
            recent_data = data.tail(lookback)
            recent_high = recent_data['high'].max()
            recent_low = recent_data['low'].min()
            
            return {
                'swing_highs': swing_highs[-5:],  # Last 5 swing highs
                'swing_lows': swing_lows[-5:],    # Last 5 swing lows
                'recent_high': recent_high,
                'recent_low': recent_low
            }
            
        except Exception as e:
            logger.error(f"Error finding structure levels: {e}")
            return {'swing_highs': [], 'swing_lows': [], 'recent_high': 0, 'recent_low': 0}
    
    def calculate_risk_reward(self, entry_price, stop_loss, take_profit):
        """
        Calculate risk:reward ratio
        
        Args:
            entry_price (float): Entry price
            stop_loss (float): Stop loss price
            take_profit (float): Take profit price
            
        Returns:
            dict: {'risk_pips': float, 'reward_pips': float, 'ratio': float, 'valid': bool}
        """
        try:
            risk = abs(entry_price - stop_loss)
            reward = abs(take_profit - entry_price)
            
            if risk == 0:
                return {'risk_pips': 0, 'reward_pips': 0, 'ratio': 0, 'valid': False}
            
            ratio = reward / risk
            
            return {
                'risk_pips': risk * 10000,  # Convert to pips
                'reward_pips': reward * 10000,
                'ratio': ratio,
                'valid': ratio >= 2.0  # Minimum 1:2 risk:reward
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk:reward: {e}")
            return {'risk_pips': 0, 'reward_pips': 0, 'ratio': 0, 'valid': False}
    
    def check_entry_confirmation(self, data, signal_type, lookback=5):
        """
        Check for entry confirmation (relaxed - accepts single strong confirmation)
        
        Args:
            data (pd.DataFrame): Price data
            signal_type (str): 'BUY' or 'SELL'
            lookback (int): Periods to look back for confirmation
            
        Returns:
            dict: {'confirmed': bool, 'strength': 0-100, 'reasons': list}
        """
        try:
            if len(data) < lookback + 2:
                return {'confirmed': False, 'strength': 0, 'reasons': ['Insufficient data']}
            
            latest = data.iloc[-1]
            prev = data.iloc[-2]
            
            confirmations = []
            strength_total = 0
            
            # 1. Strong candle close (most important)
            if signal_type == 'BUY':
                if latest['close'] > latest['open'] and latest['close'] > prev['high']:
                    confirmations.append('Strong bullish candle closing above previous high')
                    strength_total += 40
                elif latest['close'] > latest['open']:
                    confirmations.append('Bullish candle')
                    strength_total += 20
            else:  # SELL
                if latest['close'] < latest['open'] and latest['close'] < prev['low']:
                    confirmations.append('Strong bearish candle closing below previous low')
                    strength_total += 40
                elif latest['close'] < latest['open']:
                    confirmations.append('Bearish candle')
                    strength_total += 20
            
            # 2. Structure break (important)
            structure_levels = self.find_structure_levels(data, lookback=10)
            
            if signal_type == 'BUY':
                if latest['close'] > structure_levels['recent_high']:
                    confirmations.append('Break of recent high')
                    strength_total += 35
                elif latest['high'] > structure_levels['recent_high']:
                    confirmations.append('Test of recent high')
                    strength_total += 15
            else:  # SELL
                if latest['close'] < structure_levels['recent_low']:
                    confirmations.append('Break of recent low')
                    strength_total += 35
                elif latest['low'] < structure_levels['recent_low']:
                    confirmations.append('Test of recent low')
                    strength_total += 15
            
            # 3. Volume confirmation (if available)
            if 'volume' in data.columns:
                avg_volume = data['volume'].rolling(10).mean().iloc[-1]
                if latest['volume'] > avg_volume * 1.2:
                    confirmations.append('High volume confirmation')
                    strength_total += 25
                elif latest['volume'] > avg_volume:
                    confirmations.append('Above average volume')
                    strength_total += 10
            
            # 4. Momentum confirmation
            if len(data) >= 5:
                recent_closes = data['close'].tail(5)
                if signal_type == 'BUY':
                    if all(recent_closes.iloc[i] > recent_closes.iloc[i-1] for i in range(1, len(recent_closes))):
                        confirmations.append('Strong upward momentum')
                        strength_total += 30
                    elif recent_closes.iloc[-1] > recent_closes.iloc[-2]:
                        confirmations.append('Upward momentum')
                        strength_total += 15
                else:  # SELL
                    if all(recent_closes.iloc[i] < recent_closes.iloc[i-1] for i in range(1, len(recent_closes))):
                        confirmations.append('Strong downward momentum')
                        strength_total += 30
                    elif recent_closes.iloc[-1] < recent_closes.iloc[-2]:
                        confirmations.append('Downward momentum')
                        strength_total += 15
            
            # Calculate final confirmation
            confirmed = len(confirmations) >= 1 and strength_total >= 30  # Only need ONE strong confirmation
            strength = min(strength_total, 100)
            
            return {
                'confirmed': confirmed,
                'strength': strength,
                'confirmations': confirmations,
                'reasons': confirmations
            }
            
        except Exception as e:
            logger.error(f"Error checking entry confirmation: {e}")
            return {'confirmed': False, 'strength': 0, 'reasons': ['Error in confirmation check']}
    
    def _create_safe_fallback_result(self, reason):
        """Create safe fallback result to prevent crashes"""
        return {
            'signal': 'WAIT',
            'confidence': 0,
            'market_state': 'UNKNOWN',
            'htf_trend': 'SIDEWAYS',
            'trade_blocked': True,
            'block_reason': reason,
            'entry_confirmed': False,
            'risk_reward': {'valid': False, 'ratio': 0},
            'structure_sl': 0,
            'structure_tp': 0,
            'reasons': [f'Analysis fallback: {reason}'],
            'factors': {
                'atr_percent': 0.1,  # Safe fallback
                'volatility': 1.0,    # Safe fallback
                'market_condition': 'UNKNOWN'
            },
            'trade_score': 0
        }
    
    def _validate_market_condition_data(self, market_condition):
        """Validate and fix market condition data structure"""
        if not isinstance(market_condition, dict):
            logger.warning("Market condition is not a dict - using fallback")
            return {
                'condition': 'ACTIVE',
                'atr': 0.001,
                'atr_percent': 0.1,
                'volatility': 1.0,
                'price_range': 1.0
            }
        
        # Ensure required keys exist
        required_keys = {
            'condition': 'ACTIVE',
            'atr': 0.001,
            'atr_percent': 0.1,
            'volatility': 1.0,
            'price_range': 1.0
        }
        
        for key, default_value in required_keys.items():
            if key not in market_condition:
                logger.warning(f"Missing market condition key '{key}' - using fallback {default_value}")
                market_condition[key] = default_value
        
        return market_condition

    def advanced_signal_analysis(self, mt5_connector, data, symbol, timeframe='H1', as_of=None):
        """
        Comprehensive signal analysis with all professional factors
        
        Args:
            mt5_connector: MT5 connector instance
            data (pd.DataFrame): Price data
            symbol (str): Currency pair symbol
            timeframe (str): Current timeframe
            as_of (datetime, optional): Backtesting support - see
                analyze_higher_timeframe_trend for why this matters.
            
        Returns:
            dict: Comprehensive signal analysis with all factors
        """
        try:
            # Input validation
            if data is None or len(data) < 50:
                logger.warning(f"Insufficient data for {symbol} {timeframe}")
                return self._create_safe_fallback_result("Insufficient data")
            
            # Validate required columns
            required_columns = ['open', 'high', 'low', 'close']
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                logger.error(f"Missing columns for {symbol} {timeframe}: {missing_columns}")
                return self._create_safe_fallback_result(f"Missing data columns: {missing_columns}")
            
            analysis_result = {
                'signal': 'WAIT',
                'confidence': 0,
                'market_state': 'UNKNOWN',
                'htf_trend': 'SIDEWAYS',
                'risk_reward': {'valid': False, 'ratio': 0},
                'entry_confirmed': False,
                'structure_sl': 0,
                'reasons': [],
                'factors': {},
                'trade_blocked': False,
                'block_reason': ''
            }
            
            # 1. Basic signal analysis
            basic_signal = self.analyze_signals(data)
            analysis_result['signal'] = basic_signal['signal']
            analysis_result['factors']['basic_signal'] = basic_signal['signal']
            analysis_result['factors']['basic_strength'] = basic_signal['strength']
            logger.info(f" Raw signal for {symbol} {timeframe}: {basic_signal['signal']} "
                        f"(strength {basic_signal['strength']:.1f}) - before any gates/filters")
            
            # 2. Higher Timeframe Trend Analysis
            htf_trend = self.analyze_higher_timeframe_trend(mt5_connector, symbol, timeframe, as_of=as_of)
            analysis_result['htf_trend'] = htf_trend['trend']
            analysis_result['factors']['htf_trend'] = htf_trend['trend']
            analysis_result['factors']['htf_strength'] = htf_trend['strength']

            # 2b. Dollar correlation (diagnostic only - see check_dollar_correlation
            # docstring for why this doesn't block trades yet)
            dollar_check = self.check_dollar_correlation(mt5_connector, as_of=as_of)
            analysis_result['factors']['usd_trend'] = dollar_check['usd_trend']
            if dollar_check['available'] and basic_signal['signal'] in ('BUY', 'SELL', 'WEAK BUY', 'WEAK SELL'):
                direction = 'BUY' if 'BUY' in basic_signal['signal'] else 'SELL'
                usd_trend = dollar_check['usd_trend']
                if (direction == 'BUY' and usd_trend == 'BEARISH') or (direction == 'SELL' and usd_trend == 'BULLISH'):
                    analysis_result['factors']['dollar_correlation'] = 'ALIGNED'
                elif (direction == 'BUY' and usd_trend == 'BULLISH') or (direction == 'SELL' and usd_trend == 'BEARISH'):
                    analysis_result['factors']['dollar_correlation'] = 'CONFLICTING'
                else:
                    analysis_result['factors']['dollar_correlation'] = 'NEUTRAL'
            else:
                analysis_result['factors']['dollar_correlation'] = 'UNAVAILABLE'

            # 2c. Volume Profile / PoC / Value Area and Session VWAP -
            # diagnostic only, same reasoning as dollar_correlation above:
            # these are new and unvalidated against a real backtest, so they
            # get logged for visibility first rather than gating any trade.
            # Last ~100 candles as a proxy "session" window - a true session
            # reset (midnight, or exchange open) would need the real
            # timestamp boundaries, which isn't threaded through here yet.
            recent_window = data.tail(100) if len(data) >= 20 else data
            volume_profile = self.calculate_volume_profile(recent_window)
            vwap_data = self.calculate_vwap(recent_window)
            analysis_result['factors']['volume_profile'] = volume_profile
            analysis_result['factors']['vwap'] = vwap_data
            if volume_profile.get('available') and vwap_data.get('available'):
                poc_vwap_gap_pct = abs(volume_profile['poc_price'] - vwap_data['vwap']) / vwap_data['vwap'] * 100
                # "Close together" threshold here is a starting guess (0.1%
                # of gold's price, roughly $4-5 at ~4300), not a backtested
                # value - treat this confluence flag the same as the dollar
                # correlation one: informative, not yet a filter.
                analysis_result['factors']['poc_vwap_confluence'] = poc_vwap_gap_pct < 0.1
            else:
                analysis_result['factors']['poc_vwap_confluence'] = False

            # 3. Market Condition Detection
            market_condition = self.detect_market_condition(data)
            market_condition = self._validate_market_condition_data(market_condition)
            
            analysis_result['market_state'] = market_condition['condition']
            analysis_result['factors']['market_condition'] = market_condition['condition']
            analysis_result['factors']['atr_percent'] = market_condition['atr_percent']
            analysis_result['factors']['volatility'] = market_condition['volatility']
            
            # 4. Calculate structure-based SL and TP
            structure_levels = self.find_structure_levels(data)
            analysis_result['factors']['recent_high'] = structure_levels['recent_high']
            analysis_result['factors']['recent_low'] = structure_levels['recent_low']
            
            # 5. Entry Confirmation
            entry_confirmation = self.check_entry_confirmation(data, basic_signal['signal'])
            
            # Safe access - handle None or missing data
            if entry_confirmation is None:
                entry_confirmation = {'confirmed': False, 'strength': 0, 'reasons': ['Error in confirmation check']}
            
            analysis_result['entry_confirmed'] = entry_confirmation.get('confirmed', False)
            analysis_result['factors']['entry_confirmation'] = entry_confirmation.get('confirmed', False)
            analysis_result['factors']['confirmation_strength'] = entry_confirmation.get('strength', 0)
            
            # 6. TRADE CLASSIFICATION (Instead of blocking)
            # Classify trade quality instead of blocking everything
            
            # Handle weak signals
            if basic_signal['signal'] in ['WEAK BUY', 'WEAK SELL']:
                analysis_result['signal'] = basic_signal['signal'].replace('WEAK ', '')
                analysis_result['confidence'] = basic_signal['strength']
                analysis_result['trade_blocked'] = False  # Never block weak signals
                analysis_result['reasons'].append(f'Weak directional signal: {basic_signal["signal"]} with {basic_signal["strength"]}% strength')
                analysis_result['reasons'].append('Trade allowed: Weak directional movement detected')
                return analysis_result
            
            trade_tier = 'C'  # Default to weak
            trade_score = 0
            
            # Score based on market conditions
            if market_condition['condition'] in ['TRENDING', 'VOLATILE']:
                trade_score += 30
            elif market_condition['condition'] == 'ACTIVE':
                trade_score += 20
            elif market_condition['condition'] == 'RANGING':
                trade_score -= 20  # Penalize only truly ranging markets
            
            # Allow trades in ACTIVE markets even with sideways HTF
            if (market_condition['condition'] == 'ACTIVE' and 
                market_condition.get('atr_percent', 0.1) > 0.1):
                if htf_trend['trend'] == 'SIDEWAYS':
                    trade_score += 15  # Bonus for active market
                    analysis_result['reasons'].append('Active market overrides sideways HTF')
            
            # Score based on HTF trend (no more zero penalty)
            if htf_trend['trend'] in ['BULLISH', 'BEARISH']:
                trade_score += 25
            elif htf_trend['trend'] == 'SIDEWAYS':
                trade_score += 20  # Partial score, not zero
            
            # Score based on signal strength
            if basic_signal['strength'] >= 70:
                trade_score += 25
            elif basic_signal['strength'] >= 50:
                trade_score += 15
            elif basic_signal['strength'] >= 30:
                trade_score += 5
            
            # Score based on entry confirmation (lowered threshold)
            if entry_confirmation and entry_confirmation.get('confirmed', False) and entry_confirmation.get('strength', 0) >= 30:  # Lowered from 40
                trade_score += 20
            elif entry_confirmation and entry_confirmation.get('strength', 0) >= 20:
                trade_score += 10
            else:
                trade_score -= 5
            
            # Determine trade tier and calculate confidence properly
            if trade_score >= 70:
                trade_tier = 'STRONG'
                confidence = min(trade_score * 1.5, 95)  # Normalize confidence
                analysis_result['reasons'].append('STRONG Grade: Excellent setup with high confidence')
            elif trade_score >= 50:
                trade_tier = 'NORMAL'
                confidence = min(trade_score * 1.3, 85)  # Normalize confidence
                analysis_result['reasons'].append('NORMAL Grade: Good setup with solid confidence')
            elif trade_score >= 30:
                trade_tier = 'WEAK'
                confidence = min(trade_score * 1.0, 65)  # Normalize confidence
                analysis_result['reasons'].append('WEAK Grade: Moderate setup - proceed with caution')
            else:
                trade_tier = 'VERY WEAK'
                confidence = min(trade_score * 0.8, 40)  # Normalize confidence
                analysis_result['reasons'].append('VERY WEAK Grade: Low quality - high risk')
            
            analysis_result['trade_tier'] = trade_tier
            analysis_result['trade_score'] = trade_score
            
            # 9. FINAL VALIDATION - SL/TP CRITICAL
            # Note: structure_sl and structure_tp are calculated later in this function
            # We should validate after they're set, not before
            pass
            
            # 10. MINIMUM CONFIDENCE FOR EXECUTION
            if confidence < 40:
                analysis_result['trade_blocked'] = True
                analysis_result['block_reason'] = 'Low confidence - monitor only'
                analysis_result['signal'] = 'WAIT'
                analysis_result['confidence'] = confidence
                analysis_result['reasons'].append(f'Low confidence ({confidence:.0f}%) - trade monitored but not executed')
                return analysis_result
            
            # Final signal assignment
            analysis_result['signal'] = basic_signal['signal']
            analysis_result['confidence'] = confidence
            analysis_result['trade_blocked'] = False
            analysis_result['reasons'].append(f'Trade approved: {trade_tier} grade with {confidence:.0f}% confidence')

            # 7. TREND ALIGNMENT CHECK (more flexible)
            if basic_signal['signal'] == 'BUY' and htf_trend['trend'] == 'BEARISH':
                # Only block if HTF is strongly bearish (strength >= 70)
                if htf_trend['strength'] >= 70:
                    analysis_result['trade_blocked'] = True
                    analysis_result['block_reason'] = 'BUY signal conflicts with strong HTF bearish trend'
                    analysis_result['signal'] = 'WAIT'
                    # Keep current confidence, don't reset to 0
                    analysis_result['reasons'].append('BUY signal conflicts with strong HTF bearish trend')
                    return analysis_result
                else:
                    analysis_result['reasons'].append('BUY signal despite weak HTF bearish trend')
            elif basic_signal['signal'] == 'SELL' and htf_trend['trend'] == 'BULLISH':
                # Only block if HTF is strongly bullish (strength >= 70)
                if htf_trend['strength'] >= 70:
                    analysis_result['trade_blocked'] = True
                    analysis_result['block_reason'] = 'SELL signal conflicts with strong HTF bullish trend'
                    analysis_result['signal'] = 'WAIT'
                    # Keep current confidence, don't reset to 0
                    analysis_result['reasons'].append('SELL signal conflicts with strong HTF bullish trend')
                    return analysis_result
                else:
                    analysis_result['reasons'].append('SELL signal despite weak HTF bullish trend')
            
            # 8. FINAL VALIDATION - Only block if no entry confirmation or poor risk:reward
            if not entry_confirmation['confirmed']:
                analysis_result['trade_blocked'] = True
                analysis_result['block_reason'] = 'Entry confirmation missing'
                analysis_result['signal'] = 'WAIT'
                # Keep current confidence, don't reset to 0
                analysis_result['reasons'].append('Entry confirmation missing')
                return analysis_result
            
            # 9. Calculate structure-based SL and TP
            current_price = data['close'].iloc[-1]
            if basic_signal['signal'] == 'BUY':
                # SL below recent swing low
                analysis_result['structure_sl'] = structure_levels['recent_low']
                # TP based on 1:2 risk:reward
                risk = current_price - structure_levels['recent_low']
                analysis_result['structure_tp'] = current_price + (risk * 2)
            elif basic_signal['signal'] == 'SELL':
                # SL above recent swing high
                analysis_result['structure_sl'] = structure_levels['recent_high']
                # TP based on 1:2 risk:reward
                risk = structure_levels['recent_high'] - current_price
                analysis_result['structure_tp'] = current_price - (risk * 2)
            
            # 10. RISK:REWARD VALIDATION
            if basic_signal['signal'] in ['BUY', 'SELL']:
                risk_reward = self.calculate_risk_reward(
                    current_price, 
                    analysis_result['structure_sl'], 
                    analysis_result['structure_tp']
                )
                analysis_result['risk_reward'] = risk_reward
                
                if not risk_reward['valid']:
                    analysis_result['trade_blocked'] = True
                    analysis_result['block_reason'] = 'Risk:Reward below 1:2'
                    analysis_result['signal'] = 'WAIT'
                    # Keep current confidence, don't reset to 0
                    analysis_result['reasons'].append('Risk:Reward below 1:2')
                    return analysis_result
            
            # 11. ADVANCED CONFIDENCE CALCULATION
            confidence_factors = []
            
            # Basic signal strength (30% weight)
            confidence_factors.append(('basic_signal', basic_signal['strength'], 0.3))
            
            # HTF trend alignment (25% weight)
            # Was all-or-nothing: full credit only when H4 trend exactly
            # matched the trade direction, ZERO for anything else -
            # including a merely SIDEWAYS/neutral H4 trend, which isn't
            # actually opposing the trade, just not actively confirming it.
            # This was the dominant reason strong raw signals (e.g. 85%
            # basic_signal strength) were landing at ~40% final confidence:
            # a genuinely non-hostile neutral H4 read was being scored
            # identically to a directly opposing one. Partial credit for
            # neutral is more honest about what "neutral" actually means.
            htf_alignment_score = 0
            if basic_signal['signal'] == 'BUY' and htf_trend['trend'] == 'BULLISH':
                htf_alignment_score = htf_trend['strength']
            elif basic_signal['signal'] == 'SELL' and htf_trend['trend'] == 'BEARISH':
                htf_alignment_score = htf_trend['strength']
            elif htf_trend['trend'] == 'SIDEWAYS':
                htf_alignment_score = htf_trend['strength'] * 0.5
            confidence_factors.append(('htf_alignment', htf_alignment_score, 0.25))
            
            # Market condition (20% weight) - adjusted for flexibility
            # Was checking for 'SIDEWAYS', but detect_market_condition()
            # never returns that string - it returns 'ACTIVE' for normal,
            # moderate conditions (see its own condition logic above). That
            # meant every genuinely normal/healthy market - likely the most
            # common state on M5 - fell through to the catch-all else branch
            # and got scored as RANGING (20, the worst tier), not because
            # conditions were actually poor, just because of this mismatch.
            market_score = 0
            if market_condition['condition'] == 'TRENDING':
                market_score = 80
            elif market_condition['condition'] == 'VOLATILE':
                market_score = 60
            elif market_condition['condition'] == 'ACTIVE':
                market_score = 50  # Normal, healthy conditions - not as
                # strong a confirmation as an active TREND, but not remotely
                # equivalent to RANGING (dead/low-opportunity) either.
            else:  # RANGING, or any genuinely unrecognized condition
                market_score = 20
            confidence_factors.append(('market_condition', market_score, 0.2))
            
            # Entry confirmation (25% weight)
            confidence_factors.append(('entry_confirmation', entry_confirmation['strength'], 0.25))
            
            logger.info(f"   Confidence factors: " +
                        ", ".join(f"{name}={score:.1f}(w={weight})" for name, score, weight in confidence_factors))
            
            # Calculate weighted confidence
            weighted_confidence = 0
            total_weight = 0
            
            for factor_name, score, weight in confidence_factors:
                weighted_confidence += score * weight
                total_weight += weight
                analysis_result['factors'][f'{factor_name}_score'] = score
                analysis_result['factors'][f'{factor_name}_weight'] = weight
            
            if total_weight > 0:
                analysis_result['confidence'] = min(weighted_confidence / total_weight, 85)  # Cap at 85%
            
            # 12. Final validation
            if analysis_result['confidence'] < 25:  # Changed from 50 to 25
                analysis_result['trade_blocked'] = True
                analysis_result['block_reason'] = 'Confidence too low'
                analysis_result['signal'] = 'WAIT'
                # Keep current confidence, don't reset to 0
                analysis_result['reasons'].append('Confidence below 25%')
                return analysis_result
            
            # Add success reasons
            analysis_result['reasons'].extend([
                f'HTF trend aligned: {htf_trend["trend"]}',
                f'Market condition: {market_condition["condition"]}',
                f'Entry confirmed: {entry_confirmation.get("confirmed", False)}',
                f'Risk:Reward: {analysis_result["risk_reward"]["ratio"]:.1f}:1'
            ])
            
            # 12. FINAL SL/TP VALIDATION
            if not analysis_result.get('structure_sl') or not analysis_result.get('structure_tp'):
                analysis_result['trade_blocked'] = True
                analysis_result['block_reason'] = 'Invalid SL/TP - trade blocked'
                analysis_result['signal'] = 'WAIT'
                # Keep current confidence, don't reset to 0
                analysis_result['reasons'].append('CRITICAL: No valid stop loss/take profit levels')
                return analysis_result
            
            # 13. MINIMUM CONFIDENCE FOR EXECUTION
            if analysis_result.get('confidence', 0) < 25:  # Changed from 50 to 25
                analysis_result['trade_blocked'] = True
                analysis_result['block_reason'] = 'Confidence too low'
                analysis_result['signal'] = 'WAIT'
                # Keep current confidence, don't reset to 0
                analysis_result['reasons'].append('Confidence below 25%')
                return analysis_result
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in advanced signal analysis: {e}")
            return {
                'signal': 'WAIT',
                'confidence': 0,
                'market_state': 'ERROR',
                'htf_trend': 'SIDEWAYS',
                'risk_reward': {'valid': False, 'ratio': 0},
                'entry_confirmed': False,
                'structure_sl': 0,
                'reasons': [f'Analysis error: {e}'],
                'factors': {},
                'trade_blocked': True,
                'block_reason': 'Analysis error'
            }