"""
Advanced Learning System
LEVEL 10.3: Fixed and enhanced trade learning and scoring
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
import os

logger = logging.getLogger(__name__)

class AdvancedLearningSystem:
    """
    Advanced Learning System for Trade Performance
    Fixed scoring and proper trade memory management
    """
    
    def __init__(self, memory_file: str = "trade_learning_memory.json"):
        self.memory_file = memory_file
        self.trade_memory = {
            "total_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": 0.0,
            "recent_trades": [],  # Last 50 trades
            "daily_performance": {},  # Date -> performance
            "last_updated": None
        }
        
        # Load existing memory
        self.load_memory()
        
        logger.info("Advanced Learning System initialized")
        logger.info(f"Memory file: {self.memory_file}")
        logger.info(f"Current stats: {self.trade_memory['total_trades']} trades, {self.trade_memory['win_rate']:.1f}% win rate")
    
    def load_memory(self):
        """Load trade memory from file"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    loaded_memory = json.load(f)
                    
                # Validate and merge with defaults
                for key, default_value in self.trade_memory.items():
                    if key in loaded_memory:
                        self.trade_memory[key] = loaded_memory[key]
                
                logger.info(f"Loaded trade memory: {self.trade_memory['total_trades']} trades")
            else:
                logger.info("No existing memory file found, starting fresh")
                
        except Exception as e:
            logger.error(f"Error loading memory: {e}")
    
    def save_memory(self):
        """Save trade memory to file"""
        try:
            self.trade_memory['last_updated'] = datetime.now().isoformat()
            
            with open(self.memory_file, 'w') as f:
                json.dump(self.trade_memory, f, indent=2)
                
            logger.debug("Trade memory saved")
            
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
    
    def add_trade_result(self, symbol: str, profit: float, score: float, confidence: float, timestamp: datetime = None):
        """Add a trade result and update learning"""
        try:
            if timestamp is None:
                timestamp = datetime.now()
            
            # Create trade record
            trade_record = {
                "symbol": symbol,
                "profit": profit,
                "score": score,
                "confidence": confidence,
                "timestamp": timestamp.isoformat(),
                "date": timestamp.date().isoformat(),
                "was_profitable": profit > 0
            }
            
            # Update basic statistics
            self.trade_memory['total_trades'] += 1
            
            if profit > 0:
                self.trade_memory['wins'] += 1
            else:
                self.trade_memory['losses'] += 1
            
            # Recalculate win rate
            if self.trade_memory['total_trades'] > 0:
                self.trade_memory['win_rate'] = (self.trade_memory['wins'] / self.trade_memory['total_trades']) * 100
            
            # Add to recent trades (keep last 50)
            self.trade_memory['recent_trades'].append(trade_record)
            if len(self.trade_memory['recent_trades']) > 50:
                self.trade_memory['recent_trades'] = self.trade_memory['recent_trades'][-50:]
            
            # Update daily performance
            trade_date = timestamp.date().isoformat()
            if trade_date not in self.trade_memory['daily_performance']:
                self.trade_memory['daily_performance'][trade_date] = {
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "profit": 0.0
                }
            
            daily_perf = self.trade_memory['daily_performance'][trade_date]
            daily_perf['trades'] += 1
            daily_perf['profit'] += profit
            
            if profit > 0:
                daily_perf['wins'] += 1
            else:
                daily_perf['losses'] += 1
            
            # Save memory
            self.save_memory()
            
            logger.info(f"Trade recorded: {symbol} P&L=${profit:+.2f}, Score={score:.2f}, Win Rate={self.trade_memory['win_rate']:.1f}%")
            
        except Exception as e:
            logger.error(f"Error adding trade result: {e}")
    
    def calculate_enhanced_score(self, signal_quality: float, trend_strength: float) -> float:
        """
        Calculate enhanced score with learning system
        Fixed formula that never defaults to 0
        """
        try:
            # Get current win rate (default to 50% if no history)
            win_rate = self.trade_memory['win_rate']
            if self.trade_memory['total_trades'] == 0:
                win_rate = 50.0  # Default assumption for new system
            
            # Convert win rate to 0-1 scale
            win_rate_factor = win_rate / 100.0
            
            # Enhanced scoring formula
            score = (
                0.4 * signal_quality +    # Signal quality (40%)
                0.3 * trend_strength +   # Trend strength (30%)
                0.3 * win_rate_factor   # Historical win rate (30%)
            )
            
            # Ensure score is never 0 unless data is truly missing
            if signal_quality > 0 or trend_strength > 0 or win_rate > 0:
                score = max(0.1, score)  # Minimum 0.1 if we have some data
            else:
                score = 0.0  # Only 0 if all data is missing
            
            logger.info(f"Enhanced score calculation: Signal={signal_quality:.2f}, Trend={trend_strength:.2f}, WinRate={win_rate:.1f}% -> Score={score:.3f}")
            
            return round(score, 3)
            
        except Exception as e:
            logger.error(f"Error calculating enhanced score: {e}")
            return 0.1  # Safe fallback, not 0
    
    def get_recent_performance(self, trades: int = 20) -> Dict[str, Any]:
        """Get recent performance statistics"""
        try:
            recent_trades = self.trade_memory['recent_trades'][-trades:]
            
            if not recent_trades:
                return {
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_rate': 0.0,
                    'total_profit': 0.0,
                    'avg_profit': 0.0
                }
            
            wins = sum(1 for trade in recent_trades if trade['was_profitable'])
            losses = len(recent_trades) - wins
            total_profit = sum(trade['profit'] for trade in recent_trades)
            
            return {
                'trades': len(recent_trades),
                'wins': wins,
                'losses': losses,
                'win_rate': (wins / len(recent_trades)) * 100 if recent_trades else 0.0,
                'total_profit': total_profit,
                'avg_profit': total_profit / len(recent_trades) if recent_trades else 0.0
            }
            
        except Exception as e:
            logger.error(f"Error getting recent performance: {e}")
            return {}
    
    def get_daily_summary(self, target_date: datetime.date = None) -> Dict[str, Any]:
        """Get daily performance summary"""
        try:
            if target_date is None:
                target_date = datetime.now().date()
            
            date_str = target_date.isoformat()
            
            if date_str not in self.trade_memory['daily_performance']:
                return {
                    'date': date_str,
                    'trades': 0,
                    'wins': 0,
                    'losses': 0,
                    'win_rate': 0.0,
                    'profit': 0.0
                }
            
            daily_data = self.trade_memory['daily_performance'][date_str]
            
            return {
                'date': date_str,
                'trades': daily_data['trades'],
                'wins': daily_data['wins'],
                'losses': daily_data['losses'],
                'win_rate': (daily_data['wins'] / daily_data['trades']) * 100 if daily_data['trades'] > 0 else 0.0,
                'profit': daily_data['profit']
            }
            
        except Exception as e:
            logger.error(f"Error getting daily summary: {e}")
            return {}
    
    def get_adaptive_threshold(self) -> float:
        """Get adaptive threshold based on performance"""
        try:
            recent_perf = self.get_recent_performance(20)
            
            if recent_perf['trades'] < 10:
                return 0.55  # Warm-up mode
            
            win_rate = recent_perf['win_rate']
            
            # Adaptive threshold logic
            if win_rate > 70:
                threshold = 0.75
                logger.info(f"High performance ({win_rate:.1f}% win rate) -> threshold {threshold}")
            elif win_rate > 60:
                threshold = 0.65
                logger.info(f"Good performance ({win_rate:.1f}% win rate) -> threshold {threshold}")
            elif win_rate < 50:
                threshold = 0.50
                logger.info(f"Poor performance ({win_rate:.1f}% win rate) -> threshold {threshold}")
            else:
                threshold = 0.55
                logger.info(f"Average performance ({win_rate:.1f}% win rate) -> threshold {threshold}")
            
            return threshold
            
        except Exception as e:
            logger.error(f"Error calculating adaptive threshold: {e}")
            return 0.55
    
    def get_status_report(self) -> str:
        """Get detailed learning system status"""
        recent_perf = self.get_recent_performance(20)
        today_summary = self.get_daily_summary()
        
        report = f"""
ADVANCED LEARNING SYSTEM STATUS
Overall Statistics:
- Total Trades: {self.trade_memory['total_trades']}
- Total Wins: {self.trade_memory['wins']}
- Total Losses: {self.trade_memory['losses']}
- Overall Win Rate: {self.trade_memory['win_rate']:.1f}%

Recent Performance (Last 20 trades):
- Trades: {recent_perf.get('trades', 0)}
- Win Rate: {recent_perf.get('win_rate', 0):.1f}%
- Total Profit: ${recent_perf.get('total_profit', 0):+.2f}
- Avg Profit: ${recent_perf.get('avg_profit', 0):+.2f}

Today's Performance:
- Trades: {today_summary.get('trades', 0)}
- Win Rate: {today_summary.get('win_rate', 0):.1f}%
- Profit: ${today_summary.get('profit', 0):+.2f}

Adaptive Threshold: {self.get_adaptive_threshold():.2f}
        """.strip()
        
        return report
    
    def reset_memory(self):
        """Reset all learning memory"""
        try:
            self.trade_memory = {
                "total_trades": 0,
                "wins": 0,
                "losses": 0,
                "win_rate": 0.0,
                "recent_trades": [],
                "daily_performance": {},
                "last_updated": None
            }
            
            self.save_memory()
            logger.warning("Learning memory reset")
            
        except Exception as e:
            logger.error(f"Error resetting memory: {e}")
