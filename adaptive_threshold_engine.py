"""
🔥 LEVEL 10.2: ADAPTIVE THRESHOLD ENGINE
Intelligent trade scoring that adapts to performance
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class AdaptiveThresholdEngine:
    """
    🧠 INTELLIGENT THRESHOLD MANAGER
    Adapts trade thresholds based on:
    - Recent win rate
    - Recent PnL
    - Current drawdown
    - Performance trends
    """
    
    def __init__(self):
        # 🔧 CORE VARIABLES - REALISTIC VALUES
        self.BASE_THRESHOLD = 0.60  # 🔥 LOWERED from 0.65 to match bot scores
        self.MIN_THRESHOLD = 0.50   # 🔥 LOWERED from 0.55
        self.MAX_THRESHOLD = 0.75   # 🔥 LOWERED from 0.80
        
        # 📊 TRACKING VARIABLES
        self.trade_history = []
        self.daily_pnl = 0.0
        self.current_drawdown = 0.0
        self.last_update = datetime.now()
        
        # 🧠 INTELLIGENCE SETTINGS
        self.min_trades_for_analysis = 10
        self.recent_trades_window = 30
        self.drawdown_warning_5 = 5.0  # 5% drawdown
        self.drawdown_warning_10 = 10.0  # 10% drawdown
        
        logger.info("🧠 Adaptive Threshold Engine initialized")
        logger.info(f"📊 Base threshold: {self.BASE_THRESHOLD}")
        logger.info(f"📈 Range: {self.MIN_THRESHOLD} - {self.MAX_THRESHOLD}")
    
    def add_trade_result(self, symbol: str, profit: float, score: float, timestamp: datetime = None):
        """Add trade result to history for analysis"""
        if timestamp is None:
            timestamp = datetime.now()
            
        trade_record = {
            'symbol': symbol,
            'profit': profit,
            'score': score,
            'timestamp': timestamp,
            'date': timestamp.date()
        }
        
        self.trade_history.append(trade_record)
        
        # Update daily PnL
        if timestamp.date() == datetime.now().date():
            self.daily_pnl += profit
        
        # Keep history manageable (last 500 trades)
        if len(self.trade_history) > 500:
            self.trade_history = self.trade_history[-500:]
        
        logger.debug(f"📊 Trade added: {symbol} | P&L: ${profit:+.2f} | Score: {score:.2f}")
    
    def calculate_dynamic_threshold(self, trade_history: List[Dict] = None) -> float:
        """
        🧠 STEP 2: PERFORMANCE ANALYSIS FUNCTION
        Calculate intelligent threshold based on recent performance
        """
        if trade_history is None:
            trade_history = self.trade_history
            
        if len(trade_history) < self.min_trades_for_analysis:
            logger.info(f"📊 Not enough trades ({len(trade_history)} < {self.min_trades_for_analysis}) - using WARM-UP mode")
            return 0.55  # 🔥 WARM-UP MODE: Allow bot to start trading
        
        # Get recent trades for analysis
        recent_trades = trade_history[-self.recent_trades_window:]
        
        # Calculate performance metrics
        wins = sum(1 for t in recent_trades if t['profit'] > 0)
        losses = sum(1 for t in recent_trades if t['profit'] <= 0)
        win_rate = wins / len(recent_trades)
        
        total_profit = sum(t['profit'] for t in recent_trades)
        avg_profit = total_profit / len(recent_trades)
        
        # Calculate trend (last 10 vs previous 10)
        if len(recent_trades) >= 20:
            recent_10 = recent_trades[-10:]
            previous_10 = recent_trades[-20:-10]
            
            recent_profit = sum(t['profit'] for t in recent_10)
            previous_profit = sum(t['profit'] for t in previous_10)
            
            improving = recent_profit > previous_profit
        else:
            improving = True
        
        # 🧠 DYNAMIC THRESHOLD CALCULATION
        threshold = self.BASE_THRESHOLD
        
        # 🔻 LOSING → BECOME STRICTER
        if win_rate < 0.45:
            threshold += 0.05
            logger.info(f"🔻 Low win rate ({win_rate:.2f}) - increasing threshold")
        
        if total_profit < 0:
            threshold += 0.03
            logger.info(f"🔻 Negative PnL (${total_profit:.2f}) - increasing threshold")
        
        if not improving:
            threshold += 0.02
            logger.info(f"🔻 Performance declining - increasing threshold")
        
        # 🔺 WINNING → ALLOW MORE TRADES
        if win_rate > 0.60:
            threshold -= 0.05
            logger.info(f"🔺 High win rate ({win_rate:.2f}) - decreasing threshold")
        
        if total_profit > 50:  # $50+ profit
            threshold -= 0.02
            logger.info(f"🔺 Strong profit (${total_profit:.2f}) - decreasing threshold")
        
        if improving:
            threshold -= 0.01
            logger.info(f"🔺 Performance improving - decreasing threshold")
        
        # Clamp values
        threshold = max(self.MIN_THRESHOLD, min(self.MAX_THRESHOLD, threshold))
        
        # 📊 STEP 4: DEBUG LOG (IMPORTANT)
        logger.info(f"""
