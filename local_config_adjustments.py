"""
LOCAL CONFIG ADJUSTMENTS
Adjust settings for local trading (vs VPS)
"""

import os
import logging

logger = logging.getLogger(__name__)

def apply_local_adjustments():
    """Apply local-specific configuration adjustments"""
    
    # Create local config overrides
    local_settings = {
        # Reduce logging frequency for local console
        'ENABLE_ADVANCED_LOGGING': False,
        'LOG_PARTIAL_TP_EVENTS': False,
        'LOG_BREAK_EVEN_MOVES': False,
        'LOG_TRAILING_UPDATES': False,
        'LOG_EXIT_REASONS': False,
        
        # Conservative settings for local testing
        'MAX_TRADES_PER_DAY': 10,  # Reduced from 20
        'MAX_CONCURRENT_TRADES': 5,  # Reduced from 30
        
        # Smaller lot sizes for local testing
        'DEFAULT_LOT_SIZE': 0.01,
        'MAX_LOT_SIZE': 0.1,
        
        # Wider spreads for local brokers
        'MAX_SPREAD_PIPS': 10.0,  # Increased from 5.0
        
        # Shorter trading hours for local testing
        'ENABLE_SESSION_FILTER': True,
        'ASIAN_SESSION_START': 1,   # 1:00 UTC
        'ASIAN_SESSION_END': 7,     # 7:00 UTC
        'LONDON_SESSION_START': 8,  # 8:00 UTC
        'LONDON_SESSION_END': 16,   # 16:00 UTC
        'NEW_YORK_SESSION_START': 13, # 13:00 UTC
        'NEW_YORK_SESSION_END': 21,   # 21:00 UTC
        
        # Safety settings
        'ENABLE_NEWS_FILTER': True,
        'ENABLE_CORRELATION_CONTROL': True,
        'ENABLE_GLOBAL_RISK_CONTROL': True,
        
        # Telegram settings (optional)
        'ENABLE_TELEGRAM_NOTIFICATIONS': os.getenv('ENABLE_TELEGRAM', 'False').lower() == 'true',
    }
    
    # Save to environment variables
    for key, value in local_settings.items():
        os.environ[key] = str(value)
    
    logger.info("Local configuration adjustments applied:")
    for key, value in local_settings.items():
        logger.info(f"  {key}: {value}")
    
    return local_settings

def create_local_env_file():
    """Create a .env file for local settings"""
    env_content = """# NYX AI LOCAL CONFIGURATION
# Adjust these settings for local trading

# Trading Settings
MAX_TRADES_PER_DAY=10
MAX_CONCURRENT_TRADES=5
DEFAULT_LOT_SIZE=0.01
MAX_LOT_SIZE=0.1
MAX_SPREAD_PIPS=10.0

# Session Filter (UTC hours)
ASIAN_SESSION_START=1
ASIAN_SESSION_END=7
LONDON_SESSION_START=8
LONDON_SESSION_END=16
NEW_YORK_SESSION_START=13
NEW_YORK_SESSION_END=21

# Safety Features
ENABLE_SESSION_FILTER=True
ENABLE_NEWS_FILTER=True
ENABLE_CORRELATION_CONTROL=True
ENABLE_GLOBAL_RISK_CONTROL=True

# Logging (reduce console spam)
ENABLE_ADVANCED_LOGGING=False
LOG_PARTIAL_TP_EVENTS=False
LOG_BREAK_EVEN_MOVES=False
LOG_TRAILING_UPDATES=False
LOG_EXIT_REASONS=False

# Telegram (optional - set to True if you want notifications)
ENABLE_TELEGRAM_NOTIFICATIONS=False
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    logger.info("Created .env file with local settings")

if __name__ == "__main__":
    apply_local_adjustments()
    create_local_env_file()
    print("Local configuration applied successfully!")
