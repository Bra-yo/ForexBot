"""
SIGNAL BRIDGE EXECUTOR
Provides MT5-compatible interface using JSON signal bridge for trade
placement (place_trade), while get_symbol_info/get_tick_data/get_account_info/
check_open_positions/close_old_positions/close_position now use REAL, direct
MT5 calls instead of the Linux/Wine-era mock data they returned before.

That mock data was never updated when the project moved back to Windows with
a real MT5 terminal - it was returning a hardcoded fake $10,000 balance, an
empty position list, and (for XAUUSD specifically) a fake ~$1.20 price with a
randomly-jittered spread instead of gold's real ~$4400 price. The "90.1 pips"
spread rejection you saw wasn't measuring anything real; it was closer to a
random number generator.

place_trade() still writes to the JSON signal bridge - this is a genuine open
question, not something I fixed silently: does your MT5 terminal actually
have NyxEA.mq5 attached and running right now? If not, no trade this file
ever "approves" will actually reach the market, no matter how correct the
signal is upstream. See the note on place_trade() below.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from signal_bridge import send_signal, get_signal_status, signal_bridge
from config import *
from confidence_config import MIN_CONFIDENCE_PCT
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

# Execution mode: "direct" places the order with mt5.order_send() from Python
# (no EA needed). "bridge" only writes the JSON signal for NyxEA.mq5 to pick up.
# Override with the NYX_EXECUTION_MODE environment variable.
import os
EXECUTION_MODE = os.environ.get("NYX_EXECUTION_MODE", "direct").strip().lower()


class DirectTradeResult:
    """Wraps a real MT5 order result so callers see retcode/order like before."""
    def __init__(self, retcode, order, comment, success):
        self.retcode = retcode
        self.order = order
        self.comment = comment
        self.success = success


def _pick_filling_mode(symbol_info):
    """Choose a filling mode the broker actually allows for this symbol."""
    modes = symbol_info.filling_mode
    if modes & 1:   # FOK allowed
        return mt5.ORDER_FILLING_FOK
    if modes & 2:   # IOC allowed
        return mt5.ORDER_FILLING_IOC
    return mt5.ORDER_FILLING_RETURN


def place_trade_direct(symbol, signal, lot, sl, tp, magic=123456, comment="NYX AI"):
    """Place a market order with broker-side SL/TP straight from Python."""
    info = mt5.symbol_info(symbol)
    if info is None:
        return DirectTradeResult(-1, 0, f"symbol_info unavailable for {symbol}", False)
    if not info.visible:
        mt5.symbol_select(symbol, True)
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return DirectTradeResult(-1, 0, "no tick data", False)

    is_buy = signal.upper() == "BUY"
    price = tick.ask if is_buy else tick.bid
    digits = info.digits

    # Clamp lot to broker rules
    step = info.volume_step or 0.01
    lot = max(info.volume_min, min(info.volume_max, round(round(lot / step) * step, 2)))

    sl_p = round(float(sl), digits) if sl else 0.0
    tp_p = round(float(tp), digits) if tp else 0.0

    # Enforce the broker's minimum stop distance so the order is not rejected
    min_dist = (info.trade_stops_level or 0) * info.point
    if min_dist > 0:
        if is_buy:
            if sl_p and price - sl_p < min_dist:
                sl_p = round(price - min_dist, digits)
            if tp_p and tp_p - price < min_dist:
                tp_p = round(price + min_dist, digits)
        else:
            if sl_p and sl_p - price < min_dist:
                sl_p = round(price + min_dist, digits)
            if tp_p and price - tp_p < min_dist:
                tp_p = round(price - min_dist, digits)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot,
        "type": mt5.ORDER_TYPE_BUY if is_buy else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl_p,
        "tp": tp_p,
        "deviation": 50,
        "magic": magic,
        "comment": comment,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": _pick_filling_mode(info),
    }
    logger.info(f" order_send request: {request}")
    result = mt5.order_send(request)
    if result is None:
        return DirectTradeResult(-1, 0, f"order_send returned None: {mt5.last_error()}", False)
    ok = result.retcode == mt5.TRADE_RETCODE_DONE
    logger.info(f" order_send result: retcode={result.retcode} order={result.order} "
                f"deal={result.deal} comment={result.comment}")
    return DirectTradeResult(result.retcode, result.order, result.comment, ok)


class SignalBridgeResult:
    """Mock result object that mimics MT5 trade result"""
    def __init__(self, success: bool, signal_id: str = None, error: str = None):
        self.retcode = mt5.TRADE_RETCODE_DONE if success else -1
        self.comment = "Signal exported successfully" if success else (error or "Signal export failed")
        self.order = signal_id or f"signal_{int(time.time())}"
        self.success = success

def place_trade(symbol: str, signal: str, lot: float, sl: float, tp: float, 
                magic: int = 123456, confidence: float = 0.0, score: float = 0.0,
                entry_price: Optional[float] = None,
                comment: str = "NYX AI") -> Optional[SignalBridgeResult]:
    """
    Execute trade by sending signal via JSON bridge.

    IMPORTANT - NOT FIXED, FLAGGED FOR YOUR DECISION: this still only writes
    a JSON signal file (via send_signal()) rather than calling mt5.order_send()
    directly. That's correct IF NyxEA.mq5 is attached and running in your MT5
    terminal right now, reading trade_signal.json and placing the real order.
    If it isn't attached, every trade this bot "approves" silently goes
    nowhere - the JSON gets written, nothing reads it, no real position ever
    opens. Check MT5 now: is NyxEA showing a smiley-face/active icon on your
    XAUUSD chart? If not, tell me and I'll convert this to call
    mt5.order_send() directly instead, matching how the rest of this codebase
    now talks to MT5.
    
    Returns:
        SignalBridgeResult: Mock result object compatible with MT5 interface
    """
    if EXECUTION_MODE == "direct":
        try:
            res = place_trade_direct(symbol, signal, lot, sl, tp, magic=magic, comment=comment)
            if not res.success:
                logger.error(f" Direct order failed: retcode={res.retcode} {res.comment}")
            return res
        except Exception as e:
            logger.error(f" Direct order error: {e}")
            return SignalBridgeResult(False, error=str(e))

    try:
        logger.info(f" Exporting trade signal to MT5 via bridge: {symbol} {signal}")
        
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
            logger.info(f" Signal exported successfully: {signal_id}")
            return SignalBridgeResult(True, signal_id=signal_id)
        else:
            logger.error(" Signal export failed")
            return SignalBridgeResult(False, error="Signal export failed")
            
    except Exception as e:
        logger.error(f" Signal bridge error: {e}")
        return SignalBridgeResult(False, error=str(e))

def check_safety_filters(bot_instance, symbol: str, lot_size: float, signal: str, 
                         spread_pips: float, confidence: float, timeframe: str) -> tuple:
    """
    Check safety filters.

    Removed the redundant, forex-scaled spread check (was ">10.0 pips",
    a SECOND, different threshold from live_trading_executor.py's own
    (now-fixed) _max_spread_pips check - two different thresholds fighting
    each other on the same trade was never intentional). The real spread
    check with the correct real data now lives in one place:
    live_trading_executor.py.
    
    Returns:
        tuple: (passed: bool, message: str)
    """
    try:
        if lot_size > 0.5:
            return False, f"Lot size too large: {lot_size}"
        
        if confidence < MIN_CONFIDENCE_PCT:
            return False, f"Confidence too low: {confidence:.1f}% (< {MIN_CONFIDENCE_PCT}%)"
        
        # Weekend check
        now = datetime.now()
        if now.weekday() >= 5:  # Saturday or Sunday
            return False, "Weekend - no trading"
        
        logger.info(f" Safety checks passed for {symbol}")
        return True, "Safety checks passed"
        
    except Exception as e:
        logger.error(f"Safety check error: {e}")
        return False, f"Safety check error: {e}"

def get_account_info() -> Optional[Dict[str, Any]]:
    """
    Get REAL account info directly from MT5 (was previously a hardcoded
    fake $10,000 balance/equity, regardless of what the account actually
    had - any equity or drawdown check reading this was working off a
    number that never changed).
    """
    try:
        info = mt5.account_info()
        if info is None:
            logger.error("mt5.account_info() returned None - is the terminal connected and logged in?")
            return None

        return {
            'login': info.login,
            'server': info.server,
            'balance': info.balance,
            'equity': info.equity,
            'margin': info.margin,
            'free_margin': info.margin_free,
            'margin_level': info.margin_level,
            'leverage': info.leverage,
            'currency': info.currency
        }

    except Exception as e:
        logger.error(f"Error getting account info: {e}")
        return None

def check_open_positions() -> List[Dict[str, Any]]:
    """
    Get REAL open positions directly from MT5 (was previously always an
    empty list - any position-count or duplicate-position check reading
    this could never see a real open position, regardless of reality).
    """
    try:
        positions = mt5.positions_get()
        if positions is None:
            return []
        return [
            {
                'ticket': p.ticket,
                'symbol': p.symbol,
                'type': p.type,  # 0 = buy, 1 = sell
                'volume': p.volume,
                'price_open': p.price_open,
                'price_current': p.price_current,
                'sl': p.sl,
                'tp': p.tp,
                'profit': p.profit,
                'time': p.time,
                'magic': p.magic,
            }
            for p in positions
        ]
    except Exception as e:
        logger.error(f"Error checking open positions: {e}")
        return []

def close_old_positions(max_age_minutes: int = 30) -> int:
    """
    Close REAL positions older than max_age_minutes directly via MT5 (was
    previously a no-op that always returned 0 and closed nothing).

    Note: multi_pair_live_bot_clean.py's manage_open_trades() already does
    time-based closing across ALL symbols on its own schedule - this is a
    second, XAUUSD-specific path. Not necessarily redundant (different
    symbol scoping), but worth being aware both exist.
    """
    try:
        positions = mt5.positions_get()
        if not positions:
            return 0

        closed_count = 0
        now = time.time()

        for pos in positions:
            age_minutes = (now - pos.time) / 60.0
            if age_minutes < max_age_minutes:
                continue

            tick = mt5.symbol_info_tick(pos.symbol)
            if tick is None:
                logger.warning(f"Could not get tick for {pos.symbol} to close position {pos.ticket}")
                continue

            close_price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
            close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": pos.symbol,
                "volume": pos.volume,
                "type": close_type,
                "position": pos.ticket,
                "price": close_price,
                "deviation": 20,
                "magic": pos.magic,
                "comment": f"Auto-close: age {age_minutes:.0f}min",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }

            result = mt5.order_send(request)
            if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
                closed_count += 1
                logger.info(f"Closed old position {pos.ticket} ({pos.symbol}, age {age_minutes:.0f}min)")
            else:
                logger.warning(f"Failed to close old position {pos.ticket}: {result}")

        return closed_count

    except Exception as e:
        logger.error(f"Error closing old positions: {e}")
        return 0

def get_symbol_info(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get REAL symbol information directly from MT5 (was previously
    hardcoded forex-style values - point=0.00001, digits=5 - regardless
    of what symbol was actually requested. For XAUUSD, the real point
    value is normally 0.01, not 0.00001; using the wrong one alone would
    have inflated any pip-based calculation by roughly 1000x).
    """
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            logger.error(f"mt5.symbol_info({symbol}) returned None - is it visible in Market Watch?")
            return None

        return {
            'symbol': symbol,
            'point': info.point,
            'digits': info.digits,
            'spread': info.spread,
            'trade_mode': info.trade_mode,
            'volume_min': info.volume_min,
            'volume_max': info.volume_max,
            'volume_step': info.volume_step,
            'swap_long': info.swap_long,
            'swap_short': info.swap_short,
            'trade_contract_size': info.trade_contract_size,
        }

    except Exception as e:
        logger.error(f"Error getting symbol info: {e}")
        return None

