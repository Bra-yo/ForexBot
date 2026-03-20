"""
Test signal display in Streamlit
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

# Configure page
st.set_page_config(
    page_title="Signal Test",
    layout="wide"
)

st.title("🎯 Trading Signal Test")

# Generate signal
if st.button("Generate Signal"):
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
        st.markdown("### 🎯 Trading Signal Generated!")
        
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
            
    except Exception as e:
        st.error(f"Error generating signal: {e}")
        import traceback
        st.code(traceback.format_exc())

else:
    st.info("Click 'Generate Signal' to test trading signal generation")
