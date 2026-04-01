"""
🌐 BrayoForexBot - Dashboard UI (Read-Only)
Displays trading engine data, doesn't control trading logic
"""
import streamlit as st
import json
import time
from datetime import datetime, timedelta
import sys
from pathlib import Path
import MetaTrader5 as mt5
import pandas as pd

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Configure page
st.set_page_config(
    page_title="BrayoForexBot - Trading Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============ ANALYTICS FUNCTIONS ============
def get_last_6_days_trades():
    """Get last 6 days of trade data from MT5"""
    try:
        if not mt5.initialize():
            return None
        
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
        st.error(f"Error fetching trades: {e}")
        return []

def generate_analytics_report(trades):
    """Generate analytics report from trade data"""
    if not trades:
        return {
            "total_profit": 0,
            "total_trades": 0,
            "win_rate": 0,
            "avg_win": 0,
            "avg_loss": 0,
            "best_day": ("No trades", 0),
            "worst_day": ("No trades", 0),
            "daily": {},
            "profit_factor": 0
        }
    
    try:
        # Basic calculations
        total_profit = sum(t["profit"] for t in trades)
        wins = [t for t in trades if t["profit"] > 0]
        losses = [t for t in trades if t["profit"] <= 0]
        
        win_rate = (len(wins) / len(trades)) * 100 if trades else 0
        
        avg_win = sum(t["profit"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t["profit"] for t in losses) / len(losses) if losses else 0
        
        # Daily grouping
        daily = {}
        for t in trades:
            day = t["time"].date()
            daily.setdefault(day, {"profit": 0, "trades": 0})
            daily[day]["profit"] += t["profit"]
            daily[day]["trades"] += 1
        
        # Best and worst days
        daily_profits = {day: data["profit"] for day, data in daily.items()}
        best_day = max(daily_profits.items(), key=lambda x: x[1]) if daily_profits else ("No trades", 0)
        worst_day = min(daily_profits.items(), key=lambda x: x[1]) if daily_profits else ("No trades", 0)
        
        # Profit factor
        total_wins = sum(t["profit"] for t in wins)
        total_losses = abs(sum(t["profit"] for t in losses)) if losses else 1
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
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
            "total_wins": len(wins),
            "total_losses": len(losses)
        }
        
    except Exception as e:
        st.error(f"Error generating report: {e}")
        return None

def render_analytics_page():
    """Render the analytics page"""
    st.markdown("## 📊 6-Day Performance Analytics")
    
    # Get trades and generate report
    with st.spinner("Loading analytics data..."):
        trades = get_last_6_days_trades()
        report = generate_analytics_report(trades)
    
    if not report:
        st.error("Unable to generate analytics report")
        return
    
    # Main metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        profit_color = "normal" if report["total_profit"] >= 0 else "inverse"
        st.metric("💰 Total P&L", f"${report['total_profit']}", delta_color=profit_color)
    
    with col2:
        st.metric("📈 Total Trades", report["total_trades"])
    
    with col3:
        st.metric("🎯 Win Rate", f"{report['win_rate']}%")
    
    with col4:
        st.metric("📊 Profit Factor", report["profit_factor"])
    
    # Additional metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("🏆 Avg Win", f"${report['avg_win']}")
    
    with col2:
        st.metric("💀 Avg Loss", f"${report['avg_loss']}")
    
    with col3:
        st.metric("🔥 Total Wins", report["total_wins"])
    
    with col4:
        st.metric("❌ Total Losses", report["total_losses"])
    
    # Best/Worst days
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏆 Best Day")
        st.markdown(f"**{report['best_day'][0]}**: ${report['best_day'][1]:.2f}")
    
    with col2:
        st.markdown("### 💀 Worst Day")
        st.markdown(f"**{report['worst_day'][0]}**: ${report['worst_day'][1]:.2f}")
    
    # Charts
    if report["daily"]:
        st.markdown("### 📈 Daily Performance")
        
        # Prepare data for charts
        dates = list(report["daily"].keys())
        profits = list(report["daily"].values())
        trade_counts = list(report["daily_trades"].values())
        
        # Daily profit chart
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Daily Profit/Loss")
            profit_df = pd.DataFrame({
                'Date': dates,
                'Profit': profits
            })
            st.bar_chart(profit_df.set_index('Date'))
        
        with col2:
            st.markdown("#### Daily Trade Count")
            trades_df = pd.DataFrame({
                'Date': dates,
                'Trades': trade_counts
            })
            st.bar_chart(trades_df.set_index('Date'))
    
    # Recent trades table
    if trades:
        st.markdown("### 📋 Recent Trades")
        
        # Convert trades to DataFrame
        trades_df = pd.DataFrame(trades[-10:])  # Show last 10 trades
        trades_df['Time'] = trades_df['time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        trades_df['Profit'] = trades_df['profit'].round(2)
        
        # Format for display
        display_df = trades_df[['Time', 'Symbol', 'Volume', 'Price', 'Profit']].copy()
        display_df.columns = ['Time', 'Symbol', 'Volume', 'Price', 'Profit']
        
        # Color code profits
        def color_profit(val):
            color = 'green' if val > 0 else 'red' if val < 0 else 'black'
            return f'color: {color}'
        
        styled_df = display_df.style.applymap(color_profit, subset=['Profit'])
        st.dataframe(styled_df, use_container_width=True)

# ============ SHARED STATE READER ============
def read_trading_state():
    """Read shared state from trading engine"""
    try:
        with open("trading_state.json", "r") as f:
            return json.load(f)
    except:
        return {
            'timestamp': datetime.now().isoformat(),
            'market_open': False,
            'mt5_connected': False,
            'active_trades': [],
            'daily_loss': 0.0,
            'signals': {},
            'account_info': {}
        }

def is_engine_running():
    """Check if trading engine process is running"""
    try:
        state = read_trading_state()
        timestamp = datetime.fromisoformat(state['timestamp'])
        # If last update was within 5 seconds, engine is running (1-second loop with buffer)
        return (datetime.now() - timestamp).seconds < 5
    except:
        return False

# ============ UI COMPONENTS ============
def render_header():
    """Render dashboard header"""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.title("🤖 BrayoForexBot Dashboard")
        st.caption("Professional Trading System - Read-Only Interface")
    
    with col2:
        engine_status = is_engine_running()
        status_color = "🟢" if engine_status else "🔴"
        st.metric("Engine Status", f"{status_color} {'Running' if engine_status else 'Stopped'}")
    
    with col3:
        state = read_trading_state()
        market_color = "🟢" if state['market_open'] else "🔴"
        st.metric("Market", f"{market_color} {'Open' if state['market_open'] else 'Closed'}")

def render_account_info():
    """Render account information"""
    state = read_trading_state()
    account_info = state.get('account_info', {})
    
    if account_info:
        st.subheader("🏦 Account Information")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Balance", f"${account_info.get('balance', 0):.2f}")
        
        with col2:
            st.metric("Equity", f"${account_info.get('equity', 0):.2f}")
        
        with col3:
            st.metric("Free Margin", f"${account_info.get('free_margin', 0):.2f}")
        
        with col4:
            profit = account_info.get('profit', 0)
            profit_color = "normal" if profit >= 0 else "inverse"
            st.metric("Profit", f"${profit:.2f}", delta_color=profit_color)

def render_active_trades():
    """Render active trades"""
    state = read_trading_state()
    active_trades = state.get('active_trades', [])
    
    st.subheader("📊 Active Trades")
    
    if not active_trades:
        st.info("📋 No active trades")
        return
    
    for trade in active_trades:
        with st.expander(f"📈 Trade #{trade.get('ticket', 'N/A')} - {trade.get('type', 'Unknown')}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Symbol:** {trade.get('symbol', 'N/A')}")
                st.write(f"**Type:** {trade.get('type', 'N/A')}")
                st.write(f"**Volume:** {trade.get('volume', 0):.2f} lots")
                st.write(f"**Entry:** {trade.get('price', 0):.5f}")
            
            with col2:
                st.write(f"**SL:** {trade.get('sl', 0):.5f}")
                st.write(f"**TP:** {trade.get('tp', 0):.5f}")
                st.write(f"**Profit:** ${trade.get('profit', 0):.2f}")
                
                # Calculate pips
                if trade.get('type') == 'BUY':
                    pips = (trade.get('current_price', 0) - trade.get('price', 0)) / 0.00001
                else:
                    pips = (trade.get('price', 0) - trade.get('current_price', 0)) / 0.00001
                
                st.write(f"**Pips:** {pips:.1f}")

def render_signals():
    """Render trading signals"""
    state = read_trading_state()
    signals = state.get('signals', {})
    
    st.subheader("🎯 Trading Signals")
    
    if not signals:
        st.info("📋 No signals available")
        return
    
    # Signal display
    decision = signals.get('decision', 'HOLD')
    strength = signals.get('strength', 0)
    symbol = signals.get('symbol', 'N/A')
    timeframe = signals.get('timeframe', 'N/A')
    
    signal_emoji = {
        'BUY': '🟢', 'SELL': '🔴', 'HOLD': '🟡'
    }.get(decision, '⚪')
    
    st.markdown(f"### {signal_emoji} Signal: {decision}")
    st.caption(f"Strength: {strength}/10 | {symbol} | {timeframe}")
    
    # Technical indicators
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        rsi = signals.get('rsi', 0)
        rsi_status = "Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"
        st.metric("RSI(14)", f"{rsi:.1f}", rsi_status)
    
    with col2:
        st.metric("SMA(20)", f"{signals.get('sma', 0):.5f}")
    
    with col3:
        st.metric("EMA(20)", f"{signals.get('ema', 0):.5f}")
    
    with col4:
        ema = signals.get('ema', 0)
        sma = signals.get('sma', 0)
        trend = "Uptrend 📈" if ema > sma else "Downtrend 📉"
        st.metric("Trend", trend)
    
    # Signal reasons
    reasons = signals.get('reasons', [])
    if reasons:
        st.markdown("**📋 Signal Reasons:**")
        for reason in reasons:
            st.markdown(f"• {reason}")

def render_engine_controls():
    """Render engine control panel"""
    st.subheader("🎛️ Trading Engine Controls")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚀 Start Trading Engine", type="primary", use_container_width=True):
            st.info("📝 To start the trading engine, run: `python trading_engine.py` in a separate terminal")
            st.code("python trading_engine.py")
    
    with col2:
        if st.button("🛑 Stop Trading Engine", type="secondary", use_container_width=True):
            st.info("📝 To stop the trading engine, press CTRL+C in the engine terminal")
    
    st.markdown("---")
    st.info("💡 **Note:** The trading engine runs independently. This dashboard only displays data from the engine.")

def render_status_panel():
    """Render status information"""
    state = read_trading_state()
    
    st.subheader("📊 System Status")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Active Trades", len(state.get('active_trades', [])))
    
    with col2:
        st.metric("Daily Loss", f"${state.get('daily_loss', 0):.2f}")
    
    with col3:
        last_update = state.get('timestamp', '')
        if last_update:
            update_time = datetime.fromisoformat(last_update)
            st.metric("Last Update", update_time.strftime("%H:%M:%S"))
        else:
            st.metric("Last Update", "Never")
    
    with col4:
        engine_running = is_engine_running()
        st.metric("Engine", "🟢 Online" if engine_running else "🔴 Offline")

# ============ MAIN DASHBOARD ============
def main():
    """Main dashboard application"""
    # Page navigation in sidebar
    st.sidebar.markdown("## 🧭 Navigation")
    page = st.sidebar.selectbox("Choose Page:", ["🏠 Trading Dashboard", "📊 Analytics"])
    
    # Auto-refresh every 1 second (to keep up with 1-second engine)
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    # Check if it's time to refresh
    time_since_refresh = (datetime.now() - st.session_state.last_refresh).seconds
    if time_since_refresh >= 1:
        st.session_state.last_refresh = datetime.now()
        st.rerun()
    
    # Render selected page
    if page == "📊 Analytics":
        render_analytics_page()
    else:
        # Original dashboard
        render_header()
        
        # Status panel
        render_status_panel()
        
        # Account info
        render_account_info()
        
        # Active trades
        render_active_trades()
        
        # Signals
        render_signals()
        
        # Engine controls
        render_engine_controls()
        
        # Footer
        st.markdown("---")
        st.markdown("⚠️ **Important:** This dashboard is read-only. All trading logic runs in the independent trading engine.")
        st.markdown("🔄 **Auto-refresh:** Dashboard updates every 1 second for instant trade monitoring")

if __name__ == "__main__":
    main()
