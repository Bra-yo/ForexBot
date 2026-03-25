"""
Configuration settings for BrayoForexBot
"""

import os
from dotenv import load_dotenv

load_dotenv()

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
