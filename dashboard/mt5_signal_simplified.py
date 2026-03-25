"""
MT5 Integrated Trading Signal Dashboard with Trading Chatbot
Uses real market data from MetaTrader 5 with enhanced security and AI assistant
"""

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import sys
from pathlib import Path
import random
import subprocess
import threading
import time
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from technical_analysis import TechnicalAnalysis
from brokers.mt5_connector import MT5Connector
from risk_management import RiskManager
from trade_manager import TradeManager
from trading_engine import pass_login_to_engine

# Configure page
st.set_page_config(
    page_title="BrayoForexBot - MT5 Trading Signals",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============ TRADING ENGINE MANAGEMENT ============
def start_trading_engine():
    """Start trading engine in background"""
    try:
        # Start trading engine in separate process
        engine_script = Path(__file__).parent / "trading_engine.py"
        subprocess.Popen([
            sys.executable, str(engine_script)
        ], creationflags=subprocess.CREATE_NEW_CONSOLE if sys.platform == "win32" else 0)
        print("🚀 Trading engine started in background")
        return True
    except Exception as e:
        print(f"❌ Failed to start trading engine: {e}")
        return False

# ============ LOGIN PAGE ============
def render_login_page():
    """Render full-screen login page"""
    # Create three columns to center login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-top: 50px;">
            <h1 style="font-size: 3em; margin-bottom: 10px;">🎯 BrayoForexBot</h1>
            <h2 style="color: var(--text-color, #666); margin-bottom: 40px;">Professional Trading Dashboard</h2>
        </div>
        """, unsafe_allow_html=True)
        
        # Login container
        st.markdown("""
        <div style="
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            max-width: 400px;
            margin: 0 auto;
        ">
            <h3 style="text-align: center; color: white; margin-bottom: 30px;">🔐 MT5 Login</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Login form
        with st.form("mt5_login_form"):
            mt5_login = st.text_input("📱 MT5 Login", placeholder="Enter your MT5 account number")
            mt5_password = st.text_input("🔑 MT5 Password", type="password", placeholder="Enter your MT5 password")
            mt5_server = st.text_input("🌐 MT5 Server", value="MetaQuotes-Demo", placeholder="e.g., MetaQuotes-Demo")
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                submit = st.form_submit_button(
                    "🔗 Connect to MT5",
                    use_container_width=True,
                    type="primary"
                )
            
            if submit:
                if not mt5_login or not mt5_password:
                    st.error("⚠️ Please enter both login and password")
                else:
                    with st.spinner("🔄 Connecting to MT5 and starting trading engine..."):
                        try:
                            # Start trading engine first
                            if not st.session_state.get('engine_started', False):
                                if start_trading_engine():
                                    st.session_state.engine_started = True
                                    time.sleep(2)  # Give engine time to start
                                else:
                                    st.error("❌ Failed to start trading engine")
                                    return
                            
                            # Connect dashboard to MT5
                            connector = MT5Connector()
                            
                            if connector.initialize(
                                login=int(mt5_login),
                                password=mt5_password,
                                server=mt5_server
                            ):
                                # Pass credentials to trading engine
                                if pass_login_to_engine(int(mt5_login), mt5_password, mt5_server):
                                    st.success("✅ Credentials passed to trading engine!")
                                else:
                                    st.warning("⚠️ Trading engine not ready, will retry...")
                                
                                st.session_state.mt5_connected = True
                                st.session_state.mt5_connector = connector
                                st.session_state.login_credentials = {
                                    'login': int(mt5_login),
                                    'password': mt5_password,
                                    'server': mt5_server
                                }
                                st.success("✅ Connected to MT5 successfully!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error("❌ Failed to connect to MT5. Please check your credentials and ensure MT5 is running.")
                        except Exception as e:
                            st.error(f"❌ Connection error: {str(e)}")
        
        # Security notice
        st.markdown("""
        <div style="
            background: var(--warning-background, #fff3cd);
            border: 1px solid var(--warning-border, #ffc107);
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
            max-width: 400px;
            margin-left: auto;
            margin-right: auto;
        ">
            <p style="margin: 0; color: var(--warning-color, #856404);">
                <strong>🔒 Security Notice:</strong><br>
                Your credentials are used only to connect to MT5 and are not stored. 
                This dashboard runs locally on your machine.
            </p>
        </div>
        """, unsafe_allow_html=True)

# ============ MARKET STATUS ============
def is_market_open():
    """Check if forex market is open"""
    now = datetime.now()
    weekday = now.weekday()  # 0=Monday, 6=Sunday
    hour = now.hour
    
    # Check if it's Saturday (all day)
    if weekday == 5:  # Saturday
        return False
    
    # Check if it's Sunday before 22:00 UTC
    if weekday == 6 and hour < 22:  # Sunday before 22:00 UTC
        return False
    
    # Forex market is open from Sunday 22:00 UTC to Friday 22:00 UTC
    return True

# ============ CHATBOT ============
def render_chatbot():
    """Render trading chatbot interface"""
    st.markdown("### 🤖 Trading Assistant")
    
    with st.expander("💬 Ask Trading Questions", expanded=False):
        user_input = st.text_input("Ask about trading, indicators, or strategies:")
        
        if st.button("Send") and user_input:
            # Generate response based on keywords
            response = generate_chatbot_response(user_input)
            st.write(f"🤖 **Assistant:** {response}")

def generate_chatbot_response(user_input):
    """Generate chatbot response based on keywords"""
    user_input_lower = user_input.lower()
    responses = []
    
    # RSI
    if 'rsi' in user_input_lower:
        responses.append("RSI (Relative Strength Index) measures momentum on a scale of 0-100. Below 30 indicates oversold (potential BUY), above 70 indicates overbought (potential SELL).")
    
    # MACD
    if 'macd' in user_input_lower:
        responses.append("MACD shows trend direction and momentum. When MACD crosses above signal line, it's a BUY signal. Below signal line is SELL signal.")
    
    # Moving averages
    if 'moving average' in user_input_lower or 'sma' in user_input_lower or 'ema' in user_input_lower:
        responses.append("Moving averages smooth price data. SMA gives equal weight to all periods. EMA gives more weight to recent periods. Golden cross (SMA crossing above EMA) is bullish signal.")
    
    # Bollinger Bands
    if 'bollinger' in user_input_lower:
        responses.append("Bollinger Bands show volatility and price levels. Price touching upper band suggests overbought (SELL). Touching lower band suggests oversold (BUY).")
    
    # Stop loss
    if 'stop loss' in user_input_lower or 'sl' in user_input_lower:
        responses.append("Stop loss limits risk by automatically closing trades at predetermined price levels. Typically set 1-2% below entry for BUY trades.")
    
    # Take profit
    if 'take profit' in user_input_lower or 'tp' in user_input_lower:
        responses.append("Take profit secures profits by automatically closing trades at predetermined price levels. Typically set 1.5-3% above entry for BUY trades.")
    
    # Risk management
    if 'risk' in user_input_lower:
        responses.append("Risk management is crucial. Never risk more than 1-2% per trade. Use proper position sizing based on account balance.")
    
    # Trend
    if 'trend' in user_input_lower:
        responses.append("Trend analysis helps identify market direction. Uptrend = higher highs and higher lows. Downtrend = lower highs and lower lows. Trade with the trend!")
    
    # Support/Resistance
    if 'support' in user_input_lower or 'resistance' in user_input_lower:
        responses.append("Support = price floor where buying pressure emerges. Resistance = price ceiling where selling pressure emerges. These are key entry/exit points!")
    
    # Timeframes
    if 'timeframe' in user_input_lower:
        responses.append("Higher timeframes (H4, D1) show major trends. Lower timeframes (M1, M5) show entry timing. Use multiple timeframes for confirmation!")
    
    # Volatility
    if 'volatility' in user_input_lower:
        responses.append("High volatility = larger price movements = larger potential profits BUT larger risks. Low volatility = smaller movements = tighter stops needed.")
    
    # Psychology
    if 'psychology' in user_input_lower:
        responses.append("Trading psychology: Control emotions, stick to your plan, accept losses as business costs. Don't revenge trade!")
    
    # Default response
    if not responses:
        responses.append("I can help with RSI, MACD, moving averages, Bollinger Bands, stop loss, take profit, risk management, trends, support/resistance, timeframes, volatility, and trading psychology. Ask me about any of these topics!")
    
    return "\n\n".join(responses)

# ============ SESSION STATE ============
def initialize_session_state():
    """Initialize Streamlit session state variables"""
    if 'mt5_connected' not in st.session_state:
        st.session_state.mt5_connected = False
    if 'mt5_connector' not in st.session_state:
        st.session_state.mt5_connector = None
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'show_chatbot' not in st.session_state:
        st.session_state.show_chatbot = False
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = True
    if 'engine_started' not in st.session_state:
        st.session_state.engine_started = False

# ============ DASHBOARD ============
def render_main_dashboard():
    """Render main dashboard with trading information"""
    # Read trading state from engine
    try:
        with open("trading_state.json", "r") as f:
            trading_state = json.load(f)
    except FileNotFoundError:
        trading_state = {
            'timestamp': datetime.now().isoformat(),
            'market_open': False,
            'mt5_connected': False,
            'active_trades': [],
            'daily_loss': 0.0,
            'signals': {},
            'account_info': {}
        }
    except:
        trading_state = {
            'timestamp': datetime.now().isoformat(),
            'market_open': False,
            'mt5_connected': False,
            'active_trades': [],
            'daily_loss': 0.0,
            'signals': {},
            'account_info': {}
        }
    
    # Market status
    market_open = is_market_open()
    
    st.markdown("### 🟢 Market Status")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Market", "🟢 Open" if market_open else "🔴 Closed")
    with col2:
        st.metric("MT5", "🟢 Connected" if trading_state.get('mt5_connected', False) else "🔴 Disconnected")
    with col3:
        st.metric("Active Trades", len(trading_state.get('active_trades', [])))
    with col4:
        daily_loss = trading_state.get('daily_loss', 0.0)
        loss_color = "🔴" if daily_loss < 0 else "🟢"
        st.metric("Daily P&L", f"{loss_color} ${abs(daily_loss):.2f}")
    
    # Account information
    account_info = trading_state.get('account_info', {})
    if account_info:
        st.markdown("### 🏦 Account Information")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Login", account_info.get('login', 'N/A'))
        with col2:
            st.metric("Balance", f"${account_info.get('balance', 0):.2f}")
        with col3:
            st.metric("Equity", f"${account_info.get('equity', 0):.2f}")
        with col4:
            st.metric("Free Margin", f"${account_info.get('free_margin', 0):.2f}")
    
    # Active trades
    active_trades = trading_state.get('active_trades', [])
    if active_trades:
        st.markdown("### 📊 Active Trades")
        
        for trade in active_trades:
            with st.expander(f"📈 Trade #{trade.get('ticket', 'N/A')} - {trade.get('symbol', 'N/A')}"):
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Type", trade.get('type', 'N/A'))
                with col2:
                    st.metric("Volume", trade.get('volume', 0))
                with col3:
                    st.metric("Entry", f"{trade.get('price_open', 0):.5f}")
                with col4:
                    profit = trade.get('profit', 0)
                    profit_color = "🟢" if profit >= 0 else "🔴"
                    st.metric("Profit", f"{profit_color} ${profit:.2f}")
    
    # Trading signals
    signals = trading_state.get('signals', {})
    if signals:
        st.markdown("### 🎯 Trading Signals")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            signal = signals.get('signal', 'HOLD')
            signal_color = "🟢" if signal == 'BUY' else "🔴" if signal == 'SELL' else "🟡"
            st.metric("Signal", f"{signal_color} {signal}")
        with col2:
            st.metric("Strength", f"{signals.get('strength', 0)}/10")
        with col3:
            st.metric("Symbol", signals.get('symbol', 'N/A'))
    
    # Last update time
    last_update = trading_state.get('timestamp', datetime.now().isoformat())
    st.caption(f"🕒 Last Update: {last_update}")
    
    # Chatbot section
    render_chatbot()
    
    # Auto-refresh
    if st.session_state.auto_refresh:
        time.sleep(1)  # 1-second refresh
        st.rerun()

# ============ MAIN APPLICATION ============
def main():
    """Main dashboard application"""
    initialize_session_state()
    
    if not st.session_state.mt5_connected:
        # Show login page
        render_login_page()
    else:
        # Show main dashboard with sidebar
        render_main_dashboard()

if __name__ == "__main__":
    main()
