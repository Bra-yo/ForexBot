"""
MT5 Order Execution System for BrayoForexBot
Professional order management with advanced features
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import time
import threading
import queue
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from .mt5_connector import MT5Connector

logger = logging.getLogger(__name__)

class OrderType(Enum):
    """Order types"""
    BUY = "BUY"
    SELL = "SELL"
    BUY_LIMIT = "BUY_LIMIT"
    SELL_LIMIT = "SELL_LIMIT"
    BUY_STOP = "BUY_STOP"
    SELL_STOP = "SELL_STOP"

class OrderStatus(Enum):
    """Order statuses"""
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

@dataclass
class OrderRequest:
    """Order request dataclass"""
    symbol: str
    order_type: OrderType
    volume: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    deviation: int = 20
    magic: int = 234000
    comment: str = "BrayoForexBot"
    expiration: Optional[datetime] = None

@dataclass
class Position:
    """Position dataclass"""
    ticket: int
    symbol: str
    type: int  # mt5.POSITION_TYPE_BUY or SELL
    volume: float
    price_open: float
    price_current: float
    sl: float
    tp: float
    swap: float
    profit: float
    time: datetime
    comment: str

class MT5OrderExecutor:
    """
    Professional MT5 order execution system
    Handles order placement, modification, and position management
    """
    
    def __init__(self, mt5_connector: MT5Connector):
        self.mt5 = mt5_connector
        self.pending_orders = {}
        self.order_queue = queue.Queue()
        self.execution_thread = None
        self.running = False
        self.order_callbacks = []
        
        # Order management
        self.next_magic = 234000
        self.max_orders_per_second = 5
        self.last_order_time = 0
        
        # Risk settings
        self.max_position_size = 10.0  # Maximum lots per position
        self.max_total_positions = 5   # Maximum open positions
        self.max_risk_per_trade = 0.02  # 2% risk per trade
        
    def start_execution_thread(self):
        """Start the order execution thread"""
        try:
            if self.running:
                logger.warning("Execution thread already running")
                return
            
            self.running = True
            self.execution_thread = threading.Thread(
                target=self._execution_loop,
                daemon=True
            )
            self.execution_thread.start()
            
            logger.info("Order execution thread started")
            
        except Exception as e:
            logger.error(f"Error starting execution thread: {e}")
            self.running = False
    
    def stop_execution_thread(self):
        """Stop the order execution thread"""
        try:
            self.running = False
            if self.execution_thread:
                self.execution_thread.join(timeout=5)
            
            logger.info("Order execution thread stopped")
            
        except Exception as e:
            logger.error(f"Error stopping execution thread: {e}")
    
    def place_market_order(self, request: OrderRequest) -> Dict:
        """
        Place a market order immediately
        
        Args:
            request: Order request
            
        Returns:
            Order execution result
        """
        try:
            # Validate request
            validation_result = self._validate_order_request(request)
            if not validation_result['valid']:
                return {'success': False, 'error': validation_result['error']}
            
            # Rate limiting
            self._enforce_rate_limit()
            
            # Get current price if not provided
            if request.price is None:
                tick = self.mt5.get_current_price(request.symbol)
                if 'error' in tick:
                    return {'success': False, 'error': f"Cannot get price: {tick['error']}"}
                
                request.price = tick.ask if request.order_type == OrderType.BUY else tick.bid
            
            # Build MT5 order request
            mt5_request = self._build_mt5_request(request)
            
            # Execute order
            result = mt5.order_send(mt5_request)
            
            # Process result
            return self._process_order_result(result, request)
            
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return {'success': False, 'error': str(e)}
    
    def place_pending_order(self, request: OrderRequest) -> Dict:
        """
        Place a pending order
        
        Args:
            request: Order request
            
        Returns:
            Order result
        """
        try:
            # Validate request
            validation_result = self._validate_order_request(request)
            if not validation_result['valid']:
                return {'success': False, 'error': validation_result['error']}
            
            # Check if price is provided for pending orders
            if request.price is None:
                return {'success': False, 'error': 'Price required for pending orders'}
            
            # Rate limiting
            self._enforce_rate_limit()
            
            # Build MT5 order request
            mt5_request = self._build_mt5_request(request)
            
            # Execute order
            result = mt5.order_send(mt5_request)
            
            # Process result
            return self._process_order_result(result, request)
            
        except Exception as e:
            logger.error(f"Error placing pending order: {e}")
            return {'success': False, 'error': str(e)}
    
    def modify_position(self, ticket: int, sl: float = None, tp: float = None, 
                       price: float = None) -> Dict:
        """
        Modify an open position
        
        Args:
            ticket: Position ticket
            sl: New stop loss
            tp: New take profit
            price: New price (for pending orders)
            
        Returns:
            Modification result
        """
        try:
            # Get position info
            position = self._get_position_by_ticket(ticket)
            if position is None:
                return {'success': False, 'error': 'Position not found'}
            
            # Build modification request
            request = {
                "action": mt5.TRADE_ACTION_MODIFY,
                "position": ticket,
                "symbol": position.symbol,
                "sl": sl if sl is not None else position.sl,
                "tp": tp if tp is not None else position.tp,
                "price": price if price is not None else position.price_open,
                "deviation": 20,
                "magic": 234000,
                "comment": "BrayoForexBot modify",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send modification
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    'success': False,
                    'error': f'Modification failed: {result.comment}',
                    'retcode': result.retcode
                }
            
            logger.info(f"Position {ticket} modified successfully")
            
            return {
                'success': True,
                'ticket': ticket,
                'new_sl': result.sl,
                'new_tp': result.tp,
                'comment': result.comment
            }
            
        except Exception as e:
            logger.error(f"Error modifying position: {e}")
            return {'success': False, 'error': str(e)}
    
    def close_position(self, ticket: int, volume: float = None, 
                      deviation: int = 20) -> Dict:
        """
        Close a position
        
        Args:
            ticket: Position ticket
            volume: Volume to close (None for full close)
            deviation: Maximum price deviation
            
        Returns:
            Close result
        """
        try:
            # Get position info
            position = self._get_position_by_ticket(ticket)
            if position is None:
                return {'success': False, 'error': 'Position not found'}
            
            # Use provided volume or full position
            close_volume = volume if volume is not None else position.volume
            
            # Build close request
            if position.type == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(position.symbol).bid
            else:  # SELL
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(position.symbol).ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position.symbol,
                "volume": close_volume,
                "type": order_type,
                "position": ticket,
                "price": price,
                "deviation": deviation,
                "magic": 234000,
                "comment": "BrayoForexBot close",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send close order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    'success': False,
                    'error': f'Close failed: {result.comment}',
                    'retcode': result.retcode
                }
            
            logger.info(f"Position {ticket} closed: {close_volume} lots at {price}")
            
            return {
                'success': True,
                'order': result.order,
                'deal': result.deal,
                'volume': result.volume,
                'price': result.price,
                'comment': result.comment
            }
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {'success': False, 'error': str(e)}
    
    def cancel_order(self, ticket: int) -> Dict:
        """
        Cancel a pending order
        
        Args:
            ticket: Order ticket
            
        Returns:
            Cancellation result
        """
        try:
            # Get order info
            order = self._get_order_by_ticket(ticket)
            if order is None:
                return {'success': False, 'error': 'Order not found'}
            
            # Build cancellation request
            request = {
                "action": mt5.TRADE_ACTION_REMOVE,
                "order": ticket,
                "symbol": order.symbol,
                "volume": order.volume,
                "type": order.type,
                "price": order.price_open,
                "deviation": 20,
                "magic": 234000,
                "comment": "BrayoForexBot cancel",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send cancellation
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    'success': False,
                    'error': f'Cancel failed: {result.comment}',
                    'retcode': result.retcode
                }
            
            logger.info(f"Order {ticket} cancelled successfully")
            
            return {
                'success': True,
                'order': result.order,
                'comment': result.comment
            }
            
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_open_positions(self) -> List[Position]:
        """Get all open positions"""
        try:
            positions_data = self.mt5.get_positions()
            positions = []
            
            for pos_data in positions_data:
                position = Position(
                    ticket=pos_data['ticket'],
                    symbol=pos_data['symbol'],
                    type=pos_data['type'],
                    volume=pos_data['volume'],
                    price_open=pos_data['price_open'],
                    price_current=pos_data['price_current'],
                    sl=pos_data['sl'],
                    tp=pos_data['tp'],
                    swap=pos_data['swap'],
                    profit=pos_data['profit'],
                    time=pos_data['time'],
                    comment=pos_data['comment']
                )
                positions.append(position)
            
            return positions
            
        except Exception as e:
            logger.error(f"Error getting open positions: {e}")
            return []
    
    def get_pending_orders(self) -> List[Dict]:
        """Get all pending orders"""
        try:
            orders = mt5.orders_get()
            if orders is None:
                return []
            
            order_list = []
            for order in orders:
                order_list.append({
                    'ticket': order.ticket,
                    'symbol': order.symbol,
                    'type': order.type,
                    'volume': order.volume,
                    'price_open': order.price_open,
                    'sl': order.sl,
                    'tp': order.tp,
                    'state': order.state,
                    'time_setup': pd.to_datetime(order.time_setup, unit='s'),
                    'expiration': pd.to_datetime(order.expiration, unit='s') if order.expiration > 0 else None,
                    'comment': order.comment
                })
            
            return order_list
            
        except Exception as e:
            logger.error(f"Error getting pending orders: {e}")
            return []
    
    def calculate_position_size(self, symbol: str, risk_amount: float, 
                               stop_distance: float) -> float:
        """
        Calculate optimal position size based on risk
        
        Args:
            symbol: Currency pair
            risk_amount: Risk amount in account currency
            stop_distance: Stop loss distance in price units
            
        Returns:
            Position size in lots
        """
        try:
            # Get symbol info
            symbol_info = self.mt5.get_symbol_info(symbol)
            if 'error' in symbol_info:
                return 0.01  # Minimum size
            
            # Calculate position size
            tick_value = symbol_info['tick_value']
            point = symbol_info['point']
            
            # Position size = Risk Amount / (Stop Distance * Tick Value / Point)
            if stop_distance > 0 and tick_value > 0:
                position_size = risk_amount / (stop_distance * tick_value / point)
            else:
                position_size = 0.01
            
            # Apply limits
            min_lot = symbol_info['volume_min']
            max_lot = symbol_info['volume_max']
            lot_step = symbol_info['volume_step']
            
            # Round to valid step
            position_size = round(position_size / lot_step) * lot_step
            position_size = max(min_lot, min(position_size, max_lot))
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.01
    
    def _validate_order_request(self, request: OrderRequest) -> Dict:
        """Validate order request"""
        try:
            # Check connection
            if not self.mt5.connected:
                return {'valid': False, 'error': 'Not connected to MT5'}
            
            # Check symbol
            symbol_info = self.mt5.get_symbol_info(request.symbol)
            if 'error' in symbol_info:
                return {'valid': False, 'error': f"Symbol {request.symbol} not available"}
            
            # Check market open for market orders
            if request.order_type in [OrderType.BUY, OrderType.SELL]:
                if not self.mt5.is_market_open(request.symbol):
                    return {'valid': False, 'error': f'Market closed for {request.symbol}'}
            
            # Check volume
            if request.volume <= 0:
                return {'valid': False, 'error': 'Volume must be positive'}
            
            if request.volume < symbol_info['volume_min']:
                return {'valid': False, 'error': f'Volume below minimum ({symbol_info["volume_min"]})'}
            
            if request.volume > symbol_info['volume_max']:
                return {'valid': False, 'error': f'Volume above maximum ({symbol_info["volume_max"]})'}
            
            # Check total positions
            open_positions = self.get_open_positions()
            if len(open_positions) >= self.max_total_positions:
                return {'valid': False, 'error': f'Maximum positions reached ({self.max_total_positions})'}
            
            return {'valid': True, 'error': None}
            
        except Exception as e:
            logger.error(f"Error validating order request: {e}")
            return {'valid': False, 'error': str(e)}
    
    def _enforce_rate_limit(self):
        """Enforce rate limiting for orders"""
        try:
            current_time = time.time()
            time_since_last = current_time - self.last_order_time
            
            min_interval = 1.0 / self.max_orders_per_second
            
            if time_since_last < min_interval:
                time.sleep(min_interval - time_since_last)
            
            self.last_order_time = time.time()
            
        except Exception as e:
            logger.error(f"Error in rate limiting: {e}")
    
    def _build_mt5_request(self, request: OrderRequest) -> Dict:
        """Build MT5 order request"""
        try:
            # Get current price for market orders
            if request.order_type in [OrderType.BUY, OrderType.SELL]:
                tick = self.mt5.get_current_price(request.symbol)
                if 'error' in tick:
                    raise Exception(f"Cannot get price: {tick['error']}")
                
                price = tick.ask if request.order_type == OrderType.BUY else tick.bid
                mt5_type = mt5.ORDER_TYPE_BUY if request.order_type == OrderType.BUY else mt5.ORDER_TYPE_SELL
                action = mt5.TRADE_ACTION_DEAL
            else:
                # Pending orders
                price = request.price
                action = mt5.TRADE_ACTION_PENDING
                
                if request.order_type == OrderType.BUY_LIMIT:
                    mt5_type = mt5.ORDER_TYPE_BUY_LIMIT
                elif request.order_type == OrderType.SELL_LIMIT:
                    mt5_type = mt5.ORDER_TYPE_SELL_LIMIT
                elif request.order_type == OrderType.BUY_STOP:
                    mt5_type = mt5.ORDER_TYPE_BUY_STOP
                elif request.order_type == OrderType.SELL_STOP:
                    mt5_type = mt5.ORDER_TYPE_SELL_STOP
                else:
                    raise Exception(f"Unsupported order type: {request.order_type}")
            
            # Build base request
            mt5_request = {
                "action": action,
                "symbol": request.symbol,
                "volume": request.volume,
                "type": mt5_type,
                "price": price,
                "sl": request.sl,
                "tp": request.tp,
                "deviation": request.deviation,
                "magic": request.magic,
                "comment": request.comment,
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Add expiration for pending orders
            if request.expiration and action == mt5.TRADE_ACTION_PENDING:
                mt5_request["expiration"] = request.expiration
            
            return mt5_request
            
        except Exception as e:
            logger.error(f"Error building MT5 request: {e}")
            raise
    
    def _process_order_result(self, result, request: OrderRequest) -> Dict:
        """Process MT5 order result"""
        try:
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    'success': False,
                    'error': f'Order failed: {result.comment}',
                    'retcode': result.retcode,
                    'request': request
                }
            
            # Success
            success_result = {
                'success': True,
                'order': result.order,
                'deal': result.deal,
                'volume': result.volume,
                'price': result.price,
                'bid': result.bid,
                'ask': result.ask,
                'comment': result.comment,
                'request': request
            }
            
            # Notify callbacks
            self._notify_order_callbacks(success_result)
            
            return success_result
            
        except Exception as e:
            logger.error(f"Error processing order result: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_position_by_ticket(self, ticket: int) -> Optional[Dict]:
        """Get position by ticket"""
        try:
            positions = self.mt5.get_positions()
            for pos in positions:
                if pos['ticket'] == ticket:
                    return pos
            return None
        except Exception as e:
            logger.error(f"Error getting position by ticket: {e}")
            return None
    
    def _get_order_by_ticket(self, ticket: int) -> Optional[Dict]:
        """Get order by ticket"""
        try:
            orders = mt5.orders_get()
            if orders is None:
                return None
            
            for order in orders:
                if order.ticket == ticket:
                    return order
            return None
        except Exception as e:
            logger.error(f"Error getting order by ticket: {e}")
            return None
    
    def _notify_order_callbacks(self, result: Dict):
        """Notify order execution callbacks"""
        try:
            for callback in self.order_callbacks:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Error in order callback: {e}")
        except Exception as e:
            logger.error(f"Error notifying callbacks: {e}")
    
    def add_order_callback(self, callback):
        """Add order execution callback"""
        self.order_callbacks.append(callback)
    
    def remove_order_callback(self, callback):
        """Remove order execution callback"""
        try:
            self.order_callbacks.remove(callback)
        except ValueError:
            pass
    
    def _execution_loop(self):
        """Main execution loop for queued orders"""
        while self.running:
            try:
                # Process queued orders
                try:
                    request = self.order_queue.get(timeout=1)
                    
                    if request['type'] == 'market':
                        result = self.place_market_order(request['data'])
                    elif request['type'] == 'pending':
                        result = self.place_pending_order(request['data'])
                    else:
                        result = {'success': False, 'error': 'Unknown order type'}
                    
                    # Store result
                    self.pending_orders[request['id']] = result
                    
                except queue.Empty:
                    continue
                
            except Exception as e:
                logger.error(f"Error in execution loop: {e}")
                time.sleep(1)
    
    def get_execution_stats(self) -> Dict:
        """Get execution statistics"""
        try:
            return {
                'running': self.running,
                'pending_orders': len(self.pending_orders),
                'queue_size': self.order_queue.qsize(),
                'callbacks': len(self.order_callbacks),
                'max_orders_per_second': self.max_orders_per_second,
                'last_order_time': self.last_order_time
            }
        except Exception as e:
            logger.error(f"Error getting execution stats: {e}")
            return {}
