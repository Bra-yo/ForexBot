"""
LEVEL 3 INTELLIGENCE SYSTEM
Advanced market analysis, signal scoring, and adaptive trading
"""

import MetaTrader5 as mt5
import numpy as np
import logging
from datetime import datetime, timedelta
from config import *

logger = logging.getLogger(__name__)

class MarketRegimeDetector:
    """Detect market conditions and regimes"""
    
    def __init__(self):
        self.regime_cache = {}
        
    def detect_regime(self, symbol, timeframe='H1'):
        """Detect if market is trending or ranging"""
        try:
            # Get enough data for EMA calculation
            rates = mt5.copy_rates_from_pos(symbol, getattr(mt5, f'TIMEFRAME_{timeframe}'), 0, 200)
            if not rates or len(rates) < 200:
                return "UNKNOWN"
            
            closes = np.array([rate['close'] for rate in rates])
            
            # Calculate EMAs
            ema_50 = self._calculate_ema(closes, 50)
            ema_200 = self._calculate_ema(closes, 200)
            
            # Determine regime
            current_price = closes[-1]
            
            if ema_50 > ema_200:
                if current_price > ema_50:
                    return "STRONG_UPTREND"
                else:
                    return "UPTREND"
            elif ema_50 < ema_200:
                if current_price < ema_50:
                    return "STRONG_DOWNTREND"
                else:
                    return "DOWNTREND"
            else:
                return "RANGING"
                
        except Exception as e:
            logger.error(f"Regime detection error for {symbol}: {e}")
            return "UNKNOWN"
    
    def _calculate_ema(self, prices, period):
        """Calculate Exponential Moving Average"""
        alpha = 2 / (period + 1)
        ema = prices[0]
        for price in prices[1:]:
            ema = alpha * price + (1 - alpha) * ema
        return ema

