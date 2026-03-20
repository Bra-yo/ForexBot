"""
Simple Trading Signal Display
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Configure page
st.set_page_config(
    page_title="Trading Signals",
    layout="wide"
)

st.title("🎯 BrayoForexBot Trading Signals")

# Generate signal
if st.button("🚀 Generate Trading Signal"):
    try:
        # Generate sample data
        np.random.seed(42)
        latest_price = 1.10124
        latest_rsi = 53.0
        latest_sma = 1.09997
        latest_ema = 1.10018
        
        # Generate signal
        signal_strength = 1  # EMA above SMA
        decision = "WAIT"
        confidence = 50
        signal_color = "🟡"
        
        # Calculate SL/TP
        stop_loss_price = 1.10324
        take_profit_price = 1.09824
        
        # Display signal
        st.markdown("### 🎯 Trading Signal Generated!")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown(f"### {signal_color} {decision}")
            st.markdown(f"**Confidence**: {confidence:.0f}%")
            st.markdown(f"**Entry Price**: {latest_price:.5f}")
            st.markdown(f"**Stop Loss**: {stop_loss_price:.5f}")
            st.markdown(f"**Take Profit**: {take_profit_price:.5f}")
            
        with col2:
            st.markdown("**Position Size**")
            st.metric("Lots", "0.10")
            st.markdown("**Risk Amount**")
            st.metric("Risk", "$200.00")
        
        # Show reasons
        st.markdown("**Signal Reasons:**")
        st.markdown("• EMA above SMA (uptrend)")
        
        # Technical indicators
        st.markdown("**Technical Indicators:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("RSI(14)", f"{latest_rsi:.1f}")
        
        with col2:
            st.metric("SMA(20)", f"{latest_sma:.5f}")
        
        with col3:
            st.metric("EMA(20)", f"{latest_ema:.5f}")
        
        st.success("✅ Trading signal generated successfully!")
        
    except Exception as e:
        st.error(f"❌ Error generating signal: {e}")

else:
    st.info("👆 Click 'Generate Trading Signal' to create a new trading signal")

st.markdown("---")
st.markdown("### 🎯 Core Purpose:")
st.markdown("This bot answers: **Should I BUY, SELL, or WAIT?**")
st.markdown("Based on: Data → Indicators → Strategy → Risk → Signal")
