"""
TRADE MANAGER - Professional Position Management
Handles partial TP, break-even, trailing stops, and trade lifecycle
"""

import time
import MetaTrader5 as mt5
from datetime import datetime
from config import *

class TradeManager:
    """Professional trade lifecycle management"""
    
    def __init__(self):
        self.active_trades = {}  # Track trade states
        self.partial_tp_executed = set()  # Track partial TP status
        self.break_even_moved = set()  # Track break-even status
        self.trailing_active = set()  # Track trailing status
        
    def register_trade(self, ticket, symbol, signal, entry_price, sl, tp, lot):
        """Register new trade for management"""
        self.active_trades[ticket] = {
            'symbol': symbol,
            'signal': signal,
            'entry': entry_price,
            'sl': sl,
            'tp': tp,
            'lot': lot,
            'entry_time': time.time(),
            'partial_tp_done': False,
            'break_even_done': False,
            'trailing_active': False,
            'original_sl': sl
        }
        
    def check_partial_tp(self, ticket, current_price):
        """Check and execute partial take profit"""
        if not ENABLE_PARTIAL_TP or ticket in self.partial_tp_executed:
            return False
            
        trade = self.active_trades.get(ticket)
        if not trade:
            return False
            
        entry = trade['entry']
        tp = trade['tp']
        signal = trade['signal']
        
        # Calculate 50% TP level
        if signal == "BUY":
            partial_tp_level = entry + (tp - entry) * 0.5
            reached = current_price >= partial_tp_level
        else:
            partial_tp_level = entry - (entry - tp) * 0.5
            reached = current_price <= partial_tp_level
            
        if reached:
            return self.execute_partial_close(ticket, 0.5)  # Close 50%
        return False
        
    def check_break_even(self, ticket, current_price, spread):
        """Check and move to break-even"""
        if not ENABLE_BREAK_EVEN or ticket in self.break_even_moved:
            return False
            
        trade = self.active_trades.get(ticket)
        if not trade:
            return False
            
        entry = trade['entry']
        sl = trade['sl']
        signal = trade['signal']
        risk_distance = abs(entry - sl)
        
        # Check if price reached +1R (profit equals risk)
        if signal == "BUY":
            reached_be = current_price >= entry + risk_distance
            new_sl = entry + spread * 2  # Small buffer above entry
        else:
            reached_be = current_price <= entry - risk_distance
            new_sl = entry - spread * 2  # Small buffer below entry
            
        if reached_be and new_sl > sl:  # Only improve SL
            return self.modify_stop_loss(ticket, new_sl)
        return False
        
    def check_trailing_stop(self, ticket, current_price, atr_value):
        """Check and update trailing stop"""
        if not ENABLE_TRAILING or ticket in self.trailing_active:
            return False
            
        trade = self.active_trades.get(ticket)
        if not trade:
            return False
            
        signal = trade['signal']
        current_sl = trade['sl']
        tp = trade['tp']
        
        # Calculate trailing distance
        trail_distance = atr_value * 1.2
        
        # Don't trail if too close to TP
        if signal == "BUY":
            distance_to_tp = tp - current_price
            if distance_to_tp < (tp - current_sl) * 0.2:  # Within 20% of TP
                return False
            new_sl = current_price - trail_distance
        else:
            distance_to_tp = current_price - tp
            if distance_to_tp < (current_sl - tp) * 0.2:
                return False
            new_sl = current_price + trail_distance
            
        # Only trail if it improves protection
        if new_sl > current_sl:
            return self.modify_stop_loss(ticket, new_sl)
        return False
        
    def execute_partial_close(self, ticket, close_ratio):
        """Execute partial position close"""
        try:
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return False
                
            position = position[0]
            close_volume = position.volume * close_ratio
            
            # Determine close type (opposite of position)
            close_type = mt5.ORDER_TYPE_SELL if position.type == 0 else mt5.ORDER_TYPE_BUY
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": close_volume,
                "type": close_type,
                "position": ticket,
                "price": mt5.symbol_info_tick(position.symbol).bid if position.type == 0 else mt5.symbol_info_tick(position.symbol).ask,
                "deviation": 20,
                "magic": 123456,
                "comment": "PARTIAL TP - Nyx AI",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                self.partial_tp_executed.add(ticket)
                print(f"✅ Partial TP executed: {close_ratio*100:.0f}% of position {ticket}")
                return True
            else:
                print(f"❌ Partial TP failed: {result.retcode}")
                return False
                
        except Exception as e:
            print(f"❌ Partial TP error: {e}")
            return False
            
    def modify_stop_loss(self, ticket, new_sl):
        """Modify stop loss"""
        try:
            position = mt5.positions_get(ticket=ticket)
            if not position:
                return False
                
            position = position[0]
            
            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "symbol": position.symbol,
                "sl": new_sl,
                "tp": position.tp,
                "position": ticket,
                "magic": 123456,
                "comment": "SL MODIFIED - Nyx AI",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            result = mt5.order_send(request)
            if result.retcode == mt5.TRADE_RETCODE_DONE:
                # Update trade state
                if ticket in self.active_trades:
                    self.active_trades[ticket]['sl'] = new_sl
                print(f"✅ SL modified to {new_sl:.5f} for position {ticket}")
                return True
            else:
                print(f"❌ SL modification failed: {result.retcode}")
                return False
                
        except Exception as e:
            print(f"❌ SL modification error: {e}")
            return False
            
    def should_force_close(self, ticket, current_price):
        """Check if trade should be force closed"""
        if not ENABLE_LIFECYCLE_MANAGER:
            return False
            
        trade = self.active_trades.get(ticket)
        if not trade:
            return False
            
        current_time = time.time()
        age_minutes = (current_time - trade['entry_time']) / 60
        
        # Force close after 45 minutes if no progress
        if age_minutes > 45:
            entry = trade['entry']
            progress = abs(current_price - entry) / abs(trade['tp'] - entry)
            if progress < 0.3:  # Less than 30% progress toward TP
                print(f"⏰ Force close: Position {ticket} no progress after {age_minutes:.0f}min")
                return True
                
        # Force close if loss exceeds 1.5x planned risk
        position = mt5.positions_get(ticket=ticket)
        if position:
            position = position[0]
            planned_risk = abs(trade['entry'] - trade['sl'])
            current_loss = abs(position.price_current - trade['entry'])
            if current_loss > planned_risk * 1.5 and position.profit < 0:
                print(f"🛑 Force close: Position {ticket} loss exceeded 1.5x risk")
                return True
                
        return False
        
    def cleanup_trade(self, ticket):
        """Clean up trade data when closed"""
        if ticket in self.active_trades:
            del self.active_trades[ticket]
        self.partial_tp_executed.discard(ticket)
        self.break_even_moved.discard(ticket)
        self.trailing_active.discard(ticket)
