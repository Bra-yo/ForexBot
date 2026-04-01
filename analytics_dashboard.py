#!/usr/bin/env python3
"""
LEVEL 9: NYX AI ANALYTICS DASHBOARD
Real-time performance analytics from MT5 trade history
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
import json
from flask import Flask, render_template, jsonify
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)

class AnalyticsEngine:
    """LEVEL 9: Real-time analytics engine for Nyx AI trading performance"""
    
    def __init__(self):
        self.connected = False
        self.connect_mt5()
    
    def connect_mt5(self):
        """Connect to MetaTrader 5"""
        try:
            if not mt5.initialize():
                print("❌ Failed to initialize MT5")
                return False
            
            # Login to account (using demo credentials)
            account = 5048146647
            password = ""
            server = "MetaQuotes-Demo"
            
            authorized = mt5.login(account, password=password, server=server)
            if authorized:
                print("✅ Connected to MT5 Analytics Engine")
                self.connected = True
                return True
            else:
                print("❌ Failed to login to MT5")
                return False
                
        except Exception as e:
            print(f"❌ MT5 connection error: {e}")
            return False
    
    def get_last_6_days_trades(self):
        """🧩 STEP 2: Fetch last 6 days of trade data from MT5"""
        if not self.connected:
            return []
        
        try:
            end = datetime.now()
            start = end - timedelta(days=6)
            
            print(f"📊 Fetching trades from {start.date()} to {end.date()}")
            
            # Get all deals in the last 6 days
            deals = mt5.history_deals_get(start, end)
            
            if deals is None:
                print("❌ No deals found")
                return []
            
            print(f"📈 Found {len(deals)} total deals")
            
            trades = []
            for deal in deals:
                # Only include closed trades (entry == 1 means exit/in)
                if deal.entry == 1 and deal.profit != 0:  # Excluding deposits/withdrawals
                    trades.append({
                        "symbol": deal.symbol,
                        "profit": deal.profit,
                        "volume": deal.volume,
                        "time": datetime.fromtimestamp(deal.time),
                        "price": deal.price,
                        "commission": deal.commission if hasattr(deal, 'commission') else 0,
                        "swap": deal.swap if hasattr(deal, 'swap') else 0
                    })
            
            print(f"✅ Found {len(trades)} closed trades")
            return trades
            
        except Exception as e:
            print(f"❌ Error fetching trades: {e}")
            return []
    
    def generate_6day_report(self, trades):
        """📊 STEP 3: Analyze trade data and generate performance report"""
        if not trades:
            return {
                "total_profit": 0,
                "total_trades": 0,
                "win_rate": 0,
                "avg_win": 0,
                "avg_loss": 0,
                "best_day": (datetime.now().date(), 0),
                "worst_day": (datetime.now().date(), 0),
                "daily": {},
                "profit_factor": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0
            }
        
        try:
            # Basic calculations
            total_profit = sum(t["profit"] for t in trades)
            wins = [t for t in trades if t["profit"] > 0]
            losses = [t for t in trades if t["profit"] <= 0]
            
            win_rate = (len(wins) / len(trades)) * 100 if trades else 0
            
            avg_win = sum(t["profit"] for t in wins) / len(wins) if wins else 0
            avg_loss = sum(t["profit"] for t in losses) / len(losses) if losses else 0
            
            # 📅 Daily grouping
            daily = {}
            for t in trades:
                day = t["time"].date()
                daily.setdefault(day, {"profit": 0, "trades": 0})
                daily[day]["profit"] += t["profit"]
                daily[day]["trades"] += 1
            
            # Best and worst days
            daily_profits = {day: data["profit"] for day, data in daily.items()}
            best_day = max(daily_profits.items(), key=lambda x: x[1]) if daily_profits else (datetime.now().date(), 0)
            worst_day = min(daily_profits.items(), key=lambda x: x[1]) if daily_profits else (datetime.now().date(), 0)
            
            # Advanced metrics
            total_wins = sum(t["profit"] for t in wins)
            total_losses = abs(sum(t["profit"] for t in losses)) if losses else 1
            profit_factor = total_wins / total_losses if total_losses > 0 else 0
            
            # Simple Sharpe ratio (annualized)
            if len(trades) > 1:
                returns = [t["profit"] for t in trades]
                avg_return = sum(returns) / len(returns)
                std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
                sharpe_ratio = (avg_return / std_return) * (252 ** 0.5) if std_return > 0 else 0
            else:
                sharpe_ratio = 0
            
            # Maximum drawdown
            cumulative = []
            running_total = 0
            for t in trades:
                running_total += t["profit"]
                cumulative.append(running_total)
            
            max_drawdown = 0
            peak = cumulative[0] if cumulative else 0
            for value in cumulative:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
            
            return {
                "total_profit": round(total_profit, 2),
                "total_trades": len(trades),
                "win_rate": round(win_rate, 1),
                "avg_win": round(avg_win, 2),
                "avg_loss": round(avg_loss, 2),
                "best_day": (best_day[0].strftime("%Y-%m-%d"), round(best_day[1], 2)),
                "worst_day": (worst_day[0].strftime("%Y-%m-%d"), round(worst_day[1], 2)),
                "daily": {day.strftime("%Y-%m-%d"): round(data["profit"], 2) for day, data in daily.items()},
                "daily_trades": {day.strftime("%Y-%m-%d"): data["trades"] for day, data in daily.items()},
                "profit_factor": round(profit_factor, 2),
                "max_drawdown": round(max_drawdown * 100, 2),  # As percentage
                "sharpe_ratio": round(sharpe_ratio, 2),
                "total_wins": len(wins),
                "total_losses": len(losses)
            }
            
        except Exception as e:
            print(f"❌ Error generating report: {e}")
            return None

# Initialize analytics engine
analytics = AnalyticsEngine()

@app.route("/")
def dashboard():
    """🖥️ Main dashboard page"""
    return render_template("dashboard.html")

@app.route("/api/analytics")
def get_analytics():
    """🔧 API endpoint for analytics data"""
    try:
        trades = analytics.get_last_6_days_trades()
        summary = analytics.generate_6day_report(trades)
        
        if summary:
            return jsonify({
                "success": True,
                "data": summary,
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
        else:
            return jsonify({
                "success": False,
                "error": "Failed to generate analytics"
            })
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

@app.route("/api/trades")
def get_trades():
    """API endpoint for raw trade data"""
    try:
        trades = analytics.get_last_6_days_trades()
        
        # Format trades for display
        formatted_trades = []
        for trade in trades:
            formatted_trades.append({
                "symbol": trade["symbol"],
                "profit": round(trade["profit"], 2),
                "volume": trade["volume"],
                "time": trade["time"].strftime("%Y-%m-%d %H:%M:%S"),
                "price": trade["price"]
            })
        
        return jsonify({
            "success": True,
            "data": formatted_trades,
            "count": len(formatted_trades)
        })
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

if __name__ == "__main__":
    print("🚀 Starting LEVEL 9 Analytics Dashboard...")
    print("📊 Open http://localhost:5000 in your browser")
    
    app.run(debug=True, host="0.0.0.0", port=5000)
