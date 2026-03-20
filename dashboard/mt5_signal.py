"""
MT5 Integrated Trading Signal Dashboard
Uses real market data from MetaTrader 5
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from technical_analysis import TechnicalAnalysis
from brokers.mt5_connector import MT5Connector
from risk_management import RiskManager

# Configure page
st.set_page_config(
    page_title="BrayoForexBot - MT5 Trading Signals",
    layout="wide"
)

st.title("🎯 BrayoForexBot - Live Trading Signals")

# Initialize session state
if 'mt5_connected' not in st.session_state:
    st.session_state.mt5_connected = False
if 'mt5_connector' not in st.session_state:
    st.session_state.mt5_connector = None

# MT5 Connection Section
st.sidebar.markdown("### 🏦 MT5 Connection")
mt5_login = st.sidebar.text_input("MT5 Login", type="password")
mt5_password = st.sidebar.text_input("MT5 Password", type="password")
mt5_server = st.sidebar.text_input("MT5 Server", value="MetaQuotes-Demo")

# Connect to MT5
if st.sidebar.button("🔗 Connect to MT5"):
    try:
        with st.spinner("Connecting to MT5..."):
            connector = MT5Connector()
            
            if connector.initialize(
                login=int(mt5_login) if mt5_login else None,
                password=mt5_password,
                server=mt5_server
            ):
                st.session_state.mt5_connected = True
                st.session_state.mt5_connector = connector
                st.sidebar.success("Connected to MT5!")
                st.rerun()
            else:
                st.sidebar.error("Failed to connect to MT5")
                
    except Exception as e:
        st.sidebar.error(f"Connection error: {e}")

# Show connection status
if st.session_state.mt5_connected:
    st.sidebar.success("MT5 Connected")
else:
    st.sidebar.info("Not connected to MT5")

# Main Signal Generation
if st.session_state.mt5_connected and st.session_state.mt5_connector:
    st.markdown("### 🎯 Live Trading Signal")
    
    # Get real market data
    try:
        with st.spinner("Fetching market data..."):
            # First, fetch historical data
            try:
                from datetime import datetime, timedelta
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                
                historical_data = st.session_state.mt5_connector.get_historical_data(
                    symbol="EURUSD",
                    timeframe="H1",
                    start_date=start_date,
                    end_date=end_date
                )
            except Exception as e:
                st.error(f"Error getting historical data: {e}")
                historical_data = None
            
            # Get current price from historical data (last close price)
            if historical_data is not None and len(historical_data) > 0:
                current_price = historical_data['close'].iloc[-1]
                st.success(f"Using live price from MT5: {current_price:.5f} (from {len(historical_data)} data points)")
            else:
                st.error("No data from MT5. Please ensure MT5 is running and connected.")
                current_price = None
            
            if historical_data is not None and len(historical_data) > 0:
                # Calculate indicators
                ta = TechnicalAnalysis()
                rsi = ta.calculate_rsi(historical_data['close'], period=14)
                sma_fast, sma_slow = ta.calculate_moving_averages(historical_data['close'])
                
                latest_rsi = rsi.iloc[-1]
                latest_sma = sma_fast.iloc[-1]
                latest_ema = sma_slow.iloc[-1]
                
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
                    stop_loss_price = current_price - (stop_loss_pips * 0.0001)
                    take_profit_price = current_price + (stop_loss_pips * 0.00015)
                else:
                    stop_loss_price = current_price + (stop_loss_pips * 0.0001)
                    take_profit_price = current_price - (stop_loss_pips * 0.00015)
                
                # Calculate position size
                risk_manager = RiskManager(account_balance=10000)
                position_size = risk_manager.calculate_position_size(
                    "EURUSD", current_price, stop_loss_price, decision
                )
                
                # Display signal
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown(f"### {signal_color} {decision}")
                    st.markdown(f"**Confidence**: {confidence:.0f}%")
                    st.markdown(f"**Entry Price**: {current_price:.5f}")
                    st.markdown(f"**Stop Loss**: {stop_loss_price:.5f}")
                    st.markdown(f"**Take Profit**: {take_profit_price:.5f}")
                    
                with col2:
                    if decision != "WAIT":
                        st.markdown("**Position Size**")
                        st.metric("Lots", f"{position_size:.2f}")
                        st.markdown("**Risk Amount**")
                        st.metric("Risk", f"${10000 * 0.02:.2f}")
                
                # Show reasons
                st.markdown("**Signal Reasons:**")
                if reasons:
                    for reason in reasons:
                        st.markdown(f"• {reason}")
                else:
                    st.markdown("• Neutral conditions")
                
                # Technical indicators
                st.markdown("**Technical Indicators:**")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("RSI(14)", f"{latest_rsi:.1f}")
                
                with col2:
                    st.metric("SMA(20)", f"{latest_sma:.5f}")
                
                with col3:
                    st.metric("EMA(20)", f"{latest_ema:.5f}")
                
                # Market info
                st.markdown("---")
                st.markdown("### 📊 Market Information")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Current Price", f"{current_price:.5f}")
                    st.metric("Data Points", f"{len(historical_data)}")
                
                with col2:
                    st.metric("Timeframe", "H1 (1 Hour)")
                    st.metric("Signal", decision)
                
            else:
                st.error("❌ Failed to fetch historical data")
                
    except Exception as e:
        st.error(f"❌ Error generating signal: {e}")
        
else:
    st.info("🔗 Please connect to MT5 to see live trading signals")
    
    # Instructions
    st.markdown("---")
    st.markdown("### 📋 How to Use:")
    st.markdown("1. Enter your MT5 credentials in the sidebar")
    st.markdown("2. Click 'Connect to MT5'")
    st.markdown("3. Wait for connection confirmation")
    st.markdown("4. View live trading signals with real market data")
    
    st.markdown("### 🎯 Features:")
    st.markdown("• **Real Market Data** - Live prices from MT5")
    st.markdown("• **Technical Indicators** - RSI, SMA, EMA calculations")
    st.markdown("• **Live Signals** - BUY/SELL/WAIT decisions")
    st.markdown("• **Risk Management** - Position sizing, SL/TP")
    st.markdown("• **Professional Interface** - Real-time updates")