🧠 DYNAMIC THRESHOLD UPDATE
   Recent Trades: {len(recent_trades)}
   Win Rate: {win_rate:.2f} ({wins}/{len(recent_trades)})
   Recent PnL: ${total_profit:+.2f}
   Avg Profit: ${avg_profit:+.2f}
   Trend: {'Improving' if improving else 'Declining'}
   Threshold: {threshold:.3f} ({threshold - self.BASE_THRESHOLD:+.3f})
   Mode: {'Selective' if threshold > self.BASE_THRESHOLD else 'Aggressive'}
        """.strip())
        
        return round(threshold, 3)
    
    def adjust_for_drawdown(self, threshold: float, current_drawdown: float) -> float:
        """
        🔥 STEP 5: DRAWDOWN INTELLIGENCE (ELITE MODE)
        Adjust threshold based on current drawdown
        """
        original_threshold = threshold
        
        if current_drawdown > self.drawdown_warning_10:  # 10% drawdown
            threshold += 0.10
            logger.warning(f"🚨 CRITICAL DRAWDOWN ({current_drawdown:.1f}%) - threshold +0.10")
        elif current_drawdown > self.drawdown_warning_5:  # 5% drawdown
            threshold += 0.05
            logger.warning(f"⚠️ MODERATE DRAWDOWN ({current_drawdown:.1f}%) - threshold +0.05")
        
        # Ensure we don't exceed max threshold
        threshold = min(threshold, self.MAX_THRESHOLD)
        
        if threshold != original_threshold:
            logger.info(f" Drawdown adjustment: {original_threshold:.3f} → {threshold:.3f}")
        
        return threshold
    
    def get_intelligent_threshold(self) -> float:
        """
        MAIN INTELLIGENCE FUNCTION
        Get the current intelligent threshold using trade memory system
        """
        # Use trade memory system for intelligent threshold
        try:
            from trade_memory_system import trade_memory
            return trade_memory.get_adaptive_threshold()
        except:
            # Fallback to original logic
            return self.calculate_dynamic_threshold()
    
    def update_performance_metrics(self, daily_pnl: float = None, current_drawdown: float = None):
        """Update performance metrics"""
        if daily_pnl is not None:
            self.daily_pnl = daily_pnl
        
        if current_drawdown is not None:
            self.current_drawdown = current_drawdown
        
        self.last_update = datetime.now()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary"""
        if not self.trade_history:
            return {
                'total_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'current_threshold': self.BASE_THRESHOLD,
                'mode': 'Insufficient Data'
            }
        
        recent_trades = self.trade_history[-self.recent_trades_window:]
        wins = sum(1 for t in recent_trades if t['profit'] > 0)
        win_rate = wins / len(recent_trades)
        total_pnl = sum(t['profit'] for t in recent_trades)
        
        current_threshold = self.get_intelligent_threshold()
        
        if current_threshold > self.BASE_THRESHOLD:
            mode = "Selective"
        elif current_threshold < self.BASE_THRESHOLD:
            mode = "Aggressive"
        else:
            mode = "Normal"
        
        return {
            'total_trades': len(self.trade_history),
            'recent_trades': len(recent_trades),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'daily_pnl': self.daily_pnl,
            'current_drawdown': self.current_drawdown,
            'current_threshold': current_threshold,
            'base_threshold': self.BASE_THRESHOLD,
            'mode': mode,
            'last_update': self.last_update
        }
    
    def reset_daily_metrics(self):
        """Reset daily metrics (call at start of new day)"""
        self.daily_pnl = 0.0
        logger.info("📅 Daily metrics reset")
    
    def should_trade(self, score: float) -> tuple[bool, str]:
        """
        🎯 DECISION ENGINE
        Returns whether to trade and the reasoning
        """
        threshold = self.get_intelligent_threshold()
        
        if score >= threshold:
            return True, f"✅ Trade approved: Score {score:.2f} ≥ Threshold {threshold:.2f}"
        else:
            return False, f"❌ Trade rejected: Score {score:.2f} < Threshold {threshold:.2f}"
