"""
LEVEL 9: INTEGRATED ANALYTICS MODULE
Adds real-time analytics directly to your existing trading bot
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
import json
import logging

logger = logging.getLogger(__name__)

class IntegratedAnalytics:
    """LEVEL 9: Analytics integrated into existing trading bot"""
    
    def __init__(self):
        self.connected = False
        self.last_report = None
        self.trade_history = []
        self.daily_stats = {}
        self.connect_mt5()
    
    def connect_mt5(self):
        """Connect to MetaTrader 5"""
        try:
            if not mt5.initialize():
                logger.warning("❌ Failed to initialize MT5 for analytics")
                return False
            
            # Check if already logged in
            account_info = mt5.account_info()
            if account_info:
                logger.info("✅ Connected to MT5 Analytics Engine")
                self.connected = True
                return True
            else:
                logger.warning("❌ Not logged into MT5 for analytics")
                return False
                
        except Exception as e:
            logger.warning(f"❌ MT5 analytics connection error: {e}")
            return False
    
    def get_last_6_days_trades(self):
        """Fetch last 6 days of trade data"""
        if not self.connected:
            return []
        
        try:
            end = datetime.now()
            start = end - timedelta(days=6)
            
            # Get all deals in the last 6 days
            deals = mt5.history_deals_get(start, end)
            
            if deals is None:
                return []
            
            trades = []
            for deal in deals:
                # Only include closed trades (entry == 1 means exit/in)
                if deal.entry == 1 and deal.profit != 0:  # Excluding deposits/withdrawals
                    trades.append({
                        "symbol": deal.symbol,
                        "profit": deal.profit,
                        "volume": deal.volume,
                        "time": datetime.fromtimestamp(deal.time),
                        "price": deal.price
                    })
            
            return trades
            
        except Exception as e:
            logger.error(f"❌ Error fetching trades: {e}")
            return []
    
    def generate_performance_report(self):
        """Generate performance report for console display"""
        trades = self.get_last_6_days_trades()
        
        if not trades:
            return {
                "total_profit": 0,
                "total_trades": 0,
                "win_rate": 0,
                "best_day": "No trades",
                "worst_day": "No trades",
                "daily_summary": {}
            }
        
        try:
            # Basic calculations
            total_profit = sum(t["profit"] for t in trades)
            wins = [t for t in trades if t["profit"] > 0]
            win_rate = (len(wins) / len(trades)) * 100 if trades else 0
            
            # Daily grouping
            daily = {}
            for t in trades:
                day = t["time"].strftime("%Y-%m-%d")
                daily.setdefault(day, {"profit": 0, "trades": 0})
                daily[day]["profit"] += t["profit"]
                daily[day]["trades"] += 1
            
            # Best and worst days
            daily_profits = {day: data["profit"] for day, data in daily.items()}
            best_day = max(daily_profits.items(), key=lambda x: x[1]) if daily_profits else ("No trades", 0)
            worst_day = min(daily_profits.items(), key=lambda x: x[1]) if daily_profits else ("No trades", 0)
            
            # Create daily summary string
            daily_summary = {}
            for day, data in daily.items():
                profit_str = f"${data['profit']:.2f}"
                trades_str = f"{data['trades']} trades"
                daily_summary[day] = f"{profit_str} ({trades_str})"
            
            return {
                "total_profit": round(total_profit, 2),
                "total_trades": len(trades),
                "win_rate": round(win_rate, 1),
                "best_day": f"{best_day[0]} (${best_day[1]:.2f})",
                "worst_day": f"{worst_day[0]} (${worst_day[1]:.2f})",
                "daily_summary": daily_summary
            }
            
        except Exception as e:
            logger.error(f"❌ Error generating report: {e}")
            return None
    
    def print_performance_dashboard(self):
        """Print analytics dashboard to console"""
        print("\n" + "="*60)
        print("📊 LEVEL 9: NYX AI PERFORMANCE DASHBOARD")
        print("="*60)
        
        report = self.generate_performance_report()
        
        if not report:
            print("❌ Unable to generate performance report")
            return
        
        # Main metrics
        profit_color = "🟢" if report["total_profit"] >= 0 else "🔴"
        print(f"\n💰 Total Profit/Loss: {profit_color} ${report['total_profit']}")
        print(f"📈 Total Trades: {report['total_trades']}")
        print(f"🎯 Win Rate: {report['win_rate']}%")
        print(f"🏆 Best Day: {report['best_day']}")
        print(f"💀 Worst Day: {report['worst_day']}")
        
        # Daily breakdown
        if report["daily_summary"]:
            print(f"\n📅 Daily Breakdown:")
            for day, summary in report["daily_summary"].items():
                print(f"   {day}: {summary}")
        
        print("\n" + "="*60)
    
    def log_trade_execution(self, symbol, signal, confidence, entry_price, sl, tp, lot_size, success):
        """Log trade execution for analytics tracking"""
        trade_log = {
            "timestamp": datetime.now(),
            "symbol": symbol,
            "signal": signal,
            "confidence": confidence,
            "entry_price": entry_price,
            "sl": sl,
            "tp": tp,
            "lot_size": lot_size,
            "success": success
        }
        
        # Add to trade history
        self.trade_history.append(trade_log)
        
        # Keep only last 100 trades in memory
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]
        
        # Log to file
        try:
            with open("trade_log.json", "a") as f:
                json.dump(trade_log, f, default=str)
                f.write("\n")
        except Exception as e:
            logger.error(f"❌ Error logging trade: {e}")
    
    def get_hourly_summary(self):
        """Get summary of last hour's activity"""
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_trades = [t for t in self.trade_history if t["timestamp"] > one_hour_ago]
        
        if not recent_trades:
            return "No trades in the last hour"
        
        executed = sum(1 for t in recent_trades if t["success"])
        total = len(recent_trades)
        
        return f"Last hour: {executed}/{total} trades executed ({executed/total*100:.1f}% success rate)"
    
    def print_quick_stats(self):
        """Print quick stats for console display"""
        report = self.generate_performance_report()
        
        if report:
            profit_color = "🟢" if report["total_profit"] >= 0 else "🔴"
            print(f"📊 6-Day P&L: {profit_color} ${report['total_profit']} | "
                  f"Trades: {report['total_trades']} | "
                  f"Win Rate: {report['win_rate']}% | "
                  f"{self.get_hourly_summary()}")

# Global analytics instance
analytics = IntegratedAnalytics()
