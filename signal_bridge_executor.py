"""
SIGNAL BRIDGE EXECUTOR
Provides MT5-compatible interface using JSON signal bridge
for seamless migration from MT5 Python dependency
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from signal_bridge import send_signal, get_signal_status, signal_bridge
from config import *

logger = logging.getLogger(__name__)

class SignalBridgeResult:
    """Mock result object that mimics MT5 trade result"""
    def __init__(self, success: bool, signal_id: str = None, error: str = None):
        self.retcode = 1000 if success else -1
        self.comment = "Signal exported successfully" if success else (error or "Signal export failed")
        self.order = signal_id or f"signal_{int(time.time())}"
        self.success = success

def place_trade(symbol: str, signal: str, lot: float, sl: float, tp: float, 
                magic: int = 123456, confidence: float = 0.0, score: float = 0.0,
                entry_price: Optional[float] = None) -> Optional[SignalBridgeResult]:
    """
    Execute trade by sending signal via JSON bridge
    
    Returns:
        SignalBridgeResult: Mock result object compatible with MT5 interface
    """
    try:
        logger.info(f"📤 Exporting trade signal to MT5 via bridge: {symbol} {signal}")
        
        # Validate inputs
        if not symbol or not signal or lot <= 0:
            logger.error("Invalid trade parameters")
            return SignalBridgeResult(False, error="Invalid parameters")
        
        # Send signal via bridge
        success = send_signal(
            symbol=symbol,
            action=signal,
            lot=lot,
            sl=sl,
            tp=tp,
            confidence=confidence,
            score=score,
            entry_price=entry_price
        )
        
        if success:
            signal_id = f"{symbol}_{signal}_{int(time.time())}"
            logger.info(f"✅ Signal exported successfully: {signal_id}")
            return SignalBridgeResult(True, signal_id=signal_id)
        else:
            logger.error("❌ Signal export failed")
            return SignalBridgeResult(False, error="Signal export failed")
            
    except Exception as e:
        logger.error(f"❌ Signal bridge error: {e}")
        return SignalBridgeResult(False, error=str(e))

def check_safety_filters(bot_instance, symbol: str, lot_size: float, signal: str, 
                         spread_pips: float, confidence: float, timeframe: str) -> tuple:
    """
    Check safety filters (adapted for signal bridge)
    
    Returns:
        tuple: (passed: bool, message: str)
    """
    try:
        # Basic safety checks that don't require MT5
        if lot_size > 0.5:
            return False, f"Lot size too large: {lot_size}"
        
        if spread_pips > 10.0:  # Conservative for signal bridge
            return False, f"Spread too high: {spread_pips:.1f} pips"
        
        if confidence < 50.0:
            return False, f"Confidence too low: {confidence:.1f}%"
        
        # Weekend check
        now = datetime.now()
        if now.weekday() >= 5:  # Saturday or Sunday
            return False, "Weekend - no trading"
        
        logger.info(f"✅ Safety checks passed for {symbol}")
        return True, "Safety checks passed"
        
    except Exception as e:
        logger.error(f"Safety check error: {e}")
        return False, f"Safety check error: {e}"

def get_account_info() -> Optional[Dict[str, Any]]:
    """
    Get mock account info for signal bridge compatibility
    
    Returns:
        dict: Mock account information
    """
    try:
        # Return mock account data since we can't connect to MT5 directly
        account_info = {
            'login': 123456789,
            'server': 'Signal Bridge Server',
            'balance': 10000.0,
            'equity': 10000.0,
            'margin': 0.0,
            'free_margin': 10000.0,
            'margin_level': 0.0,
            'leverage': 100,
            'currency': 'USD'
        }
        
        logger.info("Using mock account info for signal bridge")
        return account_info
        
    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        return None

def check_open_positions() -> List[Dict[str, Any]]:
    """
    Check open positions (mock for signal bridge)
    
    Returns:
        list: Empty list since we can't access MT5 directly
    """
    # In signal bridge mode, we can't directly check positions
    # This would be handled by the MT5 EA reporting back
    logger.info("Position checking not available in signal bridge mode")
    return []

def close_old_positions(max_age_minutes: int = 30) -> int:
    """
    Close old positions (mock for signal bridge)
    
    Returns:
        int: 0 since we can't close positions directly
    """
    logger.info("Position closing not available in signal bridge mode")
    return 0

def get_symbol_info(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get symbol information (mock for signal bridge)
    
    Returns:
        dict: Mock symbol information
    """
    try:
        # Return mock symbol data
        symbol_info = {
            'symbol': symbol,
            'point': 0.00001 if not symbol.startswith('JPY') else 0.001,
            'digits': 5 if not symbol.startswith('JPY') else 3,
            'spread': 10,  # points
            'trade_mode': 1,  # Full trading
            'volume_min': 0.01,
            'volume_max': 100.0,
            'volume_step': 0.01,
            'swap_long': 0.0,
            'swap_short': 0.0,
            'margin_required': 100.0
        }
        
        logger.info(f"Using mock symbol info for {symbol}")
        return symbol_info
        
    except Exception as e:
        logger.error(f"Error getting symbol info: {e}")
        return None

def get_tick_data(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get tick data (mock for signal bridge)
    
    Returns:
        dict: Mock tick data
    """
    try:
        # Return mock tick data - in production this would come from price feed
        import random
        
        base_price = 1.1000 if symbol == "EURUSD" else 1.2000
        tick_data = {
            'symbol': symbol,
            'bid': base_price - random.uniform(0, 0.001),
            'ask': base_price + random.uniform(0, 0.001),
            'last': base_price,
            'volume': random.randint(100, 1000),
            'time': datetime.utcnow().timestamp()
        }
        
        return tick_data
        
    except Exception as e:
        logger.error(f"Error getting tick data: {e}")
        return None

def close_position(position_ticket: int) -> Optional[SignalBridgeResult]:
    """
    Close position (mock for signal bridge)
    
    Returns:
        SignalBridgeResult: Mock result
    """
    logger.info(f"Position closing not available in signal bridge mode for ticket {position_ticket}")
    return SignalBridgeResult(False, error="Position closing not available in bridge mode")

# Additional compatibility functions
def initialize_mt5() -> bool:
    """Mock MT5 initialization"""
    logger.info("Signal bridge mode - no MT5 initialization needed")
    return True

def shutdown_mt5():
    """Mock MT5 shutdown"""
    logger.info("Signal bridge mode - no MT5 shutdown needed")

def get_positions() -> List[Dict[str, Any]]:
    """Get open positions (mock)"""
    return []

def get_orders() -> List[Dict[str, Any]]:
    """Get open orders (mock)"""
    return []

# Constants for compatibility
TRADE_RETCODE_DONE = 1000
TRADE_RETCODE_INVALID = -1
ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
TRADE_ACTION_DEAL = 1
ORDER_FILLING_FOK = 0
ORDER_FILLING_IOC = 1
ORDER_FILLING_RETURN = 2
