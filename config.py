"""
NYX AI PROFESSIONAL CONFIGURATION
Centralized settings for institutional-grade trading
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ==========================================
# PARTIAL TAKE PROFIT SETTINGS
# ==========================================
ENABLE_PARTIAL_TP = True
PARTIAL_TP_RATIO = 0.5  # Close 50% at 50% TP
PARTIAL_TP_TRIGGER = 0.5  # Trigger at 50% of TP distance

# ==========================================
# BREAK-EVEN SETTINGS
# ==========================================
ENABLE_BREAK_EVEN = True
BREAK_EVEN_TRIGGER_R = 1.0  # Move SL to BE at +1R
BREAK_EVEN_BUFFER_PIPS = 1.0  # Buffer pips above/below entry

# ==========================================
# TRAILING STOP SETTINGS
# ==========================================
ENABLE_TRAILING = True
TRAILING_ATR_MULTIPLIER = 1.2  # ATR × 1.2 trailing distance
TRAILING_UPDATE_FREQUENCY = "candle_close"  # Update on candle close
TRAILING_DISABLE_NEAR_TP = 0.2  # Disable within 20% of TP

# ==========================================
# SESSION FILTER SETTINGS
# ==========================================
ENABLE_SESSION_FILTER = True  # 🔧 RE-ENABLED FOR VPS PRODUCTION
LONDON_SESSION_START = 8  # 08:00 UTC
LONDON_SESSION_END = 17  # 17:00 UTC
NEW_YORK_SESSION_START = 13  # 13:00 UTC
NEW_YORK_SESSION_END = 22  # 22:00 UTC
ASIAN_SESSION_START = 0  # 00:00 UTC
ASIAN_SESSION_END = 8  # 07:59 UTC (extended to cover gap)

# ==========================================
# NEWS VOLATILITY FILTER
# ==========================================
ENABLE_NEWS_FILTER = True
VOLATILITY_SPIKE_MULTIPLIER = 2.0  # Candle range > 2× ATR = skip
SPREAD_EXPANSION_MULTIPLIER = 1.5  # Spread > 1.5× average = skip

# ==========================================
# CORRELATION & EXPOSURE CONTROL
# ==========================================
ENABLE_CORRELATION_CONTROL = True
MAX_USD_DIRECTION_TRADES = 3  # Increased from 2 to 3
MAX_JPY_RELATED_TRADES = 3  # Increased from 2 to 3
CORRELATED_PAIRS = {
    'USD_BASE': ['EURUSD', 'GBPUSD', 'AUDUSD', 'NZDUSD', 'USDCAD'],
    'USD_QUOTE': ['USDJPY', 'USDCHF'],
    'JPY_RELATED': ['USDJPY', 'EURJPY', 'GBPJPY', 'CHFJPY'],
    'EUR_RELATED': ['EURUSD', 'EURGBP', 'EURJPY', 'EURCHF'],
    'GBP_RELATED': ['GBPUSD', 'EURGBP', 'GBPJPY'],
}

# ==========================================
# MULTI-TIMEFRAME CONFIRMATION
# ==========================================
ENABLE_MTF_CONFIRMATION = True
MTF_ALIGNMENT_RULES = {
    'M15_M30_ALIGN': True,  # M15 + M30 must agree
    'M30_H1_ALIGN': True,   # M30 + H1 must agree
    'H1_OVERRIDE': 90,      # H1 overrides if confidence > 90%
}
MTF_MIN_CONFIDENCE = 70.0  # Minimum confidence for MTF signals

# ==========================================
# TRADE PRIORITY ENGINE
# ==========================================
ENABLE_PRIORITY_ENGINE = True
MAX_TRADES_PER_CYCLE = 2  # Only take top X trades per cycle
PRIORITY_FACTORS = {
    'confidence_weight': 0.5,    # 50% weight to confidence
    'trend_weight': 0.3,         # 30% weight to trend strength
    'volatility_weight': 0.2,     # 20% weight to volatility quality
}

# ==========================================
# GLOBAL RISK MANAGEMENT
# ==========================================
MAX_GLOBAL_RISK = 0.05  # 5% max total risk
MAX_GLOBAL_EXPOSURE = 0.10  # 10% max total exposure
RISK_CALCULATION_METHOD = "sl_based"  # sl_based / notional_based

# ==========================================
# TRADE LIFECYCLE MANAGEMENT
# ==========================================
ENABLE_LIFECYCLE_MANAGER = True
MAX_TRADE_AGE_MINUTES = 45  # Force close after 45 min if no progress
MAX_LOSS_MULTIPLIER = 1.5  # Force close if loss > 1.5× planned risk
MIN_PROGRESS_PERCENTAGE = 0.3  # Minimum 30% progress toward TP

# ==========================================
# ADVANCED LOGGING
# ==========================================
ENABLE_ADVANCED_LOGGING = True
LOG_ENTRY_REASONS = True
LOG_PARTIAL_TP_EVENTS = True
LOG_BREAK_EVEN_MOVES = True
LOG_TRAILING_UPDATES = True
LOG_EXIT_REASONS = True

# ==========================================
# FAILSAFE EXECUTION
# ==========================================
ENABLE_EXECUTION_RETRIES = True
MAX_EXECUTION_RETRIES = 2
EXECUTION_RETRY_DELAY = 1.0  # Seconds between retries
VALIDATE_SL_TP_BEFORE_SEND = True
PREVENT_DUPLICATE_ORDERS = True

# ==========================================
# LEGACY SETTINGS (Keep existing)
# ==========================================
MAX_OPEN_TRADES = 7  # PART 8: Increased from 5 to 7
MAX_LOT_SIZE = 0.5  # Maximum lot size
MAX_SPREAD_PIPS = 5.0  # Maximum allowed spread
TRADING_HOURS_START = 6  # 06:00 UTC
TRADING_HOURS_END = 20  # 20:00 UTC

# ==========================================
# SYMBOL GROUPS FOR CORRELATION
# ==========================================
SYMBOL_GROUPS = {
    'MAJORS': ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD'],
    'COMMODITIES': ['AUDUSD', 'NZDUSD', 'USDCAD'],
    'CROSSES': ['EURGBP', 'EURJPY', 'GBPJPY', 'EURCHF'],
    'SAFE_HAVENS': ['USDJPY', 'CHFJPY', 'USDCHF'],
}

# ==========================================
# ATR SETTINGS FOR VOLATILITY
# ==========================================
ATR_PERIOD = 14
ATR_TIMEFRAME = 'H1'  # Use H1 ATR for all calculations

# ==========================================
# ENVIRONMENT VARIABLES
# ==========================================
class Config:
    """Configuration class for the Forex Bot"""
    
    # Trading Settings
    TRADING_MODE = os.getenv('TRADING_MODE', 'paper')  # paper or live
    RISK_PERCENTAGE = float(os.getenv('RISK_PERCENTAGE', 2.0))
    MAX_POSITIONS = int(os.getenv('MAX_POSITIONS', 5))
    
    # API Settings
    API_KEY = os.getenv('API_KEY')
    API_SECRET = os.getenv('API_SECRET')
    
    # Notification Settings
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
    
    # Technical Analysis Settings
    RSI_PERIOD = 14
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    MA_FAST_PERIOD = 20
    MA_SLOW_PERIOD = 50
    STOP_LOSS_PIPS = 50
    TAKE_PROFIT_PIPS = 100
    
    # Aliases for backward compatibility
    SL_PIPS = 50
    TP_PIPS = 100
    
    # Currency Pairs to Monitor
    CURRENCY_PAIRS = [
        'EUR/USD',
        'GBP/USD', 
        'USD/JPY',
        'AUD/USD',
        'USD/CAD',
        'NZD/USD',
        'EUR/GBP',
        'EUR/JPY'
    ]
    
    # Timeframes
    TIMEFRAMES = ['1m', '5m', '15m', '1h', '4h', '1d']
    
    @classmethod
    def validate_config(cls):
        """Validate configuration settings"""
        errors = []
        
        if cls.RISK_PERCENTAGE <= 0 or cls.RISK_PERCENTAGE > 10:
            errors.append("RISK_PERCENTAGE must be between 0 and 10")
            
        if cls.MAX_POSITIONS <= 0 or cls.MAX_POSITIONS > 20:
            errors.append("MAX_POSITIONS must be between 1 and 20")
            
        if cls.TRADING_MODE not in ['paper', 'live']:
            errors.append("TRADING_MODE must be 'paper' or 'live'")
            
        return errors
