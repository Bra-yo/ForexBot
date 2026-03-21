"""
🌐 BrayoForexBot - Dashboard UI (Read-Only)
Displays trading engine data, doesn't control trading logic
"""
import streamlit as st
import json
import time
from datetime import datetime
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

# Configure page
st.set_page_config(
    page_title="BrayoForexBot - Trading Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

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
    # Auto-refresh every 1 second (to keep up with 1-second engine)
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    
    # Check if it's time to refresh
    time_since_refresh = (datetime.now() - st.session_state.last_refresh).seconds
    if time_since_refresh >= 1:
        st.session_state.last_refresh = datetime.now()
        st.rerun()
    
    # Render dashboard components
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