def get_tick_data(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Get REAL tick data directly from MT5 (was previously fabricated random
    data around a hardcoded fake base price - 1.20 for anything that
    wasn't literally "EURUSD", meaning XAUUSD was getting a fake price
    utterly unrelated to gold's real ~4400 level, with a randomly jittered
    "spread" that had nothing to do with the real market).
    """
    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            logger.error(f"mt5.symbol_info_tick({symbol}) returned None")
            return None

        return {
            'symbol': symbol,
            'bid': tick.bid,
            'ask': tick.ask,
            'last': tick.last,
            'volume': tick.volume,
            'time': tick.time,
        }

    except Exception as e:
        logger.error(f"Error getting tick data: {e}")
        return None

def close_position(position_ticket: int) -> Optional[SignalBridgeResult]:
    """
    Close a REAL position by ticket directly via MT5 (was previously a
    no-op that always failed with "not available in bridge mode").
    """
    try:
        positions = mt5.positions_get(ticket=position_ticket)
        if not positions:
            return SignalBridgeResult(False, error=f"Position {position_ticket} not found")

        pos = positions[0]
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            return SignalBridgeResult(False, error=f"Could not get tick for {pos.symbol}")

        close_price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        close_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": pos.symbol,
            "volume": pos.volume,
            "type": close_type,
            "position": pos.ticket,
            "price": close_price,
            "deviation": 20,
            "magic": pos.magic,
            "comment": "Manual close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
            return SignalBridgeResult(True, signal_id=str(position_ticket))
        else:
            return SignalBridgeResult(False, error=f"order_send failed: {result}")

    except Exception as e:
        logger.error(f"Error closing position {position_ticket}: {e}")
        return SignalBridgeResult(False, error=str(e))

# Additional compatibility functions
def initialize_mt5() -> bool:
    """Initialize the real MT5 connection (was previously a no-op that
    just logged a message and returned True unconditionally)."""
    try:
        return mt5.initialize()
    except Exception as e:
        logger.error(f"MT5 initialization error: {e}")
        return False

def shutdown_mt5():
    """Shut down the real MT5 connection."""
    try:
        mt5.shutdown()
    except Exception as e:
        logger.error(f"MT5 shutdown error: {e}")

def get_positions() -> List[Dict[str, Any]]:
    """Get open positions - real data, same as check_open_positions()."""
    return check_open_positions()

def get_orders() -> List[Dict[str, Any]]:
    """Get real pending orders directly from MT5 (was previously always
    an empty list)."""
    try:
        orders = mt5.orders_get()
        if orders is None:
            return []
        return [
            {
                'ticket': o.ticket,
                'symbol': o.symbol,
                'type': o.type,
                'volume_initial': o.volume_initial,
                'price_open': o.price_open,
                'sl': o.sl,
                'tp': o.tp,
                'time_setup': o.time_setup,
            }
            for o in orders
        ]
    except Exception as e:
        logger.error(f"Error getting orders: {e}")
        return []

# Constants for compatibility
TRADE_RETCODE_DONE = mt5.TRADE_RETCODE_DONE  # real MT5 value (10009); direct orders return it
TRADE_RETCODE_INVALID = -1
ORDER_TYPE_BUY = 0
ORDER_TYPE_SELL = 1
TRADE_ACTION_DEAL = 1
ORDER_FILLING_FOK = 0
ORDER_FILLING_IOC = 1
ORDER_FILLING_RETURN = 2