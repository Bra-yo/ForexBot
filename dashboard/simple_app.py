"""
Simple Streamlit Dashboard for BrayoForexBot
Minimal version without AI dependencies for testing
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from technical_analysis import TechnicalAnalysis

# Configure page
st.set_page_config(
    page_title="BrayoForexBot Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 5px;
    }
    .status-online { background-color: #28a745; }
    .status-offline { background-color: #dc3545; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'trading_active' not in st.session_state:
    st.session_state.trading_active = False
if 'selected_symbol' not in st.session_state:
    st.session_state.selected_symbol = 'EURUSD'
if 'last_update' not in st.session_state:
    st.session_state.last_update = datetime.now()

# Sidebar
st.sidebar.title("🎛️ Trading Controls")

# Connection Status
st.sidebar.markdown("### 📡 Connection Status")
connection_status = st.sidebar.markdown('<span class="status-indicator status-offline"></span>MT5 Disconnected', unsafe_allow_html=True)

# Trading Controls
st.sidebar.markdown("### 🎯 Trading Controls")
col1, col2 = st.sidebar.columns(2)

with col1:
    if st.button("▶️ Start", type="primary"):
        st.session_state.trading_active = True
        st.success("Trading started!")

with col2:
    if st.button("⏹️ Stop", type="secondary"):
        st.session_state.trading_active = False
        st.warning("Trading stopped!")

# Symbol Selection
st.sidebar.markdown("### 📊 Symbol Selection")
symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD']
selected_symbol = st.sidebar.selectbox(
    "Select Symbol",
    symbols,
    index=symbols.index(st.session_state.selected_symbol)
)
st.session_state.selected_symbol = selected_symbol

# Risk Management
st.sidebar.markdown("### 🛡️ Risk Management")
risk_per_trade = st.sidebar.slider("Risk per Trade (%)", 0.1, 5.0, 2.0, 0.1)
max_positions = st.sidebar.slider("Max Open Positions", 1, 10, 3)

# Main Dashboard
st.title("📈 BrayoForexBot Dashboard")
st.markdown("---")

# Status Bar
col1, col2, col3, col4 = st.columns(4)

with col1:
    status_color = "🟢" if st.session_state.trading_active else "🔴"
    st.metric("Trading Status", f"{status_color} {'Active' if st.session_state.trading_active else 'Inactive'}")

with col2:
    st.metric("Last Update", st.session_state.last_update.strftime("%H:%M:%S"))

with col3:
    st.metric("Open Positions", "0")

with col4:
    st.metric("AI Decisions", "0")

# Current Signal Section
st.markdown("### 🎯 Current Trading Signal")

# Generate real trading signal
try:
    # Create sample market data
    dates = pd.date_range(start='2023-01-01', periods=100, freq='1h')
    np.random.seed(42)
    
    market_data = pd.DataFrame({
        'timestamp': dates,
        'open': 1.1000 + np.random.randn(100) * 0.001,
        'high': 1.1000 + np.random.randn(100) * 0.002,
        'low': 1.1000 + np.random.randn(100) * 0.002,
        'close': 1.1000 + np.random.randn(100) * 0.001,
        'volume': np.random.randint(1000, 10000, 100)
    })
    market_data.set_index('timestamp', inplace=True)
    
    # Calculate indicators
    ta = TechnicalAnalysis()
    rsi = ta.calculate_rsi(market_data['close'], period=14)
    sma_fast, sma_slow = ta.calculate_moving_averages(market_data['close'])
    
    latest_rsi = rsi.iloc[-1]
    latest_sma = sma_fast.iloc[-1]
    latest_ema = sma_slow.iloc[-1]
    latest_price = market_data['close'].iloc[-1]
    
    # Generate trading signal
    signal_strength = 0
    reasons = []
    
    if latest_rsi < 30:
        signal_strength += 2
        reasons.append(f"RSI oversold ({latest_rsi:.1f})")
    elif latest_rsi > 70:
        signal_strength -= 2
        reasons.append(f"RSI overbought ({latest_rsi:.1f})")
    
    if latest_ema > latest_sma:
        signal_strength += 1
        reasons.append("EMA above SMA (uptrend)")
    elif latest_ema < latest_sma:
        signal_strength -= 1
        reasons.append("EMA below SMA (downtrend)")
    
    # Final decision
    if signal_strength >= 2:
        decision = "BUY"
        confidence = min(90, 60 + signal_strength * 10)
        signal_color = "🟢"
    elif signal_strength <= -2:
        decision = "SELL"
        confidence = min(90, 60 + abs(signal_strength) * 10)
        signal_color = "🔴"
    else:
        decision = "WAIT"
        confidence = 50
        signal_color = "🟡"
    
    # Calculate SL/TP
    stop_loss_pips = 20
    if decision == "BUY":
        stop_loss_price = latest_price - (stop_loss_pips * 0.0001)
        take_profit_price = latest_price + (stop_loss_pips * 0.00015)
    else:
        stop_loss_price = latest_price + (stop_loss_pips * 0.0001)
        take_profit_price = latest_price - (stop_loss_pips * 0.00015)
    
    # Display signal
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown(f"### {signal_color} {decision}")
        st.markdown(f"**Confidence**: {confidence:.0f}%")
        st.markdown(f"**Entry Price**: {latest_price:.5f}")
        st.markdown(f"**Stop Loss**: {stop_loss_price:.5f}")
        st.markdown(f"**Take Profit**: {take_profit_price:.5f}")
        
    with col2:
        if decision != "WAIT":
            st.markdown("**Position Size**")
            st.metric("Lots", "0.10")
            st.markdown("**Risk Amount**")
            st.metric("Risk", "$200.00")
    
    # Show reasons
    if reasons:
        st.markdown("**Signal Reasons:**")
        for reason in reasons:
            st.markdown(f"• {reason}")
    else:
        st.markdown("**Signal Reasons:** Neutral conditions")
    
    # Technical indicators
    st.markdown("**Technical Indicators:**")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("RSI(14)", f"{latest_rsi:.1f}")
    
    with col2:
        st.metric("SMA(20)", f"{latest_sma:.5f}")
    
    with col3:
        st.metric("EMA(20)", f"{latest_ema:.5f}")
        
except Exception as e:
    st.error(f"Error generating signal: {e}")

st.markdown("---")
st.markdown("### 📊 Key Metrics")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Account Balance", "$10,000.00")

with col2:
    st.metric("Equity", "$10,000.00")

with col3:
    st.metric("Free Margin", "$10,000.00")

with col4:
    st.metric("Win Rate", "0.0%")

# Charts
st.markdown("### 📈 Charts")
col1, col2 = st.columns(2)

with col1:
    st.markdown("#### 💹 Price Chart")
    
    # Generate sample price data
    dates = pd.date_range(start=datetime.now() - timedelta(days=1), periods=100, freq='15min')
    np.random.seed(42)
    prices = 1.1000 + np.random.randn(100) * 0.001
    
    chart_data = pd.DataFrame({
        'time': dates,
        'price': prices
    })
    
    st.line_chart(chart_data.set_index('time'))

with col2:
    st.markdown("#### 📊 Equity Curve")
    
    # Generate sample equity data
    equity_data = pd.DataFrame({
        'time': dates,
        'equity': 10000 + np.random.randn(100) * 50
    })
    
    st.line_chart(equity_data.set_index('time'))

# Open Positions
st.markdown("### 💼 Open Positions")
positions_data = pd.DataFrame({
    'Symbol': [],
    'Type': [],
    'Volume': [],
    'Entry Price': [],
    'Current Price': [],
    'P&L': []
})

if positions_data.empty:
    st.info("No open positions")
else:
    st.dataframe(positions_data, use_container_width=True)

# Recent Activity
st.markdown("### 📋 Recent Activity")
activity_data = pd.DataFrame({
    'Time': [],
    'Symbol': [],
    'Action': [],
    'Price': [],
    'P&L': []
})

if activity_data.empty:
    st.info("No recent activity")
else:
    st.dataframe(activity_data, use_container_width=True)

# AI Performance (Placeholder)
st.markdown("### 🤖 AI Performance")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("AI Predictions", "0")

with col2:
    st.metric("AI Accuracy", "0.0%")

with col3:
    st.metric("Loaded Models", "0")

with col4:
    st.metric("Confidence", "0.0%")

# Auto-refresh
if st.session_state.trading_active:
    time.sleep(2)
    st.session_state.last_update = datetime.now()
    st.rerun()

# Footer
st.markdown("---")
st.markdown("🚀 BrayoForexBot - Professional AI Trading System")
st.markdown("⚠️ For demo purposes only. Use with demo account first.")
