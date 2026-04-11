"""
Elite Trade Override System
LEVEL 10.3: Advanced trade limit management for high-quality signals
"""

import logging
from datetime import datetime, date
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class EliteTradeOverride:
    """
    Elite Trade Override System
    Allows high-quality trades to bypass daily limits
    """
    
    def __init__(self, daily_limit: int = 20):
        self.daily_limit = daily_limit
        self.daily_trades = {}  # Date -> Trade count
        self.elite_trades_today = 0
        self.elite_trades_total = 0
        self.elite_trades_wins = 0
        
        logger.info("Elite Trade Override initialized")
        logger.info(f"Daily limit: {self.daily_limit}")
        logger.info(f"Elite conditions: Confidence >= 85%, Trend aligned, Score >= 0.60")
    
    def get_today_date(self) -> date:
        """Get today's date"""
        return datetime.now().date()
    
    def get_daily_trade_count(self) -> int:
        """Get today's trade count"""
        today = self.get_today_date()
        return self.daily_trades.get(today, 0)
    
    def is_daily_limit_reached(self) -> bool:
        """Check if daily trade limit is reached"""
        return self.get_daily_trade_count() >= self.daily_limit
    
    def check_elite_conditions(self, confidence: float, trend_aligned: bool, score: float) -> bool:
        """Check if trade meets elite conditions"""
        try:
            conditions_met = (
                confidence >= 85.0 and  # High confidence
                trend_aligned and        # Trend aligned
                score >= 0.60           # Good signal quality
            )
            
            if conditions_met:
                logger.info(f"Elite conditions met: Confidence={confidence}%, Trend={trend_aligned}, Score={score}")
            
            return conditions_met
            
        except Exception as e:
            logger.error(f"Error checking elite conditions: {e}")
            return False
    
    def can_execute_trade(self, confidence: float, trend_aligned: bool, score: float) -> tuple[bool, str]:
        """
        Check if trade can be executed
        Returns (can_execute, reason)
        """
        try:
            # Check daily limit
            if not self.is_daily_limit_reached():
                # Normal limit not reached - allow trade
                return True, "Normal trade - daily limit not reached"
            
            # Daily limit reached - check elite conditions
            if self.check_elite_conditions(confidence, trend_aligned, score):
                # Elite conditions met - override limit
                self.elite_trades_today += 1
                self.elite_trades_total += 1
                
                reason = f"Elite trade override activated - executing beyond daily limit (Elite trade #{self.elite_trades_today})"
                logger.warning(f"ELITE OVERRIDE: {reason}")
                return True, reason
            
            # Daily limit reached and elite conditions not met
            return False, f"Daily limit reached ({self.get_daily_trade_count()}/{self.daily_limit}) and elite conditions not met"
            
        except Exception as e:
            logger.error(f"Error checking trade execution: {e}")
            return False, f"Error: {e}"
    
    def record_trade(self, confidence: float, trend_aligned: bool, score: float, was_profitable: bool):
        """Record a trade and update statistics"""
        try:
            today = self.get_today_date()
            
            # Update daily count
            self.daily_trades[today] = self.daily_trades.get(today, 0) + 1
            
            # Update elite statistics if it was an elite trade
            if self.check_elite_conditions(confidence, trend_aligned, score):
                if was_profitable:
                    self.elite_trades_wins += 1
                
                logger.info(f"Elite trade recorded: Profitable={was_profitable}, Elite wins={self.elite_trades_wins}/{self.elite_trades_total}")
            
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get elite trade statistics"""
        try:
            elite_win_rate = 0.0
            if self.elite_trades_total > 0:
                elite_win_rate = (self.elite_trades_wins / self.elite_trades_total) * 100
            
            return {
                'daily_limit': self.daily_limit,
                'today_trades': self.get_daily_trade_count(),
                'daily_limit_reached': self.is_daily_limit_reached(),
                'elite_trades_today': self.elite_trades_today,
                'elite_trades_total': self.elite_trades_total,
                'elite_trades_wins': self.elite_trades_wins,
                'elite_win_rate': round(elite_win_rate, 2),
                'recent_days': len(self.daily_trades)
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def reset_daily_stats(self):
        """Reset daily statistics (call at start of new day)"""
        today = self.get_today_date()
        
        # Keep only recent days (last 7 days)
        recent_trades = {}
        cutoff_date = today - datetime.timedelta(days=7)
        
        for trade_date, count in self.daily_trades.items():
            if trade_date >= cutoff_date:
                recent_trades[trade_date] = count
        
        self.daily_trades = recent_trades
        self.elite_trades_today = 0
        
        logger.info("Daily elite trade statistics reset")
    
    def get_status_report(self) -> str:
        """Get detailed status report"""
        stats = self.get_statistics()
        
        report = f"""
ELITE TRADE OVERRIDE STATUS
Daily Limit: {stats.get('daily_limit', 'N/A')}
Today's Trades: {stats.get('today_trades', 'N/A')}
Limit Reached: {'Yes' if stats.get('daily_limit_reached', False) else 'No'}

Elite Trades Today: {stats.get('elite_trades_today', 0)}
Elite Trades Total: {stats.get('elite_trades_total', 0)}
Elite Win Rate: {stats.get('elite_win_rate', 0):.1f}%

Elite Conditions:
- Confidence >= 85%
- Trend Aligned: True
- Score >= 0.60
        """.strip()
        
        return report
