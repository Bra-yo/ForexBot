import MetaTrader5 as mt5
import time
from datetime import datetime
from config import *

def place_trade(symbol, signal, lot, sl, tp, magic=123456):
    """Execute real trade with MT5"""
    try:
        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            print(f"Failed to get tick data for {symbol}")
            return None
        
        price = tick.ask if signal == "BUY" else tick.bid
        order_type = mt5.ORDER_TYPE_BUY if signal == "BUY" else mt5.ORDER_TYPE_SELL
        
        # Get symbol info for filling mode
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            print(f"Failed to get symbol info for {symbol}")
            return None
        
        # Try different filling modes in order of preference
        filling_modes = [
            mt5.ORDER_FILLING_FOK,
            mt5.ORDER_FILLING_IOC,
            mt5.ORDER_FILLING_RETURN,
            0  # Default mode
        ]
        
        print(f"Trade Request Debug:")
        print(f"   Symbol: {symbol}")
        print(f"   Volume: {lot}")
        print(f"   Price: {price:.5f}")
        
        # Try each filling mode
        for i, filling_mode in enumerate(filling_modes):
            print(f"Trying filling mode {i+1}/{len(filling_modes)}: {filling_mode}")
            
            # Prepare trade request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": lot,
                "type": order_type,
                "price": price,
                "sl": sl,
                "tp": tp,
                "deviation": 20,
                "magic": magic,
                "comment": "Nyx AI Trading Bot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                print(f"✅ Trade Executed: {signal} {lot} lots at {price:.5f}")
                print(f"   Order ID: {result.order}")
                print(f"   SL: {sl:.5f}, TP: {tp:.5f}")
                print(f"   Filling Mode Used: {filling_mode}")
                return result
            else:
                print(f"   Failed with mode {filling_mode}: {result.retcode} - {result.comment}")
                continue
        
        # All filling modes failed
        print(f"All filling modes failed for {symbol}")
        return None
            
    except Exception as e:
        print(f"Trade execution error: {e}")
        return None

def check_safety_filters(self, symbol, lot, signal, spread_pips, confidence=None, timeframe=None):
    """
    Applies various safety filters before allowing a trade.
    Returns True if all checks pass, False otherwise.
    """
    
    # 🛑 1. Spread Check
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print("Failed to get tick data")
        return False, "Failed to get tick data"
    
    # CRITICAL FIX 2: Fix spread calculation - remove incorrect multiplication
    spread_points = (tick.ask - tick.bid) / mt5.symbol_info(symbol).point
    spread_pips = spread_points # CRITICAL: Don't multiply by 10!
    
    print(f"{symbol} Spread Debug:")
    print(f"   Ask: {tick.ask:.5f}")
    print(f"   Bid: {tick.bid:.5f}")
    print(f"   Spread Points: {spread_points:.5f}")
    print(f"   Spread Pips: {spread_pips:.1f}")
    
    if spread_pips > 5.0:  # 5.0 pips max
        print(f"Spread too high ({spread_pips:.1f} pips) — skipping trade")
        return False, f"Spread too high ({spread_pips:.1f} pips)"
    
    # 🛑 2. Position Stacking Prevention (NEW!)
    positions = mt5.positions_get()
    if len(positions) >= MAX_OPEN_TRADES:
        return False, f"Max trades reached ({len(positions)} >= {MAX_OPEN_TRADES})"
    
    # 🛑 3. Lot Size Cap
    lot = min(lot, MAX_LOT_SIZE)
    print(f"📊 Lot size capped at: {lot}")
    
    # 🛑 4. Market Hours Check
    current_time = datetime.now()
    hour = current_time.hour
    
    if not (TRADING_HOURS_START <= hour < TRADING_HOURS_END):
        return False, f"Outside trading hours ({hour}:00 not in {TRADING_HOURS_START}-{TRADING_HOURS_END})"
    
    # 🛑 5. Weekend Protection
    if current_time.weekday() >= 5:  # Saturday or Sunday
        return False, "Weekend protection active"
    
    # 🛑 6. Position Stacking Prevention
    symbol_positions = [pos for pos in positions if pos.symbol == symbol]
    for pos in symbol_positions:
        pos_signal = "BUY" if pos.type == 0 else "SELL"
        if pos_signal == signal:
            return False, f"Position stacking prevented: {symbol} already has {pos_signal} position"
    
    # 🛑 7. Global Risk Control
    total_risk = 0.0
    account_info = mt5.account_info()
    if account_info:
        for pos in positions:
            if pos.profit < 0:  # Only count losing positions
                risk_distance = abs(pos.price_open - pos.sl)
                position_risk = risk_distance * pos.volume * 100000  # Approximate
                total_risk += position_risk
        
        risk_percentage = (total_risk / account_info.balance) * 100 if account_info.balance > 0 else 0
        if risk_percentage > MAX_GLOBAL_RISK * 100:
            return False, f"Global risk limit exceeded ({risk_percentage:.1f}% > {MAX_GLOBAL_RISK*100:.1f}%)"
    
    print(f"✅ All safety checks passed for {symbol} {signal}")
    return True, "All safety checks passed"