class SignalScoringEngine:
    """Advanced signal scoring and quality assessment"""
    
    def __init__(self):
        self.signal_weights = {
            'trend_alignment': 0.3,
            'momentum_strength': 0.25,
            'volume_confirmation': 0.2,
            'volatility_quality': 0.15,
            'structure_break': 0.1
        }
        
    def calculate_signal_score(self, symbol, signal, confidence, timeframe):
        """Calculate comprehensive signal score (0-100)"""
        try:
            score = 0.0
            reasons = []
            
            # 1. Trend Alignment (30% weight)
            trend_score, trend_reason = self._analyze_trend_alignment(symbol, signal)
            score += trend_score * self.signal_weights['trend_alignment']
            reasons.append(f"Trend: {trend_reason}")
            
            # 2. Momentum Strength (25% weight)
            momentum_score, momentum_reason = self._analyze_momentum(symbol, signal)
            score += momentum_score * self.signal_weights['momentum_strength']
            reasons.append(f"Momentum: {momentum_reason}")
            
            # 3. Volume Confirmation (20% weight)
            volume_score, volume_reason = self._analyze_volume(symbol, signal)
            score += volume_score * self.signal_weights['volume_confirmation']
            reasons.append(f"Volume: {volume_reason}")
            
            # 4. Volatility Quality (15% weight)
            volatility_score, volatility_reason = self._analyze_volatility(symbol)
            score += volatility_score * self.signal_weights['volatility_quality']
            reasons.append(f"Volatility: {volatility_reason}")
            
            # 5. Structure Break (10% weight)
            structure_score, structure_reason = self._analyze_structure(symbol, signal)
            score += structure_score * self.signal_weights['structure_break']
            reasons.append(f"Structure: {structure_reason}")
            
            # Apply confidence bonus
            confidence_bonus = (confidence - 50) * 0.2  # Bonus for high confidence
            score += confidence_bonus
            
            # Cap at 100
            final_score = min(score, 100)
            
            return final_score, "; ".join(reasons)
            
        except Exception as e:
            logger.error(f"Signal scoring error for {symbol}: {e}")
            return 0.0, "Scoring error"
    
    def _analyze_trend_alignment(self, symbol, signal):
        """Analyze trend alignment with signal"""
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 100)
            if not rates:
                return 50, "No data"
            
            closes = [rate['close'] for rate in rates]
            
            # Simple trend analysis
            if len(closes) >= 20:
                recent_high = max(closes[-20:])
                recent_low = min(closes[-20:])
                
                if signal == "BUY":
                    if closes[-1] > recent_high * 0.98:  # Near recent high
                        return 80, "Strong uptrend alignment"
                    elif closes[-1] > np.mean(closes[-20:]):
                        return 60, "Moderate uptrend"
                    else:
                        return 30, "Weak uptrend"
                else:  # SELL
                    if closes[-1] < recent_low * 1.02:  # Near recent low
                        return 80, "Strong downtrend alignment"
                    elif closes[-1] < np.mean(closes[-20:]):
                        return 60, "Moderate downtrend"
                    else:
                        return 30, "Weak downtrend"
            
            return 50, "Insufficient data"
            
        except Exception as e:
            return 50, f"Trend analysis error: {e}"
    
    def _analyze_momentum(self, symbol, signal):
        """Analyze momentum indicators"""
        try:
            # Simple RSI-like momentum
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 50)
            if not rates:
                return 50, "No data"
            
            closes = np.array([rate['close'] for rate in rates])
            
            # Calculate momentum
            if len(closes) >= 14:
                momentum = closes[-1] - closes[-14]
                momentum_strength = abs(momentum) / closes[-14] * 100
                
                if (signal == "BUY" and momentum > 0) or (signal == "SELL" and momentum < 0):
                    return min(momentum_strength * 100, 80), f"Strong momentum ({momentum_strength:.1f}%)"
                else:
                    return max(momentum_strength * 50, 30), f"Weak momentum ({momentum_strength:.1f}%)"
            
            return 50, "Insufficient data"
            
        except Exception as e:
            return 50, f"Momentum analysis error: {e}"
    
    def _analyze_volume(self, symbol, signal):
        """Analyze volume confirmation"""
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 50)
            if not rates:
                return 50, "No data"
            
            volumes = np.array([rate['tick_volume'] for rate in rates])
            current_volume = volumes[-1]
            avg_volume = np.mean(volumes[:-5])  # Exclude recent 5 bars
            
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            if volume_ratio > 1.2:  # 20% above average
                return 80, f"High volume confirmation ({volume_ratio:.1f}x)"
            elif volume_ratio > 1.0:
                return 60, f"Moderate volume ({volume_ratio:.1f}x)"
            else:
                return 30, f"Low volume ({volume_ratio:.1f}x)"
                
        except Exception as e:
            return 50, f"Volume analysis error: {e}"
    
    def _analyze_volatility(self, symbol):
        """Analyze volatility quality"""
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 50)
            if not rates:
                return 50, "No data"
            
            highs = np.array([rate['high'] for rate in rates])
            lows = np.array([rate['low'] for rate in rates])
            
            # Calculate ATR-like volatility
            ranges = highs - lows
            avg_range = np.mean(ranges[-20:])  # Average range of last 20 bars
            current_range = ranges[-1]
            
            volatility_ratio = current_range / avg_range if avg_range > 0 else 1
            
            # Ideal volatility (not too high, not too low)
            if 0.8 <= volatility_ratio <= 1.5:
                return 80, "Optimal volatility"
            elif 0.5 <= volatility_ratio <= 2.0:
                return 60, "Acceptable volatility"
            else:
                return 30, "Extreme volatility"
                
        except Exception as e:
            return 50, f"Volatility analysis error: {e}"
    
    def _analyze_structure(self, symbol, signal):
        """Analyze price structure and patterns"""
        try:
            rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 0, 50)
            if not rates:
                return 50, "No data"
            
            highs = np.array([rate['high'] for rate in rates])
            lows = np.array([rate['low'] for rate in rates])
            
            # Check for structure breaks
            recent_high = max(highs[-10:])
            recent_low = min(lows[-10:])
            current_price = rates[-1]['close']
            
            if signal == "BUY":
                if current_price > recent_high:
                    return 80, "Breakout above recent high"
                elif current_price > np.mean(highs[-10:]):
                    return 60, "Above average resistance"
                else:
                    return 30, "No clear structure"
            else:  # SELL
                if current_price < recent_low:
                    return 80, "Breakout below recent low"
                elif current_price < np.mean(lows[-10:]):
                    return 60, "Below average support"
                else:
                    return 30, "No clear structure"
                    
        except Exception as e:
            return 50, f"Structure analysis error: {e}"

