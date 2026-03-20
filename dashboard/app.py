"""
BrayoForexBot Dashboard - Professional Trading Interface
Real-time monitoring and control of AI-powered trading system
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import time
import threading
from datetime import datetime, timedelta
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import trading components
from ai.ai_trading_engine import AITradingEngine
from risk_management import RiskManager
from notifications import NotificationManager
from brokers.mt5_connector import MT5Connector

# Configure page
st.set_page_config(
    page_title="BrayoForexBot Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
    border-radius: 10px;
    color: white;
    margin: 10px 0;
}
.status-online {
    color: #00ff00;
    font-weight: bold;
}
.status-offline {
    color: #ff0000;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

class TradingDashboard:
    """Professional trading dashboard interface"""
    
    def __init__(self):
        self.trading_engine = None
        self.is_running = False
        self.last_update = None
        self.data_cache = {}
        
    def initialize_session_state(self):
        """Initialize Streamlit session state"""
        if 'trading_engine' not in st.session_state:
            st.session_state.trading_engine = None
        if 'is_running' not in st.session_state:
            st.session_state.is_running = False
        if 'selected_symbols' not in st.session_state:
            st.session_state.selected_symbols = ['EURUSD', 'GBPUSD']
        if 'ai_enabled' not in st.session_state:
            st.session_state.ai_enabled = True
        if 'risk_enabled' not in st.session_state:
            st.session_state.risk_enabled = True
    
    def run_dashboard(self):
        """Main dashboard application"""
        self.initialize_session_state()
        
        # Header
        st.title("🤖 BrayoForexBot Dashboard")
        st.markdown("---")
        
        # Sidebar controls
        self.render_sidebar()
        
        # Main content
        if st.session_state.trading_engine:
            self.render_main_dashboard()
        else:
            self.render_setup_page()
    
    def render_sidebar(self):
        """Render sidebar controls"""
        with st.sidebar:
            st.header("🎛️ Control Panel")
            
            # Connection Status
            self.render_connection_status()
            
            # Trading Controls
            st.header("🚀 Trading Controls")
            
            if st.session_state.trading_engine:
                # Start/Stop Trading
                if st.button("▶️ Start Trading", type="primary" if not st.session_state.is_running else "secondary"):
                    self.start_trading()
                
                if st.button("⏹️ Stop Trading", type="primary" if st.session_state.is_running else "secondary"):
                    self.stop_trading()
                
                # Symbol Selection
                st.header("📊 Symbol Selection")
                available_symbols = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'NZDUSD']
                selected = st.multiselect(
                    "Select Symbols",
                    available_symbols,
                    default=st.session_state.selected_symbols
                )
                st.session_state.selected_symbols = selected
                
                # AI Settings
                st.header("🧠 AI Settings")
                st.session_state.ai_enabled = st.checkbox("Enable AI Trading", value=st.session_state.ai_enabled)
                
                if st.session_state.ai_enabled:
                    confidence_threshold = st.slider(
                        "AI Confidence Threshold",
                        min_value=0.5,
                        max_value=0.9,
                        value=0.65,
                        step=0.05
                    )
                    
                    ensemble_weight = st.slider(
                        "AI vs Traditional Weight",
                        min_value=0.0,
                        max_value=1.0,
                        value=0.7,
                        step=0.1
                    )
                    
                    if st.session_state.trading_engine:
                        st.session_state.trading_engine.update_ai_settings(
                            confidence_threshold=confidence_threshold,
                            ensemble_weight=ensemble_weight
                        )
                
                # Risk Management
                st.header("🛡️ Risk Management")
                st.session_state.risk_enabled = st.checkbox("Enable Risk Management", value=st.session_state.risk_enabled)
                
                if st.session_state.risk_enabled:
                    max_risk = st.slider("Max Risk per Trade (%)", 1, 5, 2)
                    max_positions = st.slider("Max Open Positions", 1, 10, 5)
            
            else:
                # Setup controls
                st.header("🔧 Setup")
                
                mt5_login = st.text_input("MT5 Login (optional)")
                mt5_password = st.text_input("MT5 Password (optional)", type="password")
                mt5_server = st.text_input("MT5 Server (optional)")
                
                if st.button("🚀 Initialize Trading Engine", type="primary"):
                    self.initialize_trading_engine(mt5_login, mt5_password, mt5_server)
    
    def render_connection_status(self):
        """Render connection status"""
        st.header("📡 Connection Status")
        
        if st.session_state.trading_engine:
            if st.session_state.trading_engine.mt5_connector.connected:
                st.markdown('<span class="status-online">● MT5 Connected</span>', unsafe_allow_html=True)
                
                # Account info
                account_info = st.session_state.trading_engine.mt5_connector.get_account_info()
                if 'error' not in account_info:
                    st.write(f"Balance: ${account_info['balance']:.2f}")
                    st.write(f"Equity: ${account_info['equity']:.2f}")
            else:
                st.markdown('<span class="status-offline">● MT5 Disconnected</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="status-offline">● Not Initialized</span>', unsafe_allow_html=True)
    
    def render_main_dashboard(self):
        """Render main dashboard content"""
        # Status bar
        self.render_status_bar()
        
        # Metrics Row
        self.render_metrics_row()
        
        # Charts Row
        self.render_charts_row()
        
        # Positions and Activity
        self.render_positions_activity()
        
        # AI Performance
        if st.session_state.ai_enabled:
            self.render_ai_performance()
    
    def render_status_bar(self):
        """Render status bar"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            status = "🟢 RUNNING" if st.session_state.is_running else "🔴 STOPPED"
            st.metric("Trading Status", status)
        
        with col2:
            if self.last_update:
                time_ago = (datetime.now() - self.last_update).seconds
                st.metric("Last Update", f"{time_ago}s ago")
            else:
                st.metric("Last Update", "Never")
        
        with col3:
            if st.session_state.trading_engine:
                try:
                    positions = st.session_state.trading_engine.get_position_summary()
                    st.metric("Open Positions", positions.get('total_positions', 0))
                except Exception as e:
                    st.metric("Open Positions", "Error")
                    st.error(f"Positions error: {e}")
        
        with col4:
            if st.session_state.ai_enabled and st.session_state.trading_engine:
                try:
                    ai_perf = st.session_state.trading_engine.get_ai_performance_report()
                    ai_predictions = ai_perf.get('ai_performance', {}).get('ai_predictions', 0)
                    st.metric("AI Decisions", ai_predictions)
                except Exception as e:
                    st.metric("AI Decisions", "Error")
                    st.error(f"AI performance error: {e}")
    
    def render_metrics_row(self):
        """Render key metrics"""
        if not st.session_state.trading_engine:
            return
        
        # Get account summary
        try:
            summary = st.session_state.trading_engine.get_mt5_account_summary()
        except AttributeError:
            # Fallback to regular trading statistics
            summary = st.session_state.trading_engine.get_trading_statistics()
        
        if 'error' not in summary:
            try:
                col1, col2, col3, col4 = st.columns(4)
                
                # Handle different summary structures
                if 'account' in summary:
                    # MT5 summary structure
                    with col1:
                        balance = summary.get('account', {}).get('balance', 0)
                        profit = summary.get('account', {}).get('profit', 0)
                        st.metric(
                            "Account Balance",
                            f"${balance:.2f}",
                            delta=f"${profit:.2f}"
                        )
                    
                    with col2:
                        equity = summary.get('account', {}).get('equity', 0)
                        unrealized_pnl = summary.get('positions', {}).get('unrealized_pnl', 0)
                        st.metric(
                            "Equity",
                            f"${equity:.2f}",
                            delta=f"${unrealized_pnl:.2f}"
                        )
                    
                    with col3:
                        margin_free = summary.get('account', {}).get('margin_free', 0)
                        margin_level = summary.get('account', {}).get('margin_level', 0)
                        st.metric(
                            "Free Margin",
                            f"${margin_free:.2f}",
                            delta=f"{margin_level:.1f}%"
                        )
                    
                    with col4:
                        orders_executed = summary.get('execution_stats', {}).get('orders_executed', 0)
                        orders_placed = summary.get('execution_stats', {}).get('orders_placed', 1)
                        win_rate = (orders_executed / orders_placed * 100) if orders_placed > 0 else 0
                        
                        st.metric(
                            "Win Rate",
                            f"{win_rate:.1f}%",
                            delta=f"{orders_executed} trades"
                        )
                else:
                    # Regular trading statistics structure
                    with col1:
                        total_pnl = summary.get('total_pnl', 0)
                        st.metric(
                            "Total P&L",
                            f"${total_pnl:.2f}",
                            delta=f"${total_pnl:.2f}"
                        )
                    
                    with col2:
                        total_trades = summary.get('total_trades', 0)
                        st.metric(
                            "Total Trades",
                            f"{total_trades}",
                            delta="Completed"
                        )
                    
                    with col3:
                        win_rate = summary.get('win_rate', 0)
                        st.metric(
                            "Win Rate",
                            f"{win_rate:.1f}%",
                            delta="Performance"
                        )
                    
                    with col4:
                        profit_factor = summary.get('profit_factor', 0)
                        st.metric(
                            "Profit Factor",
                            f"{profit_factor:.2f}",
                            delta="Ratio"
                        )
                        
            except Exception as e:
                st.error(f"Error rendering metrics: {e}")
        else:
            st.error(f"Account summary error: {summary['error']}")
    
    def render_charts_row(self):
        """Render trading charts"""
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Price Chart")
            self.render_price_chart()
        
        with col2:
            st.subheader("💹 Equity Curve")
            self.render_equity_chart()
    
    def render_price_chart(self):
        """Render price chart with indicators"""
        try:
            if not st.session_state.trading_engine or not st.session_state.selected_symbols:
                st.info("Select symbols to view charts")
                return
            
            symbol = st.session_state.selected_symbols[0]
            
            # Get historical data
            data = st.session_state.trading_engine.mt5_data_reader.get_latest_data(symbol, 'H1', bars=100)
            
            if data.empty:
                st.warning(f"No data available for {symbol}")
                return
            
            # Create candlestick chart
            fig = go.Figure()
            
            fig.add_trace(go.Candlestick(
                x=data.index,
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                name=symbol
            ))
            
            # Add moving averages
            if len(data) >= 20:
                ma20 = data['close'].rolling(20).mean()
                ma50 = data['close'].rolling(50).mean()
                
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=ma20,
                    mode='lines',
                    name='MA20',
                    line=dict(color='orange', width=1)
                ))
                
                fig.add_trace(go.Scatter(
                    x=data.index,
                    y=ma50,
                    mode='lines',
                    name='MA50',
                    line=dict(color='blue', width=1)
                ))
            
            fig.update_layout(
                title=f"{symbol} - 1 Hour",
                xaxis_title="Time",
                yaxis_title="Price",
                height=400,
                showlegend=True
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering price chart: {e}")
    
    def render_equity_chart(self):
        """Render equity curve"""
        try:
            if not st.session_state.trading_engine:
                return
            
            # Get trading history
            history = st.session_state.trading_engine.trading_history
            
            if not history:
                st.info("No trading history available")
                return
            
            # Create equity curve
            equity_data = []
            running_equity = 10000  # Starting balance
            
            for trade in history:
                if trade['type'] == 'CLOSE':
                    running_equity += trade['position'].get('realized_pnl', 0)
                    equity_data.append({
                        'timestamp': trade['timestamp'],
                        'equity': running_equity
                    })
            
            if not equity_data:
                st.info("No completed trades yet")
                return
            
            df_equity = pd.DataFrame(equity_data)
            
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=df_equity['timestamp'],
                y=df_equity['equity'],
                mode='lines',
                name='Equity',
                line=dict(color='green', width=2)
            ))
            
            fig.update_layout(
                title="Equity Curve",
                xaxis_title="Time",
                yaxis_title="Equity ($)",
                height=400
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering equity chart: {e}")
    
    def render_positions_activity(self):
        """Render positions and recent activity"""
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📋 Open Positions")
            self.render_open_positions()
        
        with col2:
            st.subheader("📜 Recent Activity")
            self.render_recent_activity()
    
    def render_open_positions(self):
        """Render open positions table"""
        try:
            if not st.session_state.trading_engine:
                return
            
            positions = st.session_state.trading_engine.mt5_order_executor.get_open_positions()
            
            if not positions:
                st.info("No open positions")
                return
            
            # Create DataFrame
            pos_data = []
            for pos in positions:
                pos_data.append({
                    'Symbol': pos['symbol'],
                    'Type': 'BUY' if pos['type'] == 0 else 'SELL',
                    'Size': pos['volume'],
                    'Entry': pos['price_open'],
                    'Current': pos['price_current'],
                    'P&L': f"${pos['profit']:.2f}",
                    'SL': pos['sl'],
                    'TP': pos['tp']
                })
            
            df_positions = pd.DataFrame(pos_data)
            
            # Color code P&L
            def color_pnl(val):
                color = 'green' if val.startswith('$') and '+' in val else 'red'
                return f'color: {color}'
            
            styled_df = df_positions.style.applymap(color_pnl, subset=['P&L'])
            
            st.dataframe(styled_df, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering positions: {e}")
    
    def render_recent_activity(self):
        """Render recent trading activity"""
        try:
            if not st.session_state.trading_engine:
                return
            
            history = st.session_state.trading_engine.trading_history
            
            if not history:
                st.info("No trading activity")
                return
            
            # Get recent trades
            recent_trades = history[-10:]  # Last 10 trades
            
            activity_data = []
            for trade in reversed(recent_trades):
                position = trade['position']
                activity_data.append({
                    'Time': trade['timestamp'].strftime('%H:%M:%S'),
                    'Action': trade['type'],
                    'Symbol': position['symbol'],
                    'Type': position.get('action', ''),
                    'Size': position.get('position_size', 0),
                    'Price': position.get('entry_price', 0),
                    'P&L': f"${position.get('realized_pnl', 0):.2f}"
                })
            
            df_activity = pd.DataFrame(activity_data)
            st.dataframe(df_activity, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering activity: {e}")
    
    def render_ai_performance(self):
        """Render AI performance metrics"""
        st.subheader("🧠 AI Performance")
        
        if not st.session_state.trading_engine:
            return
        
        try:
            ai_perf = st.session_state.trading_engine.get_ai_performance_report()
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "AI Predictions",
                    ai_perf['ai_performance']['ai_predictions']
                )
                
                if ai_perf['ai_performance']['ai_predictions'] > 0:
                    accuracy = ai_perf['ai_performance']['ai_accuracy']
                    st.metric("AI Accuracy", f"{accuracy:.1%}")
            
            with col2:
                st.metric(
                    "AI-Only Decisions",
                    ai_perf['ai_performance']['ai_only_decisions']
                )
                
                st.metric(
                    "Hybrid Decisions",
                    ai_perf['ai_performance']['hybrid_decisions']
                )
            
            with col3:
                st.metric(
                    "Loaded Models",
                    len(ai_perf['loaded_models'])
                )
                
                st.metric(
                    "Confidence Threshold",
                    f"{ai_perf['confidence_threshold']:.1%}"
                )
            
            # Model performance chart
            if ai_perf['model_performance']:
                st.subheader("📊 Model Performance")
                
                model_names = list(ai_perf['model_performance'].keys())
                if model_names:
                    fig = go.Figure()
                    
                    fig.add_trace(go.Bar(
                        x=model_names,
                        y=[ai_perf['model_performance'][m] for m in model_names],
                        name='Model Performance'
                    ))
                    
                    fig.update_layout(
                        title="Model Performance Comparison",
                        xaxis_title="Models",
                        yaxis_title="Performance Score",
                        height=300
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
            
        except Exception as e:
            st.error(f"Error rendering AI performance: {e}")
    
    def render_setup_page(self):
        """Render setup page"""
        st.markdown("""
        # 🚀 Welcome to BrayoForexBot Dashboard
        
        ## 📋 Setup Instructions
        
        1. **Connect to MT5**: Enter your MT5 credentials in the sidebar
        2. **Initialize Engine**: Click "Initialize Trading Engine"
        3. **Configure Settings**: Select symbols and adjust AI/risk settings
        4. **Start Trading**: Click "Start Trading" to begin
        
        ## 🎯 Features
        
        - 🤖 **AI-Powered Trading**: Machine learning predictions
        - 📊 **Real-time Charts**: Live price and equity charts
        - 🛡️ **Risk Management**: Built-in risk controls
        - 📈 **Performance Tracking**: Detailed analytics
        - 📱 **Mobile Friendly**: Responsive design
        
        ## ⚠️ Important Notes
        
        - Start with a **demo account**
        - Monitor closely initially
        - Adjust risk settings as needed
        - Keep AI confidence thresholds reasonable
        """)
    
    def initialize_trading_engine(self, login, password, server):
        """Initialize trading engine"""
        try:
            with st.spinner("Initializing trading engine..."):
                # Create components
                risk_manager = RiskManager(account_balance=10000)
                notifications = NotificationManager()
                
                # Create AI trading engine
                trading_engine = AITradingEngine(
                    risk_manager=risk_manager,
                    mt5_login=int(login) if login else None,
                    mt5_password=password,
                    mt5_server=server
                )
                
                # Initialize MT5
                if not trading_engine.initialize_mt5():
                    st.error("Failed to connect to MT5. Please check your credentials.")
                    return
                
                # Initialize AI (if models available)
                model_paths = {
                    'xgboost': 'ai/models/xgboost_model.pkl',
                    'random_forest': 'ai/models/rf_model.pkl'
                }
                
                model_types = {
                    'xgboost': 'classification',
                    'random_forest': 'classification'
                }
                
                try:
                    trading_engine.initialize_ai_system(model_paths, model_types)
                    st.success("AI system initialized successfully!")
                except Exception as e:
                    st.warning(f"AI system not available: {e}")
                
                # Store in session state
                st.session_state.trading_engine = trading_engine
                
                st.success("Trading engine initialized successfully!")
                
        except Exception as e:
            st.error(f"Error initializing trading engine: {e}")
    
    def start_trading(self):
        """Start trading"""
        try:
            if not st.session_state.trading_engine:
                st.error("Trading engine not initialized")
                return
            
            if not st.session_state.selected_symbols:
                st.error("Please select at least one symbol")
                return
            
            with st.spinner("Starting trading..."):
                # Start AI trading
                success = st.session_state.trading_engine.start_ai_trading(
                    st.session_state.selected_symbols
                )
                
                if success:
                    st.session_state.is_running = True
                    st.success("Trading started successfully!")
                    st.rerun()
                else:
                    st.error("Failed to start trading - Check MT5 connection and AI settings")
                    
        except Exception as e:
            st.error(f"Error starting trading: {e}")
    
    def stop_trading(self):
        """Stop trading"""
        try:
            if st.session_state.trading_engine:
                success = st.session_state.trading_engine.stop_real_time_trading()
                
                if success:
                    st.session_state.is_running = False
                    st.success("Trading stopped!")
                    st.rerun()
                else:
                    st.warning("Trading stop requested - check MT5 connection")
            else:
                st.warning("No trading engine to stop")
            
        except Exception as e:
            st.error(f"Error stopping trading: {e}")

# Main application
def main():
    """Main dashboard application"""
    dashboard = TradingDashboard()
    dashboard.run_dashboard()

if __name__ == "__main__":
    main()
