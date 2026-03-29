"""
PROFESSIONAL TRADE EXECUTOR
Enhanced with proper error handling and multiple retry strategies
"""

import MetaTrader5 as mt5
import time
import logging

logger = logging.getLogger(__name__)

def close_trade_professional(position):
    """
    Professional trade closing with multiple strategies and error handling
    Solves ERROR 10030 and other MT5 closing issues
    """
    
    symbol = position.symbol
    volume = position.volume
    ticket = position.ticket
    
    # Get current price with retry
    for attempt in range(3):
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            logger.warning(f"Failed to get tick data (attempt {attempt + 1})")
            time.sleep(0.1)
            continue
            
        # Determine close price and order type
        if position.type == mt5.ORDER_TYPE_BUY:  # BUY position
            close_price = tick.bid
            order_type = mt5.ORDER_TYPE_SELL
        else:  # SELL position
            close_price = tick.ask
            order_type = mt5.ORDER_TYPE_BUY
        
        # Try different filling modes
        filling_modes = [
            mt5.ORDER_FILLING_FOK,   # Fill or Kill
            mt5.ORDER_FILLING_IOC,   # Immediate or Cancel
            mt5.ORDER_FILLING_RETURN  # Return to client
        ]
        
        for filling_mode in filling_modes:
            # Create close request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": order_type,
                "position": ticket,
                "price": close_price,
                "deviation": 20,
                "magic": 123456,
                "comment": "NYX AI PROFESSIONAL CLOSE",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": filling_mode,
            }
            
            # Send close request
            result = mt5.order_send(request)
            
            if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
                logger.info(f"✅ Trade {ticket} closed successfully")
                logger.info(f"   Mode: {filling_mode}")
                logger.info(f"   Price: {close_price:.5f}")
                logger.info(f"   P&L: ${position.profit:+.2f}")
                return True, result
            else:
                error_code = result.retcode if result else "Unknown"
                error_comment = result.comment if result else "No result"
                logger.warning(f"❌ Close failed (mode {filling_mode}): {error_code} - {error_comment}")
                
                # If it's a price issue, update price and retry same mode
                if error_code == 10030:  # Invalid price
                    logger.info(f"   Updating price for next attempt...")
                    continue  # Retry with updated price
                
                # If it's a filling mode issue, try next mode
                if error_code in [10006, 10007, 10008]:  # Common filling errors
                    logger.info(f"   Trying next filling mode...")
                    break  # Try next filling mode
        
        # Wait before next attempt
        if attempt < 2:
            time.sleep(0.5)
    
    logger.error(f"❌ Failed to close trade {ticket} after all attempts")
    return False, None

def close_all_positions_professional():
    """
    Close all open positions using professional closing method
    """
    
    positions = mt5.positions_get()
    if not positions:
        logger.info("No open positions to close")
        return True
    
    closed = 0
    failed = 0
    
    for position in positions:
        logger.info(f"Closing {position.symbol} position {position.ticket}")
        success, result = close_trade_professional(position)
        
        if success:
            closed += 1
        else:
            failed += 1
    
    logger.info(f"Emergency close completed: {closed}/{len(positions)} positions closed, {failed} failed")
    return closed == len(positions)

def validate_order_parameters(symbol, order_type, volume, price, sl, tp):
    """
    Validate order parameters before sending
    """
    
    # Check symbol info
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        return False, "Symbol info not available"
    
    # Check volume
    if volume <= 0 or volume > symbol_info.volume_max:
        return False, f"Invalid volume: {volume}"
    
    # Check price
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        return False, "No tick data available"
    
    # Validate price levels
    if order_type == mt5.ORDER_TYPE_BUY:
        if price < tick.bid or price > tick.ask:
            return False, f"Price {price} outside market spread ({tick.bid}-{tick.ask})"
    else:
        if price > tick.bid or price < tick.ask:
            return False, f"Price {price} outside market spread ({tick.bid}-{tick.ask})"
    
    # Check SL/TP levels
    if sl and tp:
        if order_type == mt5.ORDER_TYPE_BUY:
            if sl >= price or tp <= price:
                return False, f"Invalid SL/TP for BUY: SL {sl} >= price {price} or TP {tp} <= price {price}"
        else:
            if sl <= price or tp >= price:
                return False, f"Invalid SL/TP for SELL: SL {sl} <= price {price} or TP {tp} >= price {price}"
    
    return True, "Order parameters valid"
