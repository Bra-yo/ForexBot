"""
Feature Engineering for BrayoForexBot AI Models
Transforms raw market data into meaningful features for machine learning
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import talib
from typing import Dict, List, Tuple, Optional
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.decomposition import PCA
import logging

logger = logging.getLogger(__name__)

class FeatureEngineer:
    """
    Advanced feature engineering for trading ML models
    Creates technical, statistical, and market microstructure features
    """
    
    def __init__(self):
        self.scalers = {}
        self.feature_columns = []
        self.target_columns = []
        
        # Feature categories
        self.price_features = []
        self.volume_features = []
        self.technical_features = []
        self.statistical_features = []
        self.time_features = []
        
    def create_features(self, data: pd.DataFrame, target_horizon: int = 1) -> pd.DataFrame:
        """
        Create comprehensive feature set from OHLCV data
        
        Args:
            data: OHLCV DataFrame
            target_horizon: Number of periods ahead for target variable
            
        Returns:
            DataFrame with features and targets
        """
        try:
            if data.empty or len(data) < 100:
                logger.warning("Insufficient data for feature engineering")
                return pd.DataFrame()
            
            logger.info(f"Creating features from {len(data)} data points...")
            
            # Create copy to avoid modifying original
            df = data.copy()
            
            # Basic validation
            required_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")
            
            # 1. Price-based features
            df = self._create_price_features(df)
            
            # 2. Volume-based features
            df = self._create_volume_features(df)
            
            # 3. Technical indicators
            df = self._create_technical_features(df)
            
            # 4. Statistical features
            df = self._create_statistical_features(df)
            
            # 5. Time-based features
            df = self._create_time_features(df)
            
            # 6. Market microstructure features
            df = self._create_microstructure_features(df)
            
            # 7. Target variables
            df = self._create_targets(df, target_horizon)
            
            # 8. Feature selection and cleaning
            df = self._clean_features(df)
            
            # Store feature column names
            self._update_feature_lists(df)
            
            logger.info(f"Created {len(self.feature_columns)} features and {len(self.target_columns)} targets")
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating features: {e}")
            return pd.DataFrame()
    
    def _create_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create price-based features"""
        try:
            # Price changes
            df['price_change'] = df['close'].pct_change()
            df['price_change_abs'] = df['price_change'].abs()
            
            # Log returns
            df['log_return'] = np.log(df['close'] / df['close'].shift(1))
            
            # High-Low spread
            df['hl_spread'] = (df['high'] - df['low']) / df['close']
            
            # Open-Close spread
            df['oc_spread'] = (df['close'] - df['open']) / df['open']
            
            # Price position in range
            df['price_position'] = (df['close'] - df['low']) / (df['high'] - df['low'])
            
            # True Range
            df['true_range'] = talib.TRANGE(df['high'], df['low'], df['close'])
            df['atr'] = talib.ATR(df['high'], df['low'], df['close'], timeperiod=14)
            df['atr_ratio'] = df['true_range'] / df['atr']
            
            # Price acceleration
            df['price_acceleration'] = df['price_change'].diff()
            
            # Multi-period returns
            for period in [3, 5, 10, 20]:
                df[f'return_{period}d'] = df['close'].pct_change(period)
                df[f'log_return_{period}d'] = np.log(df['close'] / df['close'].shift(period))
            
            # Rolling price statistics
            for window in [5, 10, 20, 50]:
                df[f'close_mean_{window}'] = df['close'].rolling(window).mean()
                df[f'close_std_{window}'] = df['close'].rolling(window).std()
                df[f'close_zscore_{window}'] = (df['close'] - df[f'close_mean_{window}']) / df[f'close_std_{window}']
                df[f'close_min_{window}'] = df['close'].rolling(window).min()
                df[f'close_max_{window}'] = df['close'].rolling(window).max()
                df[f'close_range_{window}'] = (df[f'close_max_{window}'] - df[f'close_min_{window}']) / df[f'close_mean_{window}']
            
            self.price_features = [col for col in df.columns if col not in ['open', 'high', 'low', 'close', 'volume']]
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating price features: {e}")
            return df
    
    def _create_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create volume-based features"""
        try:
            # Volume changes
            df['volume_change'] = df['volume'].pct_change()
            df['volume_ma_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
            
            # Volume price relationship
            df['volume_weighted_price'] = (df['high'] + df['low'] + df['close']) / 3 * df['volume']
            df['vwap'] = df['volume_weighted_price'].rolling(20).sum() / df['volume'].rolling(20).sum()
            df['price_vwap_ratio'] = df['close'] / df['vwap']
            
            # On-Balance Volume
            df['obv'] = talib.OBV(df['close'], df['volume'])
            df['obv_ma'] = df['obv'].rolling(10).mean()
            df['obv_ratio'] = df['obv'] / df['obv_ma']
            
            # Volume Rate of Change
            df['volume_roc'] = talib.ROC(df['volume'], timeperiod=10)
            
            # Accumulation/Distribution Line
            df['ad_line'] = talib.ADL(df['high'], df['low'], df['close'], df['volume'])
            df['ad_line_ma'] = df['ad_line'].rolling(10).mean()
            df['ad_line_ratio'] = df['ad_line'] / df['ad_line_ma']
            
            # Ease of Movement
            df['eom'] = talib.AD(df['high'], df['low'], df['close'], df['volume'])
            df['eom_ma'] = df['eom'].rolling(10).mean()
            df['eom_ratio'] = df['eom'] / df['eom_ma']
            
            # Rolling volume statistics
            for window in [5, 10, 20]:
                df[f'volume_mean_{window}'] = df['volume'].rolling(window).mean()
                df[f'volume_std_{window}'] = df['volume'].rolling(window).std()
                df[f'volume_zscore_{window}'] = (df['volume'] - df[f'volume_mean_{window}']) / df[f'volume_std_{window}']
            
            self.volume_features = [col for col in df.columns if 'volume' in col.lower() and col not in self.price_features]
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating volume features: {e}")
            return df
    
    def _create_technical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create technical indicator features"""
        try:
            # Moving Averages
            for period in [5, 10, 20, 50, 200]:
                df[f'sma_{period}'] = talib.SMA(df['close'], timeperiod=period)
                df[f'ema_{period}'] = talib.EMA(df['close'], timeperiod=period)
                df[f'price_sma_{period}_ratio'] = df['close'] / df[f'sma_{period}']
                df[f'price_ema_{period}_ratio'] = df['close'] / df[f'ema_{period}']
            
            # Moving Average Crossovers
            df['sma_5_20_cross'] = (df['sma_5'] > df['sma_20']).astype(int)
            df['sma_20_50_cross'] = (df['sma_20'] > df['sma_50']).astype(int)
            df['ema_12_26_cross'] = (df['ema_12'] > df['ema_26']).astype(int)
            
            # RSI
            for period in [7, 14, 21]:
                df[f'rsi_{period}'] = talib.RSI(df['close'], timeperiod=period)
                df[f'rsi_{period}_overbought'] = (df[f'rsi_{period}'] > 70).astype(int)
                df[f'rsi_{period}_oversold'] = (df[f'rsi_{period}'] < 30).astype(int)
            
            # MACD
            macd, macd_signal, macd_hist = talib.MACD(df['close'])
            df['macd'] = macd
            df['macd_signal'] = macd_signal
            df['macd_histogram'] = macd_hist
            df['macd_bullish'] = (macd > macd_signal).astype(int)
            df['macd_histogram_positive'] = (macd_hist > 0).astype(int)
            
            # Bollinger Bands
            for period in [10, 20]:
                bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'], timeperiod=period)
                df[f'bb_upper_{period}'] = bb_upper
                df[f'bb_middle_{period}'] = bb_middle
                df[f'bb_lower_{period}'] = bb_lower
                df[f'bb_width_{period}'] = (bb_upper - bb_lower) / bb_middle
                df[f'bb_position_{period}'] = (df['close'] - bb_lower) / (bb_upper - bb_lower)
                df[f'bb_squeeze_{period}'] = (df[f'bb_width_{period}'] < df[f'bb_width_{period}'].rolling(50).mean() * 0.8).astype(int)
            
            # Stochastic Oscillator
            slowk, slowd = talib.STOCH(df['high'], df['low'], df['close'])
            df['stoch_k'] = slowk
            df['stoch_d'] = slowd
            df['stoch_overbought'] = (slowk > 80).astype(int)
            df['stoch_oversold'] = (slowk < 20).astype(int)
            df['stoch_cross'] = (slowk > slowd).astype(int)
            
            # Williams %R
            df['williams_r'] = talib.WILLR(df['high'], df['low'], df['close'])
            df['williams_r_overbought'] = (df['williams_r'] < -20).astype(int)
            df['williams_r_oversold'] = (df['williams_r'] > -80).astype(int)
            
            # CCI
            df['cci'] = talib.CCI(df['high'], df['low'], df['close'])
            df['cci_overbought'] = (df['cci'] > 100).astype(int)
            df['cci_oversold'] = (df['cci'] < -100).astype(int)
            
            # ADX
            df['adx'] = talib.ADX(df['high'], df['low'], df['close'])
            df['adx_strong'] = (df['adx'] > 25).astype(int)
            df['di_plus'] = talib.PLUS_DI(df['high'], df['low'], df['close'])
            df['di_minus'] = talib.MINUS_DI(df['high'], df['low'], df['close'])
            df['di_cross'] = (df['di_plus'] > df['di_minus']).astype(int)
            
            # Momentum indicators
            df['momentum'] = talib.MOM(df['close'], timeperiod=10)
            df['rate_of_change'] = talib.ROC(df['close'], timeperiod=10)
            df['rate_of_change_pct'] = talib.ROCP(df['close'], timeperiod=10)
            
            # Commodity Channel Index
            df['cci_14'] = talib.CCI(df['high'], df['low'], df['close'], timeperiod=14)
            
            self.technical_features = [col for col in df.columns if col not in self.price_features + self.volume_features + ['open', 'high', 'low', 'close', 'volume']]
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating technical features: {e}")
            return df
    
    def _create_statistical_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create statistical features"""
        try:
            # Rolling statistics
            for window in [10, 20, 50]:
                # Skewness and kurtosis
                df[f'close_skew_{window}'] = df['close'].rolling(window).skew()
                df[f'close_kurt_{window}'] = df['close'].rolling(window).kurt()
                
                # Percentile ranks
                df[f'close_percentile_{window}'] = df['close'].rolling(window).rank(pct=True)
                
                # Autocorrelation
                df[f'close_autocorr_{window}'] = df['close'].rolling(window).apply(lambda x: x.autocorr(lag=1))
            
            # Price volatility
            for window in [5, 10, 20]:
                df[f'volatility_{window}'] = df['price_change'].rolling(window).std() * np.sqrt(252)
                df[f'volatility_ratio_{window}'] = df[f'volatility_{window}'] / df[f'volatility_{window}'].rolling(50).mean()
            
            # Trend strength
            df['trend_strength_20'] = abs(df['close'].rolling(20).apply(lambda x: np.polyfit(range(len(x)), x, 0)[0]))
            df['trend_strength_50'] = abs(df['close'].rolling(50).apply(lambda x: np.polyfit(range(len(x)), x, 0)[0]))
            
            # Price momentum consistency
            for window in [5, 10, 20]:
                df[f'positive_momentum_{window}'] = (df['price_change'].rolling(window) > 0).sum()
                df[f'momentum_consistency_{window}'] = df[f'positive_momentum_{window}'] / window
            
            # Range expansion/contraction
            for window in [10, 20]:
                df[f'range_expansion_{window}'] = df['hl_spread'].rolling(window).mean() / df['hl_spread'].rolling(window*2).mean()
            
            self.statistical_features = [col for col in df.columns if any(x in col for x in ['skew', 'kurt', 'percentile', 'autocorr', 'volatility', 'trend', 'momentum', 'range']) and col not in self.price_features + self.volume_features + self.technical_features]
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating statistical features: {e}")
            return df
    
    def _create_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create time-based features"""
        try:
            # Ensure datetime index
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            
            # Basic time features
            df['hour'] = df.index.hour
            df['day_of_week'] = df.index.dayofweek
            df['day_of_month'] = df.index.day
            df['month'] = df.index.month
            df['quarter'] = df.index.quarter
            
            # Cyclical encoding
            df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
            df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
            df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
            df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
            df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
            df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
            
            # Trading session indicators (assuming forex 24/5)
            df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)
            df['is_asian_session'] = ((df['hour'] >= 0) & (df['hour'] < 9)).astype(int)
            df['is_london_session'] = ((df['hour'] >= 8) & (df['hour'] < 17)).astype(int)
            df['is_ny_session'] = ((df['hour'] >= 13) & (df['hour'] < 22)).astype(int)
            
            # Session overlaps
            df['is_london_ny_overlap'] = ((df['hour'] >= 13) & (df['hour'] < 17)).astype(int)
            df['is_asian_london_overlap'] = ((df['hour'] >= 8) & (df['hour'] < 9)).astype(int)
            
            # Time of day volatility patterns
            df['hour_volatility_pattern'] = df.groupby('hour')['price_change'].transform('mean')
            df['day_volatility_pattern'] = df.groupby('day_of_week')['price_change'].transform('mean')
            
            self.time_features = [col for col in df.columns if any(x in col for x in ['hour', 'day', 'month', 'quarter', 'session', 'overlap']) and col not in self.price_features + self.volume_features + self.technical_features + self.statistical_features]
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating time features: {e}")
            return df
    
    def _create_microstructure_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create market microstructure features"""
        try:
            # Order flow imbalance (using volume as proxy)
            df['buy_pressure'] = np.where(df['close'] > df['open'], df['volume'], 0)
            df['sell_pressure'] = np.where(df['close'] < df['open'], df['volume'], 0)
            df['order_flow_imbalance'] = (df['buy_pressure'] - df['sell_pressure']) / df['volume']
            
            # Price efficiency
            df['price_efficiency'] = df['close'] / ((df['high'] + df['low']) / 2)
            
            # Volume weighted average price deviation
            df['vwap_deviation'] = (df['close'] - df['vwap']) / df['vwap']
            
            # Microstructure noise
            df['microstructure_noise'] = df['price_change'] - df['price_change'].rolling(5).mean()
            
            # Liquidity measures (using spread as proxy)
            df['liquidity_ratio'] = df['volume'] / df['hl_spread']
            
            # Market depth indicators
            df['depth_ratio'] = df['volume'] / df['atr']
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating microstructure features: {e}")
            return df
    
    def _create_targets(self, df: pd.DataFrame, horizon: int) -> pd.DataFrame:
        """Create target variables"""
        try:
            # Future returns
            df[f'target_return_{horizon}'] = df['close'].shift(-horizon).pct_change(horizon)
            df[f'target_log_return_{horizon}'] = np.log(df['close'].shift(-horizon) / df['close'])
            
            # Direction targets
            df[f'target_direction_{horizon}'] = (df[f'target_return_{horizon}'] > 0).astype(int)
            df[f'target_direction_strong_{horizon}'] = (df[f'target_return_{horizon}'] > 0.001).astype(int)
            df[f'target_direction_weak_{horizon}'] = (df[f'target_return_{horizon}'] > 0.0001).astype(int)
            
            # Volatility targets
            df[f'target_volatility_{horizon}'] = df['price_change'].rolling(horizon).std().shift(-horizon)
            df[f'target_high_low_{horizon}'] = (df['high'].shift(-horizon).rolling(horizon).max() - df['low'].shift(-horizon).rolling(horizon).min()) / df['close']
            
            # Range targets
            df[f'target_range_upper_{horizon}'] = df['high'].shift(-horizon).rolling(horizon).max() / df['close']
            df[f'target_range_lower_{horizon}'] = df['low'].shift(-horizon).rolling(horizon).min() / df['close']
            
            # Classification targets
            df[f'target_class_{horizon}'] = np.where(df[f'target_return_{horizon}'] > 0.002, 2,  # Strong up
                                                     np.where(df[f'target_return_{horizon}'] < -0.002, 0,  # Strong down
                                                             1))  # Neutral
            
            self.target_columns = [col for col in df.columns if 'target_' in col]
            
            return df
            
        except Exception as e:
            logger.error(f"Error creating targets: {e}")
            return df
    
    def _clean_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and prepare features"""
        try:
            # Remove infinite values
            df = df.replace([np.inf, -np.inf], np.nan)
            
            # Remove columns with too many NaN values
            nan_threshold = 0.3  # 30% threshold
            cols_to_keep = []
            
            for col in df.columns:
                if col in self.target_columns:
                    cols_to_keep.append(col)  # Keep target columns regardless
                else:
                    nan_ratio = df[col].isna().sum() / len(df)
                    if nan_ratio <= nan_threshold:
                        cols_to_keep.append(col)
            
            df = df[cols_to_keep]
            
            # Forward fill remaining NaN values
            df = df.fillna(method='ffill')
            
            # Backfill any remaining NaN values
            df = df.fillna(method='bfill')
            
            # Remove any remaining rows with NaN values
            df = df.dropna()
            
            logger.info(f"Cleaned features: {len(df.columns)} columns, {len(df)} rows")
            
            return df
            
        except Exception as e:
            logger.error(f"Error cleaning features: {e}")
            return df
    
    def _update_feature_lists(self, df: pd.DataFrame):
        """Update feature column lists"""
        all_columns = df.columns.tolist()
        
        self.feature_columns = [col for col in all_columns if col not in self.target_columns and col not in ['open', 'high', 'low', 'close', 'volume']]
        self.target_columns = [col for col in all_columns if 'target_' in col]
        
        logger.info(f"Features: {len(self.feature_columns)}, Targets: {len(self.target_columns)}")
    
    def scale_features(self, df: pd.DataFrame, method: str = 'standard') -> pd.DataFrame:
        """
        Scale features for ML models
        
        Args:
            df: DataFrame with features
            method: 'standard' or 'minmax'
            
        Returns:
            Scaled DataFrame
        """
        try:
            if self.feature_columns is None:
                self._update_feature_lists(df)
            
            df_scaled = df.copy()
            
            if method == 'standard':
                scaler = StandardScaler()
            elif method == 'minmax':
                scaler = MinMaxScaler()
            else:
                raise ValueError("Method must be 'standard' or 'minmax'")
            
            # Fit scaler on features
            df_scaled[self.feature_columns] = scaler.fit_transform(df[self.feature_columns])
            
            # Store scaler
            self.scalers[method] = scaler
            
            logger.info(f"Scaled {len(self.feature_columns)} features using {method} scaling")
            
            return df_scaled
            
        except Exception as e:
            logger.error(f"Error scaling features: {e}")
            return df
    
    def apply_scaling(self, df: pd.DataFrame, method: str = 'standard') -> pd.DataFrame:
        """Apply existing scaling to new data"""
        try:
            if method not in self.scalers:
                raise ValueError(f"No scaler found for method: {method}")
            
            df_scaled = df.copy()
            df_scaled[self.feature_columns] = self.scalers[method].transform(df[self.feature_columns])
            
            return df_scaled
            
        except Exception as e:
            logger.error(f"Error applying scaling: {e}")
            return df
    
    def reduce_features(self, df: pd.DataFrame, method: str = 'pca', n_components: int = 50) -> pd.DataFrame:
        """
        Reduce feature dimensionality
        
        Args:
            df: DataFrame with features
            method: 'pca' or 'variance'
            n_components: Number of components to keep
            
        Returns:
            DataFrame with reduced features
        """
        try:
            if self.feature_columns is None:
                self._update_feature_lists(df)
            
            features = df[self.feature_columns]
            
            if method == 'pca':
                pca = PCA(n_components=n_components)
                reduced_features = pca.fit_transform(features)
                
                # Create new column names
                pca_columns = [f'pca_{i}' for i in range(n_components)]
                df_reduced = pd.DataFrame(reduced_features, columns=pca_columns, index=df.index)
                
                # Add targets back
                for col in self.target_columns:
                    if col in df.columns:
                        df_reduced[col] = df[col]
                
                logger.info(f"Reduced features from {len(self.feature_columns)} to {n_components} using PCA")
                
            elif method == 'variance':
                # Remove low variance features
                variance_threshold = 0.01
                feature_variances = features.var()
                high_variance_features = feature_variances[feature_variances > variance_threshold].index
                
                df_reduced = df[high_variance_features.tolist() + self.target_columns]
                
                logger.info(f"Reduced features from {len(self.feature_columns)} to {len(high_variance_features)} using variance threshold")
            
            else:
                raise ValueError("Method must be 'pca' or 'variance'")
            
            return df_reduced
            
        except Exception as e:
            logger.error(f"Error reducing features: {e}")
            return df
    
    def get_feature_importance(self, df: pd.DataFrame, target_col: str) -> pd.Series:
        """
        Calculate feature importance using correlation with target
        
        Args:
            df: DataFrame with features and target
            target_col: Target column name
            
        Returns:
            Series with feature importance scores
        """
        try:
            if target_col not in df.columns:
                raise ValueError(f"Target column {target_col} not found")
            
            # Calculate correlation with target
            correlations = df[self.feature_columns].corrwith(df[target_col]).abs()
            
            # Sort by importance
            importance = correlations.sort_values(ascending=False)
            
            return importance
            
        except Exception as e:
            logger.error(f"Error calculating feature importance: {e}")
            return pd.Series()
    
    def save_feature_config(self, filepath: str):
        """Save feature configuration"""
        try:
            import json
            
            config = {
                'feature_columns': self.feature_columns,
                'target_columns': self.target_columns,
                'price_features': self.price_features,
                'volume_features': self.volume_features,
                'technical_features': self.technical_features,
                'statistical_features': self.statistical_features,
                'time_features': self.time_features
            }
            
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Feature configuration saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving feature config: {e}")
    
    def load_feature_config(self, filepath: str):
        """Load feature configuration"""
        try:
            import json
            
            with open(filepath, 'r') as f:
                config = json.load(f)
            
            self.feature_columns = config['feature_columns']
            self.target_columns = config['target_columns']
            self.price_features = config['price_features']
            self.volume_features = config['volume_features']
            self.technical_features = config['technical_features']
            self.statistical_features = config['statistical_features']
            self.time_features = config['time_features']
            
            logger.info(f"Feature configuration loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"Error loading feature config: {e}")
