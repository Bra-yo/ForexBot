import datetime
import streamlit as st
from typing import Dict, List
import logging
import inspect

# Configure logger for TradeManager
logger = logging.getLogger(__name__)

# Create a datetime function to avoid conflicts
def get_now():
    """Get current datetime without conflicts"""
    return datetime.datetime.now()

class TradeManager:
    """Advanced trade management with professional risk controls"""
    
    def __init__(self, mt5_connector):
        self.mt5 = mt5_connector
        self.active_trades = []  # Use internal list instead of st.session_state
        self.daily_loss = 0.0  # Track daily loss internally
        
    def sync_with_mt5_positions(self):
        """Sync active trades with actual MT5 positions"""
        try:
            # Get actual positions from MT5
            positions = self.mt5.get_positions()
            
            if positions and 'error' not in positions:
                mt5_tickets = {pos['ticket'] for pos in positions}
                dashboard_tickets = {trade['ticket'] for trade in self.active_trades}
                
                # Remove trades that are closed in MT5
                for trade in self.active_trades[:]:
                    if trade['ticket'] not in mt5_tickets:
                        # Trade was closed externally, remove from list
                        self.active_trades.remove(trade)
                        
                # Add trades that are missing from dashboard
                for pos in positions:
                    if pos['ticket'] not in dashboard_tickets:
                        # Add existing MT5 position to active trades
                        trade = {
                            'ticket': pos['ticket'],
                            'symbol': pos['symbol'],
                            'type': 'BUY' if pos['type'] == 0 else 'SELL',
                            'volume': pos['volume'],
                            'entry_price': pos['price_open'],
                            'stop_loss': pos['sl'],
                            'take_profit': pos['tp'],
                            'open_time': get_now(),
                            'original_sl': pos['sl']
                        }
                        self.active_trades.append(trade)
                        
        except Exception as e:
            print(f"Error syncing MT5 positions: {e}")
    
    def monitor_active_trades(self, bot_settings: Dict) -> List[Dict]:
        """Monitor and manage all active trades"""
        closed_trades = []
        
        for trade in self.active_trades:
            action = self._evaluate_trade(trade, bot_settings)
            if action['close']:
                if action['reason'] == 'Position Closed (TP/SL)':
                    # Position already closed by MT5, just remove from list
                    result = {
                        'ticket': trade['ticket'],
                        'reason': action['reason'],
                        'profit': 0,  # Will be updated from MT5 history if needed
                        'close_time': get_now()
                    }
                    closed_trades.append(result)
                    # Remove from active trades immediately
                    self.active_trades = [t for t in self.active_trades if t['ticket'] != trade['ticket']]
                    print(f"DEBUG - Removed closed trade {trade['ticket']} from active trades")
                else:
                    # Normal closure process
                    result = self._close_trade(trade, action['reason'])
                    closed_trades.append(result)
            elif action['modify_sl']:
                self._modify_stop_loss(trade, action['new_sl'], action['reason'])
                
        # Remove closed trades
        for result in closed_trades:
            if 'error' not in result:
                # Remove from active trades list
                self.active_trades = [t for t in self.active_trades if t['ticket'] != result['ticket']]
                
        return closed_trades
    
    def _evaluate_trade(self, trade: Dict, settings: Dict) -> Dict:
        """Evaluate if trade should be closed or modified"""
        # Handle both trade dict and ticket number
        ticket = trade['ticket'] if isinstance(trade, dict) else trade
        entry_price = trade['entry_price'] if isinstance(trade, dict) else trade.get('entry_price', 0)
        stop_loss = trade['stop_loss'] if isinstance(trade, dict) else trade.get('stop_loss', 0)
        take_profit = trade['take_profit'] if isinstance(trade, dict) else trade.get('take_profit', 0)
        trade_type = trade['type'] if isinstance(trade, dict) else trade.get('type', 'BUY')
        volume = trade['volume'] if isinstance(trade, dict) else trade.get('volume', 0.01)
        symbol = trade['symbol'] if isinstance(trade, dict) else trade.get('symbol', 'EURUSD')
        
        current_price = self._get_current_price(symbol)
        if not current_price:
            return {'close': False, 'modify_sl': False}
        
        # Get REAL profit from MT5 instead of calculating
        position_found = False
        real_profit = 0
        current_profit = 0  # Initialize outside try block
        profit_pips = 0
        
        try:
            positions = self.mt5.get_positions()
            if positions and 'error' not in positions:
                for pos in positions:
                    if pos['ticket'] == ticket:
                        real_profit = pos.get('profit', 0)
                        position_found = True
                        profit_pips = abs(real_profit / (volume * 10)) if volume > 0 else 0
                        
                        # DEBUG: Print current values for troubleshooting
                        print(f"DEBUG - Trade {ticket}: Type={trade_type}, Current={current_price:.5f}, SL={stop_loss:.5f}, TP={take_profit:.5f}, Real Profit=${real_profit:.2f}, Profit={profit_pips:.1f} pips")
                        break
                
                # If position not found, it might have been closed by TP/SL
                if not position_found:
                    print(f"DEBUG - Trade {ticket}: Position not found in MT5 - likely closed by TP/SL")
                    return {'close': True, 'reason': 'Position Closed (TP/SL)'}
            else:
                # Fallback calculation
                if trade_type == 'BUY':
                    current_profit = (current_price - entry_price) * volume * 100000
                else:
                    current_profit = (entry_price - current_price) * volume * 100000
                
                profit_pips = abs(current_profit / (volume * 10))
                print(f"DEBUG - Trade {ticket}: Type={trade_type}, Current={current_price:.5f}, SL={stop_loss:.5f}, TP={take_profit:.5f}, Calculated Profit={profit_pips:.1f} pips")
        except:
            # Fallback calculation
            if trade_type == 'BUY':
                current_profit = (current_price - entry_price) * volume * 100000
            else:
                current_profit = (entry_price - current_price) * volume * 100000
            
            profit_pips = abs(current_profit / (volume * 10))
            print(f"DEBUG - Trade {ticket}: Type={trade_type}, Current={current_price:.5f}, SL={stop_loss:.5f}, TP={take_profit:.5f}, Calculated Profit={profit_pips:.1f} pips")
        
        # Check stop loss (MOST IMPORTANT - Check first)
        if trade_type == 'BUY' and current_price <= stop_loss:
            print(f"DEBUG - BUY Stop Loss Hit: {current_price:.5f} <= {stop_loss:.5f}")
            return {'close': True, 'reason': 'Stop Loss Hit'}
        elif trade_type == 'SELL' and current_price >= stop_loss:
            print(f"DEBUG - SELL Stop Loss Hit: {current_price:.5f} >= {stop_loss:.5f}")
            return {'close': True, 'reason': 'Stop Loss Hit'}
        
        # ADVANCED EXIT LOGIC - Check BEFORE fixed TP
        # Break-even logic
        if settings['break_even_enabled'] and profit_pips >= settings['min_profit_pips']:
            if trade_type == 'BUY' and stop_loss < entry_price:
                print(f"DEBUG - Moving BUY SL to break-even: {stop_loss:.5f} -> {entry_price:.5f}")
                return {'modify_sl': True, 'new_sl': entry_price, 'reason': 'Break-even'}
            elif trade_type == 'SELL' and stop_loss > entry_price:
                print(f"DEBUG - Moving SELL SL to break-even: {stop_loss:.5f} -> {entry_price:.5f}")
                return {'modify_sl': True, 'new_sl': entry_price, 'reason': 'Break-even'}
        
        # Trailing stop
        if settings['trailing_stop_enabled'] and profit_pips >= settings['trailing_profit_pips']:
            if trade_type == 'BUY':
                new_sl = current_price - (settings['min_profit_pips'] * 0.0001)
                if new_sl > stop_loss:
                    print(f"DEBUG - BUY Trailing stop: {stop_loss:.5f} -> {new_sl:.5f}")
                    return {'modify_sl': True, 'new_sl': new_sl, 'reason': 'Trailing Stop'}
            else:
                new_sl = current_price + (settings['min_profit_pips'] * 0.0001)
                if new_sl < stop_loss:
                    print(f"DEBUG - SELL Trailing stop: {stop_loss:.5f} -> {new_sl:.5f}")
                    return {'modify_sl': True, 'new_sl': new_sl, 'reason': 'Trailing Stop'}
        
        # Time-based exit
        if settings['time_exit_enabled']:
            open_time = trade['open_time'] if isinstance(trade, dict) else trade.get('open_time', get_now())
            trade_duration = get_now() - open_time
            if trade_duration.total_seconds() > settings['max_trade_time_minutes'] * 60:
                if current_profit <= 0:
                    print(f"DEBUG - Time exit: {trade_duration.total_seconds()/60:.1f}m, no profit")
                    return {'close': True, 'reason': 'Time Exit (No Profit)'}
        
        # Check take profit (LAST - after advanced logic)
        if trade_type == 'BUY' and current_price >= take_profit:
            print(f"DEBUG - BUY Take Profit Hit: {current_price:.5f} >= {take_profit:.5f}")
            return {'close': True, 'reason': 'Take Profit Hit'}
        elif trade_type == 'SELL' and current_price <= take_profit:
            print(f"DEBUG - SELL Take Profit Hit: {current_price:.5f} <= {take_profit:.5f}")
            return {'close': True, 'reason': 'Take Profit Hit'}
        
        return {'close': False, 'modify_sl': False}
    
    def _get_current_price(self, symbol: str) -> float:
        """Get current price for symbol"""
        try:
            price_data = self.mt5.get_current_price(symbol)
            return price_data.get('bid', 0) if price_data else 0
        except:
            return 0
    
    def _close_trade(self, trade: Dict, reason: str) -> Dict:
        """Close a trade and record the result"""
        try:
            # Handle both trade dict and ticket number
            ticket = trade['ticket'] if isinstance(trade, dict) else trade
            
            print(f"DEBUG - Attempting to close trade {ticket} for reason: {reason}")
            
            result = self.mt5.close_position(ticket)
            
            print(f"DEBUG - Close result: {result}")
            
            # Update daily loss tracking
            if result.get('profit', 0) < 0:
                self.daily_loss += abs(result['profit'])
            
            return {
                'ticket': ticket,
                'reason': reason,
                'profit': result.get('profit', 0),
                'close_time': get_now()
            }
        except Exception as e:
            print(f"DEBUG - Exception in _close_trade: {e}")
            return {'ticket': trade['ticket'] if isinstance(trade, dict) else trade, 'error': str(e)}
    
    def _modify_stop_loss(self, trade: Dict, new_sl: float, reason: str):
        """Modify stop loss for a trade"""
        try:
            # Handle both trade dict and ticket number
            ticket = trade['ticket'] if isinstance(trade, dict) else trade
            tp = trade['take_profit'] if isinstance(trade, dict) else trade.get('take_profit', 0)
            
            self.mt5.modify_position(ticket, new_sl, tp)
            # Update trade in active trades
            for t in self.active_trades:
                if t['ticket'] == ticket:
                    t['stop_loss'] = new_sl
                    break
        except Exception as e:
            print(f"Error modifying SL: {e}")
    
    def check_daily_loss_limit(self, settings: Dict) -> bool:
        """Check if daily loss limit has been reached"""
        return self.daily_loss >= settings['max_daily_loss']
    
    def check_spread_filter(self, symbol: str, settings: Dict) -> bool:
        """Check if spread is acceptable for trading"""
        if not settings['spread_filter_enabled']:
            return True
            
        try:
            symbol_info = self.mt5.get_symbol_info(symbol)
            if 'error' not in symbol_info:
                spread_pips = symbol_info.get('spread', 0)
                max_spread = settings.get('max_spread_points', settings.get('max_spread_pips', 3))
                print(f"DEBUG - Spread Check: {spread_pips} pips <= {max_spread} pips")
                return spread_pips <= max_spread
        except Exception as e:
            print(f"DEBUG - Spread filter error: {e}")
            pass
        
        return False
    
    def add_trade(self, trade_info: Dict):
        """Add new trade to active trades list"""
        trade = {
            'ticket': trade_info['order'],
            'symbol': trade_info['symbol'],
            'type': trade_info['type'],
            'volume': trade_info['volume'],
            'price_open': trade_info['price'],
            'sl': trade_info['sl'],
            'tp': trade_info['tp'],
            'time': get_now().isoformat(),
            'reason': 'auto_trading'
        }
        self.active_trades.append(trade)
        return trade
    
    def place_trade(self, symbol: str, trade_type: str, lot_size: float, 
                  sl: float, tp: float, current_price: float) -> Dict:
        """Place a new trade"""
        try:
            # Place the order using the correct MT5 method
            result = self.mt5.place_market_order(
                symbol=symbol,
                order_type=trade_type,
                volume=lot_size,
                deviation=20,
                magic=234000
            )
            
            if result.get('success', False):
                # Add to active trades
                trade_info = {
                    'order': result.get('order'),
                    'symbol': symbol,
                    'type': trade_type,
                    'volume': lot_size,
                    'price': current_price,
                    'sl': sl,
                    'tp': tp
                }
                self.add_trade(trade_info)
                
                logger.info(f"✅ Trade placed successfully: {symbol} {trade_type} {lot_size}")
                return {'success': True, 'ticket': result.get('order'), 'trade': trade_info}
            else:
                logger.error(f"❌ Trade placement failed: {result.get('error', 'Unknown error')}")
                return {'success': False, 'error': result.get('error', 'Unknown error')}
                
        except Exception as e:
            logger.error(f"❌ Error placing trade: {e}")
            return {'success': False, 'error': str(e)}
