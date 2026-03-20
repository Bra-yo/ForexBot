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

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from technical_analysis import TechnicalAnalysis
from brokers.mt5_connector import MT5Connector
from risk_management import RiskManager
from trade_manager import TradeManager

# Configure page
st.set_page_config(
    page_title="BrayoForexBot - MT5 Trading Signals",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============ TRADING CHATBOT KNOWLEDGE BASE ============
TRADING_KNOWLEDGE = {
    "indicators": {
        "rsi": """RSI (Relative Strength Index) measures momentum on a scale of 0-100.
• Below 30: Oversold condition - potential BUY signal
• Above 70: Overbought condition - potential SELL signal
• 30-70: Neutral zone - WAIT or HOLD
• RSI divergence from price can signal trend reversals.""",
        
        "macd": """MACD (Moving Average Convergence Divergence) shows trend direction and momentum.
• MACD Line crossing above Signal Line: Bullish signal
• MACD Line crossing below Signal Line: Bearish signal
• Histogram growing: Momentum increasing
• Divergence between MACD and price indicates potential reversal.""",
        
        "moving_average": """Moving Averages smooth price data to identify trends.
• SMA (Simple): Equal weight to all prices, good for long-term trends
• EMA (Exponential): More weight to recent prices, more responsive
• Price above MA: Uptrend | Price below MA: Downtrend
• Golden Cross (fast MA crosses above slow MA): Bullish
• Death Cross (fast MA crosses below slow MA): Bearish""",
        
        "bollinger_bands": """Bollinger Bands measure volatility and identify overbought/oversold conditions.
• Price touching upper band: Potentially overbought
• Price touching lower band: Potentially oversold
• Squeeze (bands narrowing): Volatility expansion likely
• Band expansion: High volatility period""",
        
        "fibonacci": """Fibonacci retracements identify potential support/resistance levels.
• Key levels: 23.6%, 38.2%, 50%, 61.8%, 78.6%
• Price often reverses at these levels
• Strong trends typically retrace to 38.2% or 50%
• Weaker trends may retrace deeper to 61.8%""",
        
        "stochastic": """Stochastic Oscillator compares closing price to price range.
• Below 20: Oversold - potential reversal up
• Above 80: Overbought - potential reversal down
• %K crossing above %D: Buy signal
• %K crossing below %D: Sell signal""",
        
        "atr": """ATR (Average True Range) measures market volatility.
• Higher ATR = More volatility = Wider stops needed
• Lower ATR = Less volatility = Tighter stops possible
• Used for position sizing and stop loss placement
• Not a directional indicator - only volatility""",
        
        "adx": """ADX (Average Directional Index) measures trend strength.
• Below 20: Weak trend or ranging market
• 20-40: Trend developing/strengthening
• Above 40: Strong trend
• Above 50: Very strong trend (potential reversal zone)
• Does NOT indicate trend direction, only strength"""
    },
    
    "patterns": {
        "candlestick": """Key Candlestick Patterns:
• Doji: Indecision, potential reversal
• Hammer/Inverted Hammer: Bullish reversal (bottom)
• Shooting Star: Bearish reversal (top)
• Engulfing: Strong reversal signal
• Morning Star: Bullish reversal pattern
• Evening Star: Bearish reversal pattern
• Harami: Potential reversal (weaker signal)""",
        
        "chart": """Common Chart Patterns:
• Head and Shoulders: Reversal pattern (bearish)
• Inverse H&S: Reversal pattern (bullish)
• Double Top/Bottom: Reversal patterns
• Triangles: Continuation patterns (ascending, descending, symmetrical)
• Flags/Pennants: Short-term continuation patterns
• Wedges: Reversal patterns (rising=bearish, falling=bullish)
• Cup and Handle: Bullish continuation""",
        
        "support_resistance": """Support and Resistance:
• Support: Price level where buying overcomes selling
• Resistance: Price level where selling overcomes buying
• Role reversal: Old support becomes new resistance (and vice versa)
• More touches = Stronger level
• Round numbers often act as S/R
• Previous highs/lows create S/R zones"""
    },
    
    "risk_management": {
        "position_sizing": """Position Sizing Principles:
• Risk only 1-2% of account per trade
• Formula: Position Size = (Account Risk $) / (Stop Loss in $)
• Never risk more than you can afford to lose
• Adjust size based on volatility (ATR)
• Smaller positions in volatile markets
• Consider correlation between positions""",
        
        "stop_loss": """Stop Loss Best Practices:
• Always use stop losses - no exceptions
• Place stops based on technical levels, not arbitrary amounts
• ATR-based stops: 1.5-2x ATR from entry
• Give trades room to breathe - avoid tight stops
• Never move stop loss further away (only trail)
• Risk:Reward ratio minimum 1:2 (preferably 1:3)""",
        
        "risk_reward": """Risk-Reward Ratio:
• Minimum 1:2 ratio (risk $1 to make $2)
• Professional traders often use 1:3 or higher
• Higher R:R allows lower win rate to be profitable
• Formula: (Target Price - Entry) / (Entry - Stop Loss)
• Don't take trades with poor R:R setups""",
        
        "drawdown": """Managing Drawdowns:
• Maximum acceptable drawdown: 10-20% of account
• Reduce position size during losing streaks
• Take breaks after consecutive losses
• Never try to "revenge trade" to recover losses
• Monthly loss limit: Stop trading if reached
• Diversify across uncorrelated pairs"""
    },
    
    "trading_psychology": {
        "emotions": """Controlling Trading Emotions:
• Fear: Causes missed opportunities, premature exits
• Greed: Causes overtrading, ignoring stops, chasing trades
• Hope: Holding losers hoping they'll recover
• FOMO: Jumping into trades without proper analysis
• Solution: Follow a trading plan with strict rules""",
        
        "discipline": """Trading Discipline:
• Create and follow a written trading plan
• Keep a detailed trading journal
• Review trades weekly/monthly
• Only trade your defined setups
• Don't trade when emotional or tired
• Accept losses as part of the business""",
        
        "patience": """The Power of Patience:
• Wait for your setup - don't force trades
• Quality over quantity in trading
• Most successful traders are selective
• Cash is a position - staying out is valid
• Missing a trade is better than losing money"""
    },
    
    "market_analysis": {
        "trend": """Trend Analysis:
• Higher highs + Higher lows = Uptrend
• Lower highs + Lower lows = Downtrend
• Mixed signals = Sideways/Ranging
• Trade with the trend, not against it
• "The trend is your friend"
• Use multiple timeframes to confirm trend""",
        
        "timeframes": """Multiple Timeframe Analysis:
• Higher timeframe: Determines major trend direction
• Middle timeframe: Entry/exit timing
• Lower timeframe: Fine-tuning entries
• Golden rule: 1:4:16 ratio (e.g., 15m, 1H, 4H)
• Always trade in direction of higher timeframe trend""",
        
        "fundamental": """Fundamental Factors in Forex:
• Interest rates: Higher rates = currency appreciation
• Economic data: GDP, employment, inflation, retail sales
• Central bank policy: Hawkish = bullish, Dovish = bearish
• Geopolitical events: Create volatility and uncertainty
• Market sentiment: Risk-on vs Risk-off flows""",
        
        "correlation": """Currency Correlations:
• EUR/USD and GBP/USD: Positive correlation (~+85%)
• EUR/USD and USD/CHF: Negative correlation (~-95%)
• AUD/USD and NZD/USD: Positive correlation (~+80%)
• Gold (XAU/USD) and USD: Negative correlation
• Don't take multiple correlated trades (increases risk)"""
    },
    
    "order_types": {
        "market": """Market Orders:
• Executed immediately at current price
• Use when you need immediate entry
• Watch for spread widening during volatile times
• Slippage can occur in fast markets""",
        
        "limit": """Limit Orders:
• Buy Limit: Order below current price
• Sell Limit: Order above current price
• Better entry prices than market orders
• Risk: Order may not fill if price doesn't reach level
• Use for buying support / selling resistance""",
        
        "stop": """Stop Orders:
• Buy Stop: Order above current price (breakout)
• Sell Stop: Order below current price (breakdown)
• Used to enter on momentum breakouts
• Also used as stop-loss orders""",
        
        "trailing": """Trailing Stop Orders:
• Automatically adjusts as price moves favorably
• Locks in profits while allowing trend continuation
• Distance set in pips or percentage
• Good for trend-following strategies
• Risk: Can be triggered by normal retracements"""
    },
    
    "forex_basics": {
        "pips": """Pips and Pipettes:
• Pip: Smallest price move (0.0001 for most pairs)
• Pipette: 1/10 of a pip (0.00001 - 5th decimal)
• JPY pairs: Pip = 0.01 (2nd decimal)
• Profit/Loss calculated in pips then converted to currency
• Spread measured in pips""",
        
        "spread": """Understanding Spread:
• Spread = Ask Price - Bid Price
• Represents broker commission
• Variable spreads widen during volatility/news
• Fixed spreads stay constant but may have slippage
• Lower spreads = lower trading costs
• Major pairs have tighter spreads than exotics""",
        
        "leverage": """Leverage in Forex:
• Leverage amplifies both gains and losses
• Common ratios: 1:50, 1:100, 1:200, 1:500
• Higher leverage = Higher risk
• Margin requirement = 1 / Leverage ratio
• Use leverage responsibly - it can wipe out accounts""",
        
        "margin": """Margin Concepts:
• Required Margin: Amount needed to open a position
• Used Margin: Total margin for all open positions
• Free Margin: Available for new positions
• Margin Level: (Equity / Used Margin) × 100%
• Margin Call: Warning when margin level is low
• Stop Out: Automatic position closure at critical level""",
        
        "rollover": """Rollover/Swap:
• Interest paid or earned for holding positions overnight
• Based on interest rate differential between currencies
• Positive swap: You earn interest (long high-rate, short low-rate)
• Negative swap: You pay interest
• Triple swap on Wednesday (covers weekend)
• Important for long-term traders"""
    },
    
    "trading_strategies": {
        "scalping": """Scalping Strategy:
• Very short-term trades (seconds to minutes)
• Target small profits (5-10 pips)
• Requires tight spreads and fast execution
• High frequency, small position sizes
• Not suitable for all traders (stressful)
• Best during high volatility sessions""",
        
        "day_trading": """Day Trading:
• Open and close positions within same day
• No overnight risk (no swap charges)
• Requires active monitoring
• Multiple trades per day possible
• Focus on high-probability setups only
• Best during London and NY sessions""",
        
        "swing_trading": """Swing Trading:
• Hold positions for days to weeks
• Capture larger price movements
• Requires wider stops
• Less time-intensive than day trading
• Suitable for part-time traders
• Focus on daily/4H charts""",
        
        "position_trading": """Position Trading:
• Long-term holding (weeks to months)
• Based on fundamental and macro trends
• Very wide stops
• Minimal time required for monitoring
• Requires larger account size
• Lowest stress trading style""",
        
        "breakout": """Breakout Trading:
• Enter when price breaks key levels
• Wait for confirmation (close beyond level)
• False breakouts common - use filters
• High volatility, strong momentum expected
• Good for trending markets
• Set stops beyond breakout level""",
        
        "range": """Range Trading:
• Buy at support, sell at resistance
• Works in sideways markets
• Clear support/resistance required
• Set tight stops beyond range
• Take profits before opposite boundary
• Not suitable for trending markets"""
    }
}

# Common off-topic responses
OFF_TOPIC_RESPONSES = [
    "I'm a trading-focused assistant. I can help you with forex trading, technical analysis, risk management, and market strategies. How can I assist with your trading today?",
    "I specialize in forex trading and financial markets. For other topics, you might want to consult a general assistant. What trading questions do you have?",
    "My knowledge is dedicated to trading and financial markets. I can explain indicators, strategies, risk management, and market psychology. How can I help with your trading?",
    "I'm designed specifically for trading assistance. I can discuss technical analysis, trading psychology, risk management, and forex markets. What would you like to know about trading?",
]

# Greeting responses
GREETING_RESPONSES = {
    "hello": "Hello! I'm your trading assistant. I can help you with technical analysis, trading strategies, risk management, and forex market knowledge. What would you like to learn about?",
    "hi": "Hi there! Ready to help you become a better trader. Ask me about indicators, chart patterns, risk management, or any trading concepts!",
    "hey": "Hey! I'm here to assist with your trading journey. What trading topic can I help you with today?",
    "good morning": "Good morning! Ready to tackle the markets? I can help you analyze setups, explain indicators, or discuss trading strategies.",
    "good afternoon": "Good afternoon! How's your trading day going? I'm here to help with any trading questions.",
    "good evening": "Good evening! Perfect time to review the markets or study trading concepts. What can I help you with?",
}

# ============ CHATBOT FUNCTIONS ============
def get_chatbot_response(user_input: str) -> str:
    """Generate trading-focused chatbot response"""
    user_input_lower = user_input.lower().strip()
    
    # Handle greetings first
    for greeting, response in GREETING_RESPONSES.items():
        if greeting in user_input_lower:
            return response
    
    # Check for specific knowledge base matches FIRST (before generic trading check)
    responses = []
    
    # FOREX BASICS - Check first for pip/spread/leverage questions (high priority)
    if any(x in user_input_lower for x in ['what is a pip', 'what\'s a pip', 'explain pip', 'pip in forex', 'pip value', 'pipette']) or \
       (('pip' in user_input_lower or 'pips' in user_input_lower) and len(user_input_lower) < 50):
        responses.append(TRADING_KNOWLEDGE["forex_basics"]["pips"])
    if 'spread' in user_input_lower and len(user_input_lower) < 100:
        responses.append(TRADING_KNOWLEDGE["forex_basics"]["spread"])
    if any(x in user_input_lower for x in ['leverage', 'leveraged', 'leveraging']) and len(user_input_lower) < 150:
        responses.append(TRADING_KNOWLEDGE["forex_basics"]["leverage"])
    if any(x in user_input_lower for x in ['margin', 'free margin', 'margin level', 'margin call', 'stop out']) and len(user_input_lower) < 150:
        responses.append(TRADING_KNOWLEDGE["forex_basics"]["margin"])
    if any(x in user_input_lower for x in ['rollover', 'swap', 'overnight fee', 'overnight interest']) and len(user_input_lower) < 150:
        responses.append(TRADING_KNOWLEDGE["forex_basics"]["rollover"])
    
    # INDICATORS
    if any(x in user_input_lower for x in ['rsi', 'relative strength', 'overbought', 'oversold']) and not responses:
        responses.append(TRADING_KNOWLEDGE["indicators"]["rsi"])
    if 'macd' in user_input_lower and not responses:
        responses.append(TRADING_KNOWLEDGE["indicators"]["macd"])
    if any(x in user_input_lower for x in ['moving average', 'sma', 'ema', 'simple moving', 'exponential moving']) and not responses:
        responses.append(TRADING_KNOWLEDGE["indicators"]["moving_average"])
    if 'bollinger' in user_input_lower and not responses:
        responses.append(TRADING_KNOWLEDGE["indicators"]["bollinger_bands"])
    if any(x in user_input_lower for x in ['fibonacci', 'fib retracement', 'fib level']) and not responses:
        responses.append(TRADING_KNOWLEDGE["indicators"]["fibonacci"])
    if 'stochastic' in user_input_lower and not responses:
        responses.append(TRADING_KNOWLEDGE["indicators"]["stochastic"])
    if any(x in user_input_lower for x in ['atr', 'average true range', 'volatility indicator']) and not responses:
        responses.append(TRADING_KNOWLEDGE["indicators"]["atr"])
    if 'adx' in user_input_lower and not responses:
        responses.append(TRADING_KNOWLEDGE["indicators"]["adx"])
    
    # PATTERNS
    if any(x in user_input_lower for x in ['candlestick', 'doji', 'hammer', 'shooting star', 'engulfing', 'morning star', 'evening star']) and not responses:
        responses.append(TRADING_KNOWLEDGE["patterns"]["candlestick"])
    if any(x in user_input_lower for x in ['chart pattern', 'head and shoulders', 'triangle pattern', 'flag pattern', 'wedge pattern', 'double top', 'double bottom']) and not responses:
        responses.append(TRADING_KNOWLEDGE["patterns"]["chart"])
    if any(x in user_input_lower for x in ['support', 'resistance', 'support level', 'resistance level', 's/r']) and not responses:
        responses.append(TRADING_KNOWLEDGE["patterns"]["support_resistance"])
    
    # RISK MANAGEMENT
    if any(x in user_input_lower for x in ['position size', 'position sizing', 'lot size', 'how many lots', 'calculate position']) and not responses:
        responses.append(TRADING_KNOWLEDGE["risk_management"]["position_sizing"])
    if any(x in user_input_lower for x in ['stop loss', 'stoploss', 'sl', 'where to place stop']) and not responses:
        responses.append(TRADING_KNOWLEDGE["risk_management"]["stop_loss"])
    if any(x in user_input_lower for x in ['risk reward', 'risk:reward', 'risk to reward', 'r:r', 'risk ratio']) and not responses:
        responses.append(TRADING_KNOWLEDGE["risk_management"]["risk_reward"])
    if 'drawdown' in user_input_lower and not responses:
        responses.append(TRADING_KNOWLEDGE["risk_management"]["drawdown"])
    
    # PSYCHOLOGY
    if any(x in user_input_lower for x in ['emotion', 'fear', 'greed', 'fomo', 'trading psychology', 'psychology']) and not responses:
        responses.append(TRADING_KNOWLEDGE["trading_psychology"]["emotions"])
    if 'discipline' in user_input_lower and not responses:
        responses.append(TRADING_KNOWLEDGE["trading_psychology"]["discipline"])
    if 'patience' in user_input_lower and not responses:
        responses.append(TRADING_KNOWLEDGE["trading_psychology"]["patience"])
    
    # MARKET ANALYSIS
    if any(x in user_input_lower for x in ['trend', 'trending', 'uptrend', 'downtrend', 'bullish', 'bearish']) and not responses:
        responses.append(TRADING_KNOWLEDGE["market_analysis"]["trend"])
    if any(x in user_input_lower for x in ['timeframe', 'time frame', 'time frame', 'higher timeframe', 'multiple timeframe']) and not responses:
        responses.append(TRADING_KNOWLEDGE["market_analysis"]["timeframes"])
    if any(x in user_input_lower for x in ['fundamental', 'fundamentals', 'news trading', 'economic data', 'economic calendar']) and not responses:
        responses.append(TRADING_KNOWLEDGE["market_analysis"]["fundamental"])
    if 'correlation' in user_input_lower and not responses:
        responses.append(TRADING_KNOWLEDGE["market_analysis"]["correlation"])
    
    # ORDER TYPES
    if any(x in user_input_lower for x in ['market order', 'market execution', 'instant execution']) and not responses:
        responses.append(TRADING_KNOWLEDGE["order_types"]["market"])
    if any(x in user_input_lower for x in ['limit order', 'buy limit', 'sell limit', 'limit entry']) and not responses:
        responses.append(TRADING_KNOWLEDGE["order_types"]["limit"])
    if any(x in user_input_lower for x in ['stop order', 'buy stop', 'sell stop', 'stop entry']) and not responses:
        responses.append(TRADING_KNOWLEDGE["order_types"]["stop"])
    if 'trailing' in user_input_lower and not responses:
        responses.append(TRADING_KNOWLEDGE["order_types"]["trailing"])
    
    # STRATEGIES
    if any(x in user_input_lower for x in ['scalping', 'scalp', 'scalper']) and not responses:
        responses.append(TRADING_KNOWLEDGE["trading_strategies"]["scalping"])
    if any(x in user_input_lower for x in ['day trading', 'daytrade', 'day trader', 'intraday']) and not responses:
        responses.append(TRADING_KNOWLEDGE["trading_strategies"]["day_trading"])
    if any(x in user_input_lower for x in ['swing trading', 'swing trade', 'swing trader']) and not responses:
        responses.append(TRADING_KNOWLEDGE["trading_strategies"]["swing_trading"])
    if any(x in user_input_lower for x in ['position trading', 'long term trading', 'long-term']) and not responses:
        responses.append(TRADING_KNOWLEDGE["trading_strategies"]["position_trading"])
    if 'breakout' in user_input_lower and not responses:
        responses.append(TRADING_KNOWLEDGE["trading_strategies"]["breakout"])
    if any(x in user_input_lower for x in ['range trading', 'ranging market', 'range bound']) and not responses:
        responses.append(TRADING_KNOWLEDGE["trading_strategies"]["range"])
    
    # If we found specific responses, combine and return them
    if responses:
        return "\n\n".join(responses)
    
    # Check if input is trading-related for generic responses
    trading_keywords = [
        'rsi', 'macd', 'moving average', 'ema', 'sma', 'bollinger', 'fibonacci', 'stochastic', 
        'atr', 'adx', 'obv', 'cci', 'williams', 'momentum', 'volume', 'indicator',
        'pattern', 'candlestick', 'support', 'resistance', 'doji', 'hammer', 'engulfing',
        'head and shoulders', 'triangle', 'flag', 'wedge', 'trendline',
        'risk', 'stop loss', 'take profit', 'position size', 'drawdown', 'risk reward', 
        'money management', 'leverage', 'margin', 'account risk',
        'pips', 'spread', 'lot', 'long', 'short', 'buy', 'sell', 'entry', 'exit',
        'trend', 'bullish', 'bearish', 'uptrend', 'downtrend', 'sideways', 'range',
        'market order', 'limit order', 'stop order', 'trailing stop', 'pending order',
        'strategy', 'scalping', 'day trading', 'swing trading', 'position trading',
        'breakout', 'reversal', 'trend following', 'range trading',
        'fundamental', 'technical', 'sentiment', 'correlation', 'timeframe', 'chart',
        'psychology', 'emotion', 'discipline', 'patience', 'fomo', 'fear', 'greed',
        'forex', 'currency', 'pair', 'eurusd', 'gbpusd', 'usd', 'eur', 'gbp', 'jpy',
        'gold', 'xau', 'commodity', 'index', 'session', 'london', 'new york', 'asian',
        'trade', 'trading', 'market', 'price', 'analysis', 'setup', 'signal'
    ]
    
    is_trading_related = any(keyword in user_input_lower for keyword in trading_keywords)
    
    # Return off-topic response for non-trading queries
    if not is_trading_related and len(user_input_lower) > 3:
        return random.choice(OFF_TOPIC_RESPONSES)
    
    # Default responses for general trading questions
    if any(x in user_input_lower for x in ['how to trade', 'start trading', 'beginner', 'new trader']):
        return """Welcome to trading! Here's how to get started:

1. **Learn the Basics**: Understand pips, spreads, leverage, and margin
2. **Study Technical Analysis**: Learn to read charts and use indicators
3. **Master Risk Management**: Never risk more than 1-2% per trade
4. **Choose a Strategy**: Scalping, day trading, swing trading, or position trading
5. **Practice on Demo**: Use a demo account before trading real money
6. **Keep a Journal**: Track all your trades to learn from mistakes

What specific aspect would you like to explore first?"""
    
    if any(x in user_input_lower for x in ['help', 'what can you do', 'capabilities', 'what do you know']):
        return """I'm your trading assistant! I can help you with:

📊 **Technical Indicators**: RSI, MACD, Moving Averages, Bollinger Bands, Fibonacci, and more
📈 **Chart Patterns**: Candlestick patterns, support/resistance, trend analysis
🛡️ **Risk Management**: Position sizing, stop losses, risk-reward ratios
🧠 **Trading Psychology**: Controlling emotions, discipline, patience
📚 **Trading Strategies**: Scalping, day trading, swing trading, breakout, range trading
💱 **Forex Basics**: Pips, spreads, leverage, margin, rollover
📉 **Order Types**: Market, limit, stop, and trailing stop orders

Ask me about any trading topic!"""
    
    # Final fallback for trading-related but unrecognized queries
    if is_trading_related:
        return """That's an interesting trading question! While I don't have specific information on that exact topic, I can help you with:

• Technical analysis and indicators
• Risk management strategies  
• Trading psychology and discipline
• Chart patterns and price action
• Forex basics and order types
• Various trading strategies

Could you rephrase your question or ask about a specific trading concept you'd like to learn?"""
    
    # Off-topic fallback
    return random.choice(OFF_TOPIC_RESPONSES)

def initialize_session_state():
    """Initialize session state variables"""
    if 'mt5_connected' not in st.session_state:
        st.session_state.mt5_connected = False
    if 'mt5_connector' not in st.session_state:
        st.session_state.mt5_connector = None
    if 'show_login' not in st.session_state:
        st.session_state.show_login = True
    if 'selected_timeframe' not in st.session_state:
        st.session_state.selected_timeframe = 'H1'
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now()
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = True
    if 'selected_volume' not in st.session_state:
        st.session_state.selected_volume = 0.1  # Default to 0.1 lots
    if 'show_chatbot' not in st.session_state:
        st.session_state.show_chatbot = False  # Chatbot hidden by default
    
    # Advanced Bot Features
    if 'active_trades' not in st.session_state:
        st.session_state.active_trades = []  # Track open trades
    if 'daily_loss' not in st.session_state:
        st.session_state.daily_loss = 0.0  # Track daily losses
    if 'last_trade_date' not in st.session_state:
        st.session_state.last_trade_date = datetime.now().date()
    if 'bot_settings' not in st.session_state:
        st.session_state.bot_settings = {
            'trailing_stop_enabled': True,
            'break_even_enabled': True,
            'time_exit_enabled': True,
            'max_daily_loss': 100.0,  # $100 max daily loss
            'max_trade_time_minutes': 10,  # Close trade after 10 minutes if no profit
            'min_profit_pips': 10,  # Move to break-even at 10 pips
            'trailing_profit_pips': 20,  # Move SL to +10 pips at 20 pips profit
            'spread_filter_enabled': True,
            'max_spread_pips': 5  # Don't trade if spread > 5 pips
        }

# ============ CUSTOM CSS ============
st.markdown("""
<style>
/* Login page styling */
.login-container {
    max-width: 400px;
    margin: 0 auto;
    padding: 40px;
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
    border-radius: 20px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.3);
}

.login-title {
    text-align: center;
    color: white;
    font-size: 2.5em;
    margin-bottom: 10px;
}

.login-subtitle {
    text-align: center;
    color: #a0c4ff;
    margin-bottom: 30px;
}

/* Chatbot styling */
.chatbot-container {
    background: #1e1e1e;
    border-radius: 15px;
    padding: 20px;
    margin-top: 20px;
    border: 1px solid #333;
}

.chat-message {
    padding: 12px 16px;
    border-radius: 12px;
    margin: 8px 0;
    max-width: 80%;
}

.chat-user {
    background: #2a5298;
    color: white;
    margin-left: auto;
    text-align: right;
}

.chat-bot {
    background: #2d2d2d;
    color: #e0e0e0;
    border-left: 4px solid #4CAF50;
}

.chat-header {
    background: linear-gradient(90deg, #4CAF50, #8BC34A);
    color: white;
    padding: 15px;
    border-radius: 10px 10px 0 0;
    font-weight: bold;
    display: flex;
    align-items: center;
    gap: 10px;
}

/* Logout button */
.logout-btn {
    background: linear-gradient(90deg, #f44336, #d32f2f) !important;
    color: white !important;
    border: none !important;
    padding: 10px 20px !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    width: 100% !important;
}

/* Signal styling */
.signal-buy {
    background: linear-gradient(135deg, #4CAF50, #45a049);
    padding: 20px;
    border-radius: 10px;
    color: white;
}

.signal-sell {
    background: linear-gradient(135deg, #f44336, #d32f2f);
    padding: 20px;
    border-radius: 10px;
    color: white;
}

.signal-wait {
    background: linear-gradient(135deg, #ff9800, #f57c00);
    padding: 20px;
    border-radius: 10px;
    color: white;
}

/* Status indicators */
.status-connected {
    color: #4CAF50;
    font-weight: bold;
}

.status-disconnected {
    color: #f44336;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)


# ============ LOGIN PAGE ============
def render_login_page():
    """Render full-screen login page"""
    # Create three columns to center the login form
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-top: 50px;">
            <h1 style="font-size: 3em; margin-bottom: 10px;">🎯 BrayoForexBot</h1>
            <h2 style="color: #666; margin-bottom: 40px;">Professional Trading Dashboard</h2>
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
                    with st.spinner("🔄 Connecting to MT5..."):
                        try:
                            connector = MT5Connector()
                            
                            if connector.initialize(
                                login=int(mt5_login),
                                password=mt5_password,
                                server=mt5_server
                            ):
                                st.session_state.mt5_connected = True
                                st.session_state.mt5_connector = connector
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
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
            max-width: 400px;
            margin-left: auto;
            margin-right: auto;
        ">
            <p style="margin: 0; color: #856404;">
                <strong>🔒 Security Notice:</strong><br>
                Your credentials are used only to connect to MT5 and are not stored. 
                This dashboard runs locally on your machine.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Features showcase
        st.markdown("""
        <div style="margin-top: 50px; text-align: center;">
            <h3>✨ Features</h3>
            <div style="display: flex; justify-content: center; flex-wrap: wrap; gap: 20px; margin-top: 20px;">
                <div style="background: #f0f0f0; padding: 15px; border-radius: 10px; min-width: 150px;">
                    📊 Live Signals
                </div>
                <div style="background: #f0f0f0; padding: 15px; border-radius: 10px; min-width: 150px;">
                    🤖 AI Assistant
                </div>
                <div style="background: #f0f0f0; padding: 15px; border-radius: 10px; min-width: 150px;">
                    📈 Real-time Data
                </div>
                <div style="background: #f0f0f0; padding: 15px; border-radius: 10px; min-width: 150px;">
                    🛡️ Risk Management
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ============ LOGOUT FUNCTION ============
def logout():
    """Disconnect MT5 and return to login page"""
    try:
        if st.session_state.mt5_connector:
            st.session_state.mt5_connector.disconnect()
            st.session_state.mt5_connector = None
        st.session_state.mt5_connected = False
        st.session_state.chat_history = []
        st.session_state.show_chatbot = False
        st.success("👋 Logged out successfully. MT5 connection closed.")
        st.rerun()
    except Exception as e:
        st.error(f"Error during logout: {e}")


# ============ SIDEBAR (POST-LOGIN) ============
def render_sidebar_logged_in():
    """Render sidebar for logged-in users"""
    with st.sidebar:
        st.header("🎛️ Control Panel")
        
        # Account Info
        st.subheader("🏦 Account Status")
        st.markdown('<span class="status-connected">● MT5 Connected</span>', unsafe_allow_html=True)
        
        try:
            if st.session_state.mt5_connector:
                account_info = st.session_state.mt5_connector.get_account_info()
                if 'error' not in account_info:
                    st.write(f"**Login:** {account_info['login']}")
                    st.write(f"**Balance:** ${account_info['balance']:.2f}")
                    st.write(f"**Equity:** ${account_info['equity']:.2f}")
                    st.write(f"**Free Margin:** ${account_info['free_margin']:.2f}")
        except Exception as e:
            st.error(f"Error loading account info: {e}")
        
        st.markdown("---")
        
        # Chatbot Toggle
        st.subheader("🤖 Trading Assistant")
        if st.button("💬 Open Chatbot" if not st.session_state.show_chatbot else "❌ Close Chatbot", 
                     use_container_width=True):
            st.session_state.show_chatbot = not st.session_state.show_chatbot
            st.rerun()
        
        # Refresh Button with timestamp
        st.markdown("---")
        st.subheader("📊 Data Settings")
        
        # Timeframe selector
        timeframe_options = {
            'M1': '1 Minute',
            'M5': '5 Minutes', 
            'M15': '15 Minutes',
            'M30': '30 Minutes',
            'H1': '1 Hour',
            'H4': '4 Hours',
        }
        timeframes = list(timeframe_options.keys())
        selected_tf = st.selectbox(
            "Select Timeframe:",
            options=timeframes,
            index=timeframes.index(st.session_state.selected_timeframe),
            key="timeframe_selector"
        )
        
        if selected_tf != st.session_state.selected_timeframe:
            st.session_state.selected_timeframe = selected_tf
            st.rerun()
        
        # Volume selection
        st.markdown("### 📏 Volume Size")
        volume_options = [0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
        selected_vol = st.selectbox(
            "Select Volume (Lots):",
            options=volume_options,
            index=volume_options.index(st.session_state.selected_volume),
            key="volume_selector"
        )
        
        if selected_vol != st.session_state.selected_volume:
            st.session_state.selected_volume = selected_vol
            st.rerun()
        
        # Auto-refresh toggle
        st.markdown("### 🔄 Auto Refresh")
        auto_refresh = st.checkbox(
            "Enable Auto-refresh (30s)",
            value=st.session_state.get('auto_refresh', True),
            key="auto_refresh_toggle"
        )
        
        if auto_refresh != st.session_state.get('auto_refresh', True):
            st.session_state.auto_refresh = auto_refresh
            st.rerun()
        
        # Refresh Button with timestamp
        st.markdown("---")
        st.subheader("📊 Data Settings")
        if st.button("🔄 Refresh Data Now", use_container_width=True):
            # Only refresh data, not full trade monitoring
            st.session_state.last_refresh = datetime.now()
            st.rerun()
        
        # Show last refresh time
        time_since_refresh = (datetime.now() - st.session_state.last_refresh).seconds
        st.caption(f"Last update: {time_since_refresh}s ago")
        
        st.markdown("---")
        
        # Bot Settings Panel
        st.markdown("---")
        st.markdown("### 🤖 Bot Settings")
        
        # Toggle bot features
        st.session_state.bot_settings['trailing_stop_enabled'] = st.checkbox(
            "🔄 Trailing Stop", 
            value=st.session_state.bot_settings['trailing_stop_enabled']
        )
        
        st.session_state.bot_settings['break_even_enabled'] = st.checkbox(
            "🛡️ Break-even Protection", 
            value=st.session_state.bot_settings['break_even_enabled']
        )
        
        st.session_state.bot_settings['time_exit_enabled'] = st.checkbox(
            "⏰ Time-based Exit", 
            value=st.session_state.bot_settings['time_exit_enabled']
        )
        
        st.session_state.bot_settings['spread_filter_enabled'] = st.checkbox(
            "� Spread Filter", 
            value=st.session_state.bot_settings['spread_filter_enabled']
        )
        
        # Advanced settings
        with st.expander("⚙️ Advanced Settings"):
            st.session_state.bot_settings['max_daily_loss'] = st.number_input(
                "Max Daily Loss ($)",
                min_value=10.0,
                max_value=1000.0,
                value=st.session_state.bot_settings['max_daily_loss'],
                step=10.0
            )
            
            st.session_state.bot_settings['max_trade_time_minutes'] = st.number_input(
                "Max Trade Time (minutes)",
                min_value=1,
                max_value=60,
                value=st.session_state.bot_settings['max_trade_time_minutes']
            )
            
            st.session_state.bot_settings['min_profit_pips'] = st.number_input(
                "Break-even at (pips)",
                min_value=5,
                max_value=50,
                value=st.session_state.bot_settings['min_profit_pips']
            )
            
            st.session_state.bot_settings['max_spread_pips'] = st.number_input(
                "Max Spread (pips)",
                min_value=1,
                max_value=20,
                value=st.session_state.bot_settings['max_spread_pips']
            )
        
        # Active Trades Monitor
        st.markdown("---")
        st.markdown("### 📈 Active Trades")
        
        if st.session_state.active_trades:
            # Display active trades (automatic monitoring happens in main dashboard)
            for trade in st.session_state.active_trades:
                with st.expander(f"📊 Trade #{trade['ticket']} - {trade['type']}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Symbol", trade['symbol'])
                        st.metric("Volume", f"{trade['volume']:.2f}")
                    with col2:
                        st.metric("Entry", f"{trade['entry_price']:.5f}")
                        st.metric("SL", f"{trade['stop_loss']:.5f}")
                    with col3:
                        st.metric("TP", f"{trade['take_profit']:.5f}")
                        duration = datetime.now() - trade['open_time']
                        st.metric("Duration", f"{duration.total_seconds()/60:.1f}m")
        else:
            st.info("📭 No active trades")
        
        # Daily loss tracking
        if st.session_state.daily_loss > 0:
            st.warning(f"⚠️ Daily Loss: ${st.session_state.daily_loss:.2f} / ${st.session_state.bot_settings['max_daily_loss']:.2f}")
        
        # Logout button
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            logout()
        
        # Safety warning
        st.markdown("""
        <div style="
            background: #ffebee;
            border: 1px solid #f44336;
            border-radius: 5px;
            padding: 10px;
            margin-top: 20px;
            font-size: 0.9em;
        ">
            <strong>⚠️ Trading Risk:</strong><br>
            Forex trading involves significant risk. 
            Never trade with money you cannot afford to lose.
        </div>
        """, unsafe_allow_html=True)


# ============ CHATBOT INTERFACE ============
def render_chatbot():
    """Render the trading chatbot interface"""
    if not st.session_state.show_chatbot:
        return
    
    st.markdown("""
    <div class="chatbot-container">
        <div class="chat-header">
            <span style="font-size: 1.5em;">🤖</span>
            <span>Trading Assistant - Ask me anything about trading!</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Display chat history
    for msg in st.session_state.chat_history:
        if msg['role'] == 'user':
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-end; margin: 5px 0;">
                <div style="background: #2a5298; color: white; padding: 10px 15px; border-radius: 15px 15px 0 15px; max-width: 70%;">
                    {msg['content']}
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="display: flex; justify-content: flex-start; margin: 5px 0;">
                <div style="background: #2d2d2d; color: #e0e0e0; padding: 10px 15px; border-radius: 15px 15px 15px 0; max-width: 70%; border-left: 4px solid #4CAF50;">
                    <span style="color: #4CAF50; font-weight: bold;">🤖 Assistant:</span><br>
                    {msg['content'].replace(chr(10), '<br>')}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    # Quick suggestions
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("**Quick Questions:**")
    
    quick_questions = [
        "What is RSI?",
        "How do I set a stop loss?",
        "Explain risk-reward ratio",
        "What's a pip?",
        "How does leverage work?",
    ]
    
    cols = st.columns(len(quick_questions))
    for idx, question in enumerate(quick_questions):
        with cols[idx]:
            if st.button(question, key=f"quick_{idx}", use_container_width=True):
                st.session_state.chat_history.append({'role': 'user', 'content': question})
                response = get_chatbot_response(question)
                st.session_state.chat_history.append({'role': 'assistant', 'content': response})
                st.rerun()
    
    # Chat input
    st.markdown("<br>", unsafe_allow_html=True)
    user_input = st.chat_input("Ask about trading indicators, strategies, risk management...")
    
    if user_input:
        # Add user message to history
        st.session_state.chat_history.append({'role': 'user', 'content': user_input})
        
        # Get bot response
        response = get_chatbot_response(user_input)
        st.session_state.chat_history.append({'role': 'assistant', 'content': response})
        
        st.rerun()
    
    # Clear chat button
    if st.session_state.chat_history:
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)


# ============ MAIN DASHBOARD (POST-LOGIN) ============
def render_main_dashboard():
    """Render main trading dashboard after login"""
    st.title("🎯 BrayoForexBot - Live Trading Signals")
    
    # Auto-refresh mechanism
    if st.session_state.get('auto_refresh', True):
        time_since_refresh = (datetime.now() - st.session_state.last_refresh).seconds
        if time_since_refresh >= 3:  # Refresh every 3 seconds for real-time monitoring
            st.session_state.last_refresh = datetime.now()
            st.rerun()
    
    # Signal generation section
    st.markdown("### 🎯 Live Trading Signal")
    
    # Show current timeframe
    st.caption(f"Current Timeframe: **{st.session_state.selected_timeframe}** | Auto-refresh: **{'ON' if st.session_state.get('auto_refresh', True) else 'OFF'}**")
    
    # Monitor active trades on every refresh (REAL-TIME AUTOMATION)
    if st.session_state.mt5_connected and st.session_state.mt5_connector:
        try:
            trade_manager = TradeManager(st.session_state.mt5_connector)
            
            # Debug: Check current state
            print(f"DEBUG - Active trades count: {len(st.session_state.active_trades)}")
            
            # Sync with MT5 positions every refresh
            trade_manager.sync_with_mt5_positions()
            print(f"DEBUG - After sync, active trades count: {len(st.session_state.active_trades)}")
            
            # Monitor for SL/TP and all exit logic on every refresh
            if st.session_state.active_trades:
                print(f"DEBUG - Monitoring {len(st.session_state.active_trades)} trades")
                closed_trades = trade_manager.monitor_active_trades(st.session_state.bot_settings)
                if closed_trades:
                    print(f"DEBUG - Closed {len(closed_trades)} trades")
                    for trade in closed_trades:
                        if 'error' not in trade:
                            st.success(f"📊 Trade #{trade['ticket']} closed: {trade['reason']} | P&L: ${trade['profit']:.2f}")
                        else:
                            st.error(f"❌ Error closing trade #{trade['ticket']}: {trade['error']}")
                else:
                    print("DEBUG - No trades closed this cycle")
            else:
                print("DEBUG - No active trades to monitor")
        except Exception as e:
            print(f"DEBUG - Error in trade monitoring: {e}")
            st.error(f"❌ Error monitoring trades: {e}")
    
    if st.session_state.mt5_connected and st.session_state.mt5_connector:
        try:
            with st.spinner("📊 Analyzing market data..."):
                # Fetch historical data based on selected timeframe
                end_date = datetime.now()
                
                # Adjust lookback period based on timeframe
                tf_days_map = {
                    'M1': 1, 'M5': 2, 'M15': 3, 'M30': 5,
                    'H1': 7, 'H4': 30, 'D1': 90, 'W1': 365
                }
                lookback_days = tf_days_map.get(st.session_state.selected_timeframe, 7)
                start_date = end_date - timedelta(days=lookback_days)
                
                historical_data = st.session_state.mt5_connector.get_historical_data(
                    symbol="EURUSD",
                    timeframe=st.session_state.selected_timeframe,
                    start_date=start_date,
                    end_date=end_date
                )
                
                if historical_data is not None and len(historical_data) > 0:
                    current_price = historical_data['close'].iloc[-1]
                    
                    st.success(f"✅ Using live price from MT5: **{current_price:.5f}** (from {len(historical_data)} data points)")
                    
                    # Calculate indicators
                    ta = TechnicalAnalysis()
                    rsi = ta.calculate_rsi(historical_data['close'], period=14)
                    sma_fast, sma_slow = ta.calculate_moving_averages(historical_data['close'])
                    
                    latest_rsi = rsi.iloc[-1] if not rsi.empty else 50
                    latest_sma = sma_fast.iloc[-1] if not sma_fast.empty else current_price
                    latest_ema = sma_slow.iloc[-1] if not sma_slow.empty else current_price
                    
                    # Enhanced signal generation with more indicators
                    signal_strength = 0
                    reasons = []
                    confidence_factors = []
                    
                    # RSI Analysis (more nuanced)
                    if latest_rsi < 25:
                        signal_strength += 3
                        reasons.append(f"RSI strongly oversold ({latest_rsi:.1f})")
                        confidence_factors.append("Strong RSI oversold signal")
                    elif latest_rsi < 35:
                        signal_strength += 2
                        reasons.append(f"RSI oversold ({latest_rsi:.1f})")
                        confidence_factors.append("RSI oversold")
                    elif latest_rsi < 45:
                        signal_strength += 1
                        reasons.append(f"RSI approaching oversold ({latest_rsi:.1f})")
                        confidence_factors.append("RSI bearish momentum")
                    elif latest_rsi > 75:
                        signal_strength -= 3
                        reasons.append(f"RSI strongly overbought ({latest_rsi:.1f})")
                        confidence_factors.append("Strong RSI overbought signal")
                    elif latest_rsi > 65:
                        signal_strength -= 2
                        reasons.append(f"RSI overbought ({latest_rsi:.1f})")
                        confidence_factors.append("RSI overbought")
                    elif latest_rsi > 55:
                        signal_strength -= 1
                        reasons.append(f"RSI approaching overbought ({latest_rsi:.1f})")
                        confidence_factors.append("RSI bullish momentum")
                    else:
                        confidence_factors.append("RSI neutral")
                    
                    # Moving Average Analysis (more detailed)
                    ema_sma_diff = latest_ema - latest_sma
                    ema_sma_pct_diff = (ema_sma_diff / latest_sma) * 100
                    
                    if ema_sma_pct_diff > 0.1:  # EMA significantly above SMA
                        signal_strength += 2
                        reasons.append(f"EMA strongly above SMA (+{ema_sma_pct_diff:.2f}%)")
                        confidence_factors.append("Strong uptrend")
                    elif ema_sma_pct_diff > 0.02:  # EMA slightly above SMA
                        signal_strength += 1
                        reasons.append(f"EMA above SMA (+{ema_sma_pct_diff:.2f}%)")
                        confidence_factors.append("Moderate uptrend")
                    elif ema_sma_pct_diff < -0.1:  # EMA significantly below SMA
                        signal_strength -= 2
                        reasons.append(f"EMA strongly below SMA ({ema_sma_pct_diff:.2f}%)")
                        confidence_factors.append("Strong downtrend")
                    elif ema_sma_pct_diff < -0.02:  # EMA slightly below SMA
                        signal_strength -= 1
                        reasons.append(f"EMA below SMA ({ema_sma_pct_diff:.2f}%)")
                        confidence_factors.append("Moderate downtrend")
                    else:
                        confidence_factors.append("MA trend neutral")
                    
                    # Price Action Analysis (add price momentum)
                    if len(historical_data) >= 5:
                        price_change = (historical_data['close'].iloc[-1] - historical_data['close'].iloc[-5]) / historical_data['close'].iloc[-5] * 100
                        if price_change > 0.3:
                            signal_strength += 1
                            reasons.append(f"Strong upward momentum (+{price_change:.2f}% in 5 periods)")
                            confidence_factors.append("Price momentum bullish")
                        elif price_change > 0.1:
                            signal_strength += 0.5
                            reasons.append(f"Moderate upward momentum (+{price_change:.2f}% in 5 periods)")
                            confidence_factors.append("Price momentum slightly bullish")
                        elif price_change < -0.3:
                            signal_strength -= 1
                            reasons.append(f"Strong downward momentum ({price_change:.2f}% in 5 periods)")
                            confidence_factors.append("Price momentum bearish")
                        elif price_change < -0.1:
                            signal_strength -= 0.5
                            reasons.append(f"Moderate downward momentum ({price_change:.2f}% in 5 periods)")
                            confidence_factors.append("Price momentum slightly bearish")
                        else:
                            confidence_factors.append("Price momentum neutral")
                    
                    # Volatility Analysis (using ATR if available)
                    if len(historical_data) >= 14:
                        high_low_diff = historical_data['high'] - historical_data['low']
                        avg_range = high_low_diff.rolling(14).mean().iloc[-1]
                        current_range = high_low_diff.iloc[-1]
                        
                        if current_range > avg_range * 1.5:
                            reasons.append("High volatility detected")
                            confidence_factors.append("High volatility")
                        elif current_range < avg_range * 0.5:
                            reasons.append("Low volatility detected")
                            confidence_factors.append("Low volatility")
                    
                    # Enhanced decision logic with more granular levels
                    if signal_strength >= 4:
                        decision = "STRONG BUY"
                        confidence = min(95, 70 + signal_strength * 5)
                        signal_color = "signal-buy"
                        emoji = "🟢"
                    elif signal_strength >= 2:
                        decision = "BUY"
                        confidence = min(85, 60 + signal_strength * 8)
                        signal_color = "signal-buy"
                        emoji = "🟢"
                    elif signal_strength >= 0.5:
                        decision = "WEAK BUY"
                        confidence = min(75, 55 + signal_strength * 10)
                        signal_color = "signal-wait"
                        emoji = "🟡"
                    elif signal_strength >= -0.5:
                        decision = "NEUTRAL"
                        confidence = 50 + abs(signal_strength) * 10
                        signal_color = "signal-wait"
                        emoji = "🟡"
                    elif signal_strength >= -2:
                        decision = "WEAK SELL"
                        confidence = min(75, 55 + abs(signal_strength) * 10)
                        signal_color = "signal-wait"
                        emoji = "🟡"
                    elif signal_strength >= -4:
                        decision = "SELL"
                        confidence = min(85, 60 + abs(signal_strength) * 8)
                        signal_color = "signal-sell"
                        emoji = "🔴"
                    else:
                        decision = "STRONG SELL"
                        confidence = min(95, 70 + abs(signal_strength) * 5)
                        signal_color = "signal-sell"
                        emoji = "�"
                    
                    # Add analysis summary
                    analysis_summary = f"Signal Strength: {signal_strength:+.1f} | Factors: {len(confidence_factors)} analyzed"
                    reasons.insert(0, analysis_summary)
                    
                    # Calculate SL/TP with proper MT5 symbol requirements
                    try:
                        # Get symbol info for minimum distances
                        symbol_info = st.session_state.mt5_connector.get_symbol_info("EURUSD")
                        if 'error' not in symbol_info:
                            # Get minimum stop level from MT5
                            min_stop_level = symbol_info.get('trade_stops_level', 0)
                            point = symbol_info.get('point', 0.00001)
                            
                            # Calculate minimum required pips
                            if min_stop_level > 0:
                                min_pips = max(min_stop_level / point, 5)  # At least 5 pips
                            else:
                                min_pips = 5  # Default minimum
                            stop_loss_pips = max(20, min_pips)  # Use larger of 20 pips or minimum
                        else:
                            # Fallback values
                            stop_loss_pips = 20
                            point = 0.00001
                    except Exception as e:
                        # Fallback if symbol info fails
                        stop_loss_pips = 20
                        point = 0.00001
                    
                    # Use conservative approach: wider stops to be safe
                    stop_loss_pips = max(stop_loss_pips, 30)  # Ensure at least 30 pips
                    
                    if decision in ["BUY", "STRONG BUY"]:
                        stop_loss_price = current_price - (stop_loss_pips * point)
                        take_profit_price = current_price + (stop_loss_pips * point * 1.5)  # 1.5:1 RR
                    elif decision in ["SELL", "STRONG SELL"]:
                        stop_loss_price = current_price + (stop_loss_pips * point)
                        take_profit_price = current_price - (stop_loss_pips * point * 1.5)  # 1.5:1 RR
                    else:
                        # For neutral/weak signals, use wider stops
                        stop_loss_price = current_price - (stop_loss_pips * point)
                        take_profit_price = current_price + (stop_loss_pips * point * 1.5)
                    
                    # Validate SL/TP prices are reasonable
                    if stop_loss_price <= 0 or take_profit_price <= 0:
                        st.error("❌ Invalid SL/TP calculated. Using fallback values.")
                        stop_loss_price = current_price * 0.999  # 0.1% SL
                        take_profit_price = current_price * 1.0015  # 0.15% TP
                    
                    # Use user-selected volume instead of calculated position size
                    position_size = st.session_state.selected_volume
                    
                    # Display signal
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        st.markdown(f"""
                        <div class="{signal_color}">
                            <h2>{emoji} {decision}</h2>
                            <p><strong>Confidence:</strong> {confidence:.0f}%</p>
                            <p><strong>Entry Price:</strong> {current_price:.5f}</p>
                            <p><strong>Stop Loss:</strong> {stop_loss_price:.5f}</p>
                            <p><strong>Take Profit:</strong> {take_profit_price:.5f}</p>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with col2:
                        if decision not in ["NEUTRAL", "WAIT"]:
                            st.metric("Position Size", f"{position_size:.2f} lots")
                            st.metric("Risk Amount", f"${10000 * 0.02:.2f}")
                            st.metric("Potential Reward", f"${10000 * 0.02 * 1.5:.2f}")
                            
                            # Add order placement button
                            st.markdown("---")
                            st.markdown("### 🎯 Order Placement")
                            
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                if st.button(f"📈 Place {decision} Order", 
                                           use_container_width=True,
                                           type="primary"):
                                    try:
                                        # Initialize trade manager
                                        trade_manager = TradeManager(st.session_state.mt5_connector)
                                        
                                        # Check daily loss limit
                                        if trade_manager.check_daily_loss_limit(st.session_state.bot_settings):
                                            st.error("❌ Daily loss limit reached. Trading stopped.")
                                            return
                                        
                                        # Check spread filter
                                        if not trade_manager.check_spread_filter("EURUSD", st.session_state.bot_settings):
                                            st.error("❌ Spread too high. Trade blocked.")
                                            return
                                        
                                        result = st.session_state.mt5_connector.place_market_order(
                                            symbol="EURUSD",
                                            order_type=decision.split()[-1],  # Get last word (BUY/SELL)
                                            volume=position_size
                                        )
                                        if result.get('success'):
                                            # Add to active trades
                                            trade_info = {
                                                'symbol': 'EURUSD',
                                                'type': decision.split()[-1],
                                                'volume': position_size,
                                                'price': current_price,
                                                'sl': stop_loss_price,
                                                'tp': take_profit_price
                                            }
                                            trade_manager.add_trade({**result, **trade_info})
                                            st.success(f"✅ Order placed successfully! Ticket: {result.get('order')}")
                                        else:
                                            st.error(f"❌ Order failed: {result.get('error', 'Unknown error')}")
                                    except Exception as e:
                                        st.error(f"❌ Error placing order: {e}")
                            
                            with col2:
                                st.write("**Order Details:**")
                                st.write(f"Type: {decision}")
                                st.write(f"Volume: {position_size:.2f} lots")
                                st.write(f"Entry: {current_price:.5f}")
                                st.write(f"SL: {stop_loss_price:.5f}")
                                st.write(f"TP: {take_profit_price:.5f}")
                                st.write(f"SL Distance: {abs(current_price - stop_loss_price) / 0.00001:.0f} pips")
                                st.write(f"TP Distance: {abs(take_profit_price - current_price) / 0.00001:.0f} pips")
                    
                    # Signal reasons
                    st.markdown("**📋 Signal Reasons:**")
                    if reasons:
                        for reason in reasons:
                            st.markdown(f"• {reason}")
                    else:
                        st.markdown("• Neutral market conditions")
                    
                    # Technical indicators
                    st.markdown("---")
                    st.markdown("### 📊 Technical Indicators")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("RSI(14)", f"{latest_rsi:.1f}", 
                                 delta="Oversold" if latest_rsi < 30 else "Overbought" if latest_rsi > 70 else "Neutral")
                    with col2:
                        st.metric("SMA(20)", f"{latest_sma:.5f}")
                    with col3:
                        st.metric("EMA(20)", f"{latest_ema:.5f}")
                    with col4:
                        trend = "Uptrend 📈" if latest_ema > latest_sma else "Downtrend 📉"
                        st.metric("Trend", trend)
                    
                    # Market information
                    st.markdown("---")
                    st.markdown("### 📈 Market Information")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Symbol", "EURUSD")
                    with col2:
                        st.metric("Current Price", f"{current_price:.5f}")
                    with col3:
                        st.metric("Data Points", f"{len(historical_data)}")
                    with col4:
                        st.metric("Timeframe", st.session_state.selected_timeframe)
                    
                else:
                    st.error("❌ Failed to fetch historical data. Please ensure MT5 is running and has market data.")
                    
        except Exception as e:
            st.error(f"❌ Error generating signal: {e}")
            st.info("💡 Tip: Make sure MT5 is running and you have an active internet connection.")
    
    # Chatbot section
    render_chatbot()


# ============ MAIN APPLICATION ============
def main():
    """Main dashboard application"""
    initialize_session_state()
    
    if not st.session_state.mt5_connected:
        # Show login page
        render_login_page()
    else:
        # Show main dashboard with sidebar
        render_sidebar_logged_in()
        render_main_dashboard()


if __name__ == "__main__":
    main()
