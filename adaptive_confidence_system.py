"""
Adaptive Confidence System
LEVEL 10.3: Dynamic confidence threshold management
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AdaptiveConfidenceSystem:
    """
    Adaptive Confidence System
    Dynamically adjusts confidence thresholds based on performance
    """
    
    def __init__(self, base_threshold: float = 75.0, learning_system=None):
        self.base_threshold = base_threshold
        self.learning_system = learning_system
        self.current_threshold = base_threshold
        self.min_threshold = 60.0
        self.max_threshold = 90.0
        
        # Performance tracking
        self.performance_history = []
        self.last_adjustment = datetime.now()
        self.adjustment_interval = timedelta(hours=6)  # Adjust every 6 hours
        
        logger.info("Adaptive Confidence System initialized")
        logger.info(f"Base threshold: {self.base_threshold}%")
        logger.info(f"Range: {self.min_threshold}% - {self.max_threshold}%")
    
    def get_current_threshold(self) -> float:
        """Get current adaptive confidence threshold"""
        try:
            # Check if it's time to adjust
            if datetime.now() - self.last_adjustment > self.adjustment_interval:
                self.adjust_threshold()
            
            return self.current_threshold
            
        except Exception as e:
            logger.error(f"Error getting current threshold: {e}")
            return self.base_threshold
    
    def adjust_threshold(self):
        """Adjust threshold based on recent performance"""
        try:
            if not self.learning_system:
                logger.warning("No learning system available for adaptive adjustment")
                return
            
            # Get recent performance
            recent_perf = self.learning_system.get_recent_performance(20)
            
            if recent_perf['trades'] < 10:
                logger.info("Not enough trades for threshold adjustment")
                return
            
            win_rate = recent_perf['win_rate']
            old_threshold = self.current_threshold
            
            # Adaptive threshold logic
            if win_rate > 70:
                # High performance - be more selective
                self.current_threshold = min(self.max_threshold, self.base_threshold + 10)
                adjustment_reason = "High performance - increasing selectivity"
                
            elif win_rate > 60:
                # Good performance - slight increase
                self.current_threshold = min(self.max_threshold, self.base_threshold + 5)
                adjustment_reason = "Good performance - slight increase"
                
            elif win_rate < 50:
                # Poor performance - be more flexible
                self.current_threshold = max(self.min_threshold, self.base_threshold - 10)
                adjustment_reason = "Poor performance - increasing flexibility"
                
            else:
                # Average performance - maintain base
                self.current_threshold = self.base_threshold
                adjustment_reason = "Average performance - maintaining base"
            
            # Log the adjustment
            if old_threshold != self.current_threshold:
                logger.info(f"Threshold adjusted: {old_threshold:.1f}% -> {self.current_threshold:.1f}% ({adjustment_reason})")
                self.last_adjustment = datetime.now()
                
                # Store performance history
                self.performance_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'win_rate': win_rate,
                    'trades': recent_perf['trades'],
                    'old_threshold': old_threshold,
                    'new_threshold': self.current_threshold,
                    'reason': adjustment_reason
                })
                
                # Keep only last 20 adjustments
                if len(self.performance_history) > 20:
                    self.performance_history = self.performance_history[-20:]
            
        except Exception as e:
            logger.error(f"Error adjusting threshold: {e}")
    
    def check_confidence(self, confidence: float) -> tuple[bool, str]:
        """
        Check if confidence meets current threshold
        Returns (passed, reason)
        """
        try:
            current_threshold = self.get_current_threshold()
            
            if confidence >= current_threshold:
                return True, f"Confidence {confidence:.1f}% >= threshold {current_threshold:.1f}%"
            else:
                return False, f"Confidence {confidence:.1f}% < threshold {current_threshold:.1f}%"
                
        except Exception as e:
            logger.error(f"Error checking confidence: {e}")
            return False, f"Error: {e}"
    
    def get_performance_trend(self) -> str:
        """Analyze performance trend over recent adjustments"""
        try:
            if len(self.performance_history) < 3:
                return "Insufficient data"
            
            recent = self.performance_history[-3:]
            
            # Calculate trend
            win_rates = [adj['win_rate'] for adj in recent]
            thresholds = [adj['new_threshold'] for adj in recent]
            
            if all(win_rates[i] > win_rates[i+1] for i in range(len(win_rates)-1)):
                return "Improving"
            elif all(win_rates[i] < win_rates[i+1] for i in range(len(win_rates)-1)):
                return "Declining"
            else:
                return "Stable"
                
        except Exception as e:
            logger.error(f"Error analyzing trend: {e}")
            return "Unknown"
    
    def get_status_report(self) -> str:
        """Get detailed adaptive confidence status"""
        try:
            current_threshold = self.get_current_threshold()
            trend = self.get_performance_trend()
            
            if self.learning_system:
                recent_perf = self.learning_system.get_recent_performance(20)
                win_rate = recent_perf.get('win_rate', 0)
                trades = recent_perf.get('trades', 0)
            else:
                win_rate = 0
                trades = 0
            
            report = f"""
ADAPTIVE CONFIDENCE SYSTEM STATUS
Current Threshold: {current_threshold:.1f}%
Base Threshold: {self.base_threshold:.1f}%
Range: {self.min_threshold}% - {self.max_threshold}%

Recent Performance:
- Trades: {trades}
- Win Rate: {win_rate:.1f}%
- Trend: {trend}

Last Adjustment: {self.last_adjustment.strftime('%Y-%m-%d %H:%M') if self.last_adjustment else 'Never'}
Adjustment Interval: Every {self.adjustment_interval.total_seconds() / 3600:.0f} hours

Recent Adjustments: {len(self.performance_history)}
            """.strip()
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating status report: {e}")
            return "Error generating status report"
    
    def force_adjustment(self):
        """Force immediate threshold adjustment"""
        try:
            logger.info("Forcing immediate threshold adjustment")
            self.last_adjustment = datetime.now() - timedelta(hours=7)  # Force adjustment
            self.adjust_threshold()
            
        except Exception as e:
            logger.error(f"Error forcing adjustment: {e}")
    
    def reset_to_base(self):
        """Reset threshold to base value"""
        try:
            self.current_threshold = self.base_threshold
            self.last_adjustment = datetime.now()
            logger.info(f"Threshold reset to base: {self.base_threshold:.1f}%")
            
        except Exception as e:
            logger.error(f"Error resetting threshold: {e}")
    
    def get_adjustment_history(self, limit: int = 10) -> list:
        """Get recent adjustment history"""
        try:
            return self.performance_history[-limit:]
        except Exception as e:
            logger.error(f"Error getting adjustment history: {e}")
            return []
