"""
TRADE MEMORY SYSTEM - Persistent Trade History Storage
Handles local JSON storage and MT5 history integration
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class TradeMemorySystem:
    def __init__(self, memory_file="trade_history.json"):
        self.memory_file = memory_file
        self.max_trades = 100  # Keep last 100 trades
        self._ensure_memory_file()
        
    def _ensure_memory_file(self):
        """Create memory file if it doesn't exist"""
        if not os.path.exists(self.memory_file):
            with open(self.memory_file, 'w') as f:
                json.dump([], f)
            logger.info(f"Created trade memory file: {self.memory_file}")
    
    def save_trade(self, symbol: str, direction: str, score: float, 
                   result: str, profit: float, timestamp: str = None):
        """Save a trade result to memory"""
        try:
            if timestamp is None:
                timestamp = datetime.now().isoformat()
            
            trade_data = {
                "symbol": symbol,
                "direction": direction,
                "score": round(score, 3),
                "result": result,
                "profit": round(profit, 2),
                "timestamp": timestamp
            }
            
            # Load existing trades
            trades = self.load_trade_history()
            
            # Add new trade
            trades.append(trade_data)
            
            # Keep only last 100 trades
            if len(trades) > self.max_trades:
                trades = trades[-self.max_trades:]
            
            # Save back to file
            with open(self.memory_file, 'w') as f:
                json.dump(trades, f, indent=2)
            
            logger.info(f"Trade saved: {symbol} {direction} | Score: {score:.3f} | Result: {result} | Profit: ${profit:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to save trade: {e}")
    
    def update_trade_result(self, symbol: str, result: str, profit: float):
        """
        Update the most recent pending ("SIGNAL SENT") record for this symbol
        with its real outcome once the trade actually closes.

        This method never existed before - save_trade() was only ever called
        once, at trade-open time, with result="SIGNAL SENT" and profit=0.0 as
        explicit placeholders ("Will be updated when trade closes" - but
        nothing ever called back to do that update). Every record in this
        file was permanently stuck as "SIGNAL SENT"/$0.00, which means
        get_adaptive_threshold() below - the value the live trade-approval
        gate actually uses - was computing win_rate from data that could
        never register a real win, regardless of how the bot actually
        performed. There's no ticket/ID stored per trade, so this matches by
        symbol + most recent pending entry, which is adequate for a single
        symbol at a time but would need a real key if multiple concurrent
        positions per symbol ever need independent tracking here.
        """
        try:
            trades = self.load_trade_history()
            for trade in reversed(trades):
                if trade.get('symbol') == symbol and trade.get('result') == 'SIGNAL SENT':
                    trade['result'] = result
                    trade['profit'] = round(profit, 2)
                    with open(self.memory_file, 'w') as f:
                        json.dump(trades, f, indent=2)
                    logger.info(f"Trade result updated: {symbol} | Result: {result} | Profit: ${profit:.2f}")
                    return
            logger.warning(f"No pending SIGNAL SENT record found for {symbol} to update")
        except Exception as e:
            logger.error(f"Failed to update trade result: {e}")

    def load_trade_history(self) -> List[Dict[str, Any]]:
        """Load trade history from file"""
        try:
            with open(self.memory_file, 'r') as f:
                trades = json.load(f)
            return trades
        except Exception as e:
            logger.error(f"Failed to load trade history: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Calculate trade statistics"""
        trades = self.load_trade_history()
        
        if not trades:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "avg_score": 0.0,
                "total_profit": 0.0,
                "recent_trades": 0
            }
        
        # Calculate statistics
        total_trades = len(trades)
        wins = sum(1 for trade in trades if trade["result"] == "WIN")
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0.0
        
        avg_score = sum(trade["score"] for trade in trades) / total_trades if total_trades > 0 else 0.0
        total_profit = sum(trade["profit"] for trade in trades)
        
        # Count recent trades (last 24 hours)
        now = datetime.now()
        recent_trades = sum(1 for trade in trades 
                           if datetime.fromisoformat(trade["timestamp"]) > now - timedelta(hours=24))
        
        return {
            "total_trades": total_trades,
            "win_rate": round(win_rate, 1),
            "avg_score": round(avg_score, 3),
            "total_profit": round(total_profit, 2),
            "recent_trades": recent_trades
        }
    
    def get_recent_trades(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent trades"""
        trades = self.load_trade_history()
        return trades[-limit:] if trades else []
    
    def should_use_warmup_mode(self) -> bool:
        """Check if we should use warm-up mode (less than 10 trades)"""
        stats = self.get_statistics()
        return stats["total_trades"] < 10
    
    def get_adaptive_threshold(self) -> float:
        """Get adaptive threshold based on trade history"""
        stats = self.get_statistics()
        
        if stats["total_trades"] < 10:
            # Warm-up mode: lower threshold
            return 0.45
        elif stats["win_rate"] < 40:
            # Poor performance: lower threshold
            return 0.50
        elif stats["win_rate"] > 60:
            # Good performance: normal threshold
            return 0.55
        else:
            # Average performance: normal threshold
            return 0.55
    
    def integrate_mt5_history(self, mt5_connector=None):
        """Optional: Integrate MT5 deal history"""
        if mt5_connector is None:
            try:
                import MetaTrader5 as mt5
                if not mt5.initialize():
                    logger.warning("MT5 not available for history integration")
                    return
            except:
                logger.warning("MT5 not available for history integration")
                return
        
        try:
            # Get deals from last 7 days
            from_date = datetime.now() - timedelta(days=7)
            deals = mt5.history_deals_get(from_date, datetime.now())
            
            if deals:
                for deal in deals:
                    if deal.type == mt5.DEAL_TYPE_BUY or deal.type == mt5.DEAL_TYPE_SELL:
                        # Convert MT5 deal to our format
                        symbol = deal.symbol
                        direction = "BUY" if deal.type == mt5.DEAL_TYPE_BUY else "SELL"
                        profit = deal.profit
                        result = "WIN" if profit > 0 else "LOSS"
                        timestamp = datetime.fromtimestamp(deal.time).isoformat()
                        
                        # Estimate score based on profit (simplified)
                        score = min(0.9, max(0.3, 0.5 + (profit / 100)))
                        
                        self.save_trade(symbol, direction, score, result, profit, timestamp)
                
                logger.info(f"Integrated {len(deals)} MT5 deals into trade memory")
                
        except Exception as e:
            logger.error(f"Failed to integrate MT5 history: {e}")
        finally:
            if 'mt5' in locals():
                mt5.shutdown()

# Global instance
trade_memory = TradeMemorySystem()