class AdaptiveLotSizer:
    """Adaptive position sizing based on confidence and market conditions"""
    
    def __init__(self):
        self.base_lot = 0.01
        self.max_lot = MAX_LOT_SIZE
        
    def calculate_lot_size(self, confidence, account_balance, volatility_ratio=1.0):
        """Calculate adaptive lot size"""
        try:
            # Base lot on confidence
            if confidence >= 90:
                confidence_lot = 0.03
            elif confidence >= 80:
                confidence_lot = 0.02
            else:
                confidence_lot = self.base_lot
            
            # Adjust for volatility
            volatility_adjusted_lot = confidence_lot
            if volatility_ratio > 2.0:  # High volatility - reduce size
                volatility_adjusted_lot *= 0.7
            elif volatility_ratio < 0.5:  # Low volatility - can increase slightly
                volatility_adjusted_lot *= 1.2
            
            # Risk-based calculation (1% risk per trade)
            risk_amount = account_balance * 0.01
            risk_lot = risk_amount / 1000  # Simplified calculation
            
            # Use the most conservative
            final_lot = min(confidence_lot, volatility_adjusted_lot, risk_lot, self.max_lot)
            
            logger.info(f"Adaptive lot sizing: {final_lot:.3f} (confidence: {confidence:.0f}%, vol: {volatility_ratio:.1f})")
            
            return round(final_lot, 2)
            
        except Exception as e:
            logger.error(f"Lot sizing error: {e}")
            return self.base_lot

class ProfitTargetManager:
    """R-multiple profit target system"""
    
    def __init__(self):
        self.r_multiples = {
            'partial': 1.5,    # 1.5R for partial TP
            'full': 2.5,       # 2.5R for full TP
            'breakeven': 1.0    # 1R for break-even
        }
    
    def calculate_profit_levels(self, entry_price, stop_loss, signal):
        """Calculate partial and full profit targets"""
        try:
            risk_distance = abs(entry_price - stop_loss)
            
            if signal == "BUY":
                partial_tp = entry_price + (risk_distance * self.r_multiples['partial'])
                full_tp = entry_price + (risk_distance * self.r_multiples['full'])
                breakeven_level = entry_price + (risk_distance * self.r_multiples['breakeven'])
            else:  # SELL
                partial_tp = entry_price - (risk_distance * self.r_multiples['partial'])
                full_tp = entry_price - (risk_distance * self.r_multiples['full'])
                breakeven_level = entry_price - (risk_distance * self.r_multiples['breakeven'])
            
            return {
                'entry': entry_price,
                'sl': stop_loss,
                'partial_tp': partial_tp,
                'full_tp': full_tp,
                'breakeven': breakeven_level,
                'risk': risk_distance,
                'partial_r': self.r_multiples['partial'],
                'full_r': self.r_multiples['full']
            }
            
        except Exception as e:
            logger.error(f"Profit target calculation error: {e}")
            return None

class IntelligentTradeManager:
    """Level 3 intelligent trade management system"""
    
    def __init__(self):
        self.regime_detector = MarketRegimeDetector()
        self.signal_scorer = SignalScoringEngine()
        self.lot_sizer = AdaptiveLotSizer()
        self.profit_manager = ProfitTargetManager()
        
    def should_execute_trade(self, symbol, signal, confidence, timeframe):
        """Intelligent trade execution decision"""
        try:
            # 1. Check market regime
            regime = self.regime_detector.detect_regime(symbol)
            
            # 2. Only trade trending markets (unless confidence is very high)
            if regime in ["RANGING", "UNKNOWN"] and confidence < 95:
                return False, f"Market regime ({regime}) not suitable for trading"
            
            # 3. Calculate signal score
            score, score_details = self.signal_scorer.calculate_signal_score(symbol, signal, confidence, timeframe)
            
            # 4. Only trade high-quality signals
            if score < 70:
                return False, f"Signal quality too low ({score:.1f} < 70)"
            
            # 5. Check for conflicting signals
            if self._has_conflicting_signal(symbol, signal):
                return False, f"Conflicting signal detected for {symbol}"
            
            logger.info(f"Intelligent trade approval for {symbol} {signal}")
            logger.info(f"   Regime: {regime}")
            logger.info(f"   Score: {score:.1f} ({score_details})")
            
            return True, f"High-quality signal (score: {score:.1f})"
            
        except Exception as e:
            logger.error(f"Intelligent trade decision error: {e}")
            return False, f"Decision error: {e}"
    
    def _has_conflicting_signal(self, symbol, current_signal):
        """Check for conflicting signals on same symbol"""
        try:
            # This would integrate with other timeframes
            # For now, simple check
            return False  # Can be enhanced with MTF analysis
        except Exception:
            return False