def get_account_info():
    """Get current account information"""
    account = mt5.account_info()
    if account:
        return {
            'balance': account.balance,
            'equity': account.equity,
            'margin': account.margin,
            'free_margin': account.margin_free,
            'profit': account.profit
        }
    return None

def check_open_positions(symbol="EURUSD"):
    """Get all open positions with age check"""
    positions = mt5.positions_get(symbol=symbol)
    
    if not positions:
        return []
    
    current_time = time.time()
    max_duration_seconds = 1800  # 30 minutes max
    
    for pos in positions:
        # Calculate position age in seconds
        pos_time = pos.time
        age_seconds = current_time - pos_time
        
        # Log position details with age
        profit = pos.profit
        age_minutes = age_seconds / 60
        
        print(f"Position {pos.ticket}: {pos.type} {pos.volume} lots")
        print(f"   Age: {age_minutes:.1f} minutes")
        print(f"   P&L: ${profit:+.2f}")
        print(f"   Entry: {pos.price_open:.5f}")
        print(f"   Current: {pos.price_current:.5f}")
        
        # Check if position is too old
        if age_seconds > max_duration_seconds:
            print(f"Position too old ({age_minutes:.1f} min > 30 min) - should be closed")
    
    return positions

def close_old_positions(symbol="EURUSD", max_minutes=30):
    """Close positions that are older than max_minutes"""
    positions = check_open_positions(symbol)
    current_time = time.time()
    max_duration_seconds = max_minutes * 60
    closed = 0
    
    for pos in positions:
        age_seconds = current_time - pos.time
        
        if age_seconds > max_duration_seconds:
            print(f"Closing old position {pos.ticket} (age: {age_seconds/60:.1f} min)")
            if close_position(pos):
                closed += 1
    
    if closed > 0:
        print(f"Closed {closed} old positions (older than {max_minutes} minutes)")
    
    return closed

def close_position(position):
    """Close a specific position"""
    try:
        if position.type == mt5.POSITION_TYPE_BUY:
            order_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(position.symbol).bid
        else:
            order_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(position.symbol).ask
        
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": order_type,
            "position": position.ticket,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": "Nyx AI Bot Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_RETURN,  # Most compatible filling mode
        }
        
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            print(f"Close failed: {result.retcode}")
            return False
        else:
            print(f"Position {position.ticket} closed")
            return True
            
    except Exception as e:
        print(f"Close position error: {e}")
        return False

def close_all_positions(symbol="EURUSD"):
    """Close all open positions"""
    positions = check_open_positions(symbol)
    closed = 0
    
    for position in positions:
        if close_position(position):
            closed += 1
    
    print(f"Closed {closed}/{len(positions)} positions")
    return closed
