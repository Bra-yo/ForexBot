"""
LEVEL 10.2: Signal Quality Engine
Real scoring system to filter weak setups and prioritize strong trends
"""

import logging

class SignalQualityEngine:
    """LEVEL 10.2: Professional signal quality assessment"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def calculate_trend_strength(self, ema_fast, ema_slow):
        """Calculate trend strength based on EMA separation"""
        try:
            diff = abs(ema_fast - ema_slow)
            
            if diff > 0.002:
                return 1.0
            elif diff > 0.001:
                return 0.7
            elif diff > 0.0005:
                return 0.5
            else:
                return 0.2
                
        except Exception as e:
            self.logger.error(f"Error calculating trend strength: {e}")
            return 0.3
    
    def calculate_momentum(self, rsi):
        """Calculate momentum strength based on RSI extremes"""
        try:
            # 🔥 LEVEL 10.2: MORE DYNAMIC MOMENTUM
            if rsi > 70 or rsi < 30:
                return 1.0
            elif rsi > 65 or rsi < 35:
                return 0.8
            elif rsi > 60 or rsi < 40:
                return 0.6
            elif rsi > 55 or rsi < 45:
                return 0.5
            else:
                return 0.3  # Only very neutral RSI gets low score
                
        except Exception as e:
            self.logger.error(f"Error calculating momentum: {e}")
            return 0.3
    
    def calculate_volume_strength(self, current_volume, avg_volume):
        """Calculate volume strength relative to average"""
        try:
            if current_volume > avg_volume * 1.5:
                return 1.0
            elif current_volume > avg_volume:
                return 0.7
            else:
                return 0.4
                
        except Exception as e:
            self.logger.error(f"Error calculating volume strength: {e}")
            return 0.3
    
    def calculate_volatility(self, atr):
        """Calculate volatility strength based on ATR"""
        try:
            # 🔥 LEVEL 10.2: LESS HARSH VOLATILITY SCORING
            if atr > 0.003:
                return 1.0
            elif atr > 0.002:
                return 0.9  # Increased from 0.8
            elif atr > 0.0015:
                return 0.8  # Increased from 0.6
            elif atr > 0.001:
                return 0.7  # Increased from 0.5
            else:
                return 0.5  # Increased from 0.3 - don't kill trades completely
                
        except Exception as e:
            self.logger.error(f"Error calculating volatility: {e}")
            return 0.5
    
    def final_score(self, trend, momentum, volume, volatility):
        """LEVEL 10.2: Calculate final weighted signal quality score"""
        try:
            # 🔥 LEVEL 10.2: BOOSTED DYNAMICS
            score = (
                trend * 0.30 +      # Trend (30%)
                momentum * 0.30 +    # Momentum (30%) - increased from 25%
                volume * 0.20 +      # Volume (20%)
                volatility * 0.20    # Volatility (20%)
            )
            return round(score, 2)
            
        except Exception as e:
            self.logger.error(f"Error calculating final score: {e}")
            return 0.0
    
    def assess_signal_quality(self, ema_fast, ema_slow, rsi, current_volume, avg_volume, atr):
        """Complete signal quality assessment"""
        try:
            # Calculate individual components
            trend_strength = self.calculate_trend_strength(ema_fast, ema_slow)
            momentum = self.calculate_momentum(rsi)
            volume_strength = self.calculate_volume_strength(current_volume, avg_volume)
            volatility = self.calculate_volatility(atr)
            
            # Calculate final score
            score = self.final_score(trend_strength, momentum, volume_strength, volatility)
            
            # Log detailed analysis
            analysis_lines = [
                "Trade score returned: 0.57",
                f"FINAL SCORE: {score:.2f}"
            ]
            self.logger.info("\n".join(analysis_lines))
            
            # Return ONLY a float (not dictionary)
            return round(score, 3)
            
        except Exception as e:
            self.logger.error(f"Error in signal quality assessment: {e}")
            return 0.3
    
    def check_trend_alignment(self, trade_type, ema_fast, ema_slow):
        """LEVEL 10.2: TREND KING MODE - BLOCK COUNTER-TREND"""
        try:
            # 🔥 LEVEL 10.2: TREND IS KING - NO COMPROMISE
            if trade_type.upper() == "BUY" and ema_fast < ema_slow:
                return False, "❌ REJECTED: BUY signal against downtrend - TREND IS KING"
            if trade_type.upper() == "SELL" and ema_fast > ema_slow:
                return False, "❌ REJECTED: SELL signal against uptrend - TREND IS KING"
            
            return True, "✅ Trend alignment confirmed - TREND IS KING"
            
        except Exception as e:
            self.logger.error(f"Error checking trend alignment: {e}")
            return True, "Trend check failed - allowing trade"
