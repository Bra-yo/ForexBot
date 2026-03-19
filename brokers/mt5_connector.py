"""
MetaTrader 5 Connector for BrayoForexBot
Professional broker integration for real forex trading
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pytz
import time
import logging
from typing import Dict, List, Optional, Tuple
from config import Config

logger = logging.getLogger(__name__)

class MT5Connector:
    """
    Professional MT5 connector for real forex trading
    Handles data retrieval, order execution, and account management
    """
    
    def __init__(self):
        self.connected = False
        self.account_info = None
        self.symbols_info = {}
        self.timezone = pytz.timezone('EET')  # MetaTrader server timezone
        
    def initialize(self, login: int = None, password: str = None, 
                   server: str = None, path: str = None) -> bool:
        """
        Initialize MT5 connection
        
        Args:
            login: Account number
            password: Account password  
            server: Broker server
            path: MT5 terminal path
            
        Returns:
            Connection success status
        """
        try:
            # Initialize MT5 terminal
            if not mt5.initialize():
                logger.error("MT5 initialize() failed")
                return False
            
            # Login if credentials provided
            if login and password and server:
                authorized = mt5.login(login, password=password, server=server)
                if not authorized:
                    logger.error(f"MT5 login failed: {mt5.last_error()}")
                    return False
                logger.info(f"MT5 login successful: {login}")
            
            # Verify connection
            if not mt5.terminal_info():
                logger.error("MT5 terminal not connected")
                return False
            
            self.connected = True
            
            # Get account information
            self.account_info = mt5.account_info()
            if self.account_info:
                logger.info(f"Connected to account: {self.account_info.login}")
                logger.info(f"Balance: ${self.account_info.balance:.2f}")
                logger.info(f"Equity: ${self.account_info.equity:.2f}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing MT5: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MT5"""
        try:
            if self.connected:
                mt5.shutdown()
                self.connected = False
                logger.info("MT5 disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting MT5: {e}")
    
    def get_account_info(self) -> Dict:
        """Get current account information"""
        try:
            if not self.connected:
                return {'error': 'Not connected to MT5'}
            
            account_info = mt5.account_info()
            if account_info is None:
                return {'error': 'Failed to get account info'}
            
            return {
                'login': account_info.login,
                'server': account_info.server,
                'currency': account_info.currency,
                'balance': account_info.balance,
                'equity': account_info.equity,
                'margin': account_info.margin,
                'free_margin': account_info.free_margin,
                'margin_level': account_info.margin_level,
                'leverage': account_info.leverage,
                'profit': account_info.profit,
                'swap': account_info.swap,
                'margin_free': account_info.margin_free,
                'margin_used': account_info.margin_used
            }
            
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {'error': str(e)}
    
    def get_symbol_info(self, symbol: str) -> Dict:
        """Get symbol information"""
        try:
            if not self.connected:
                return {'error': 'Not connected to MT5'}
            
            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return {'error': f'Symbol {symbol} not found'}
            
            # Store for future use
            self.symbols_info[symbol] = symbol_info
            
            return {
                'symbol': symbol_info.name,
                'digits': symbol_info.digits,
                'point': symbol_info.point,
                'tick_value': symbol_info.trade_tick_value,
                'tick_size': symbol_info.trade_tick_size,
                'contract_size': symbol_info.trade_contract_size,
                'volume_min': symbol_info.volume_min,
                'volume_max': symbol_info.volume_max,
                'volume_step': symbol_info.volume_step,
                'spread': symbol_info.spread,
                'swap_long': symbol_info.swap_long,
                'swap_short': symbol_info.swap_short,
                'starting': symbol_info.starting,
                'expiration': symbol_info.expiration,
                'trade_mode': symbol_info.trade_mode
            }
            
        except Exception as e:
            logger.error(f"Error getting symbol info for {symbol}: {e}")
            return {'error': str(e)}
    
    def get_historical_data(self, symbol: str, timeframe: str, 
                           start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Get historical data from MT5
        
        Args:
            symbol: Currency pair (e.g., 'EURUSD')
            timeframe: Timeframe (M1, M5, M15, H1, H4, D1)
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            if not self.connected:
                return pd.DataFrame()
            
            # Convert timeframe string to MT5 constant
            timeframe_map = {
                'M1': mt5.TIMEFRAME_M1,
                'M5': mt5.TIMEFRAME_M5,
                'M15': mt5.TIMEFRAME_M15,
                'M30': mt5.TIMEFRAME_M30,
                'H1': mt5.TIMEFRAME_H1,
                'H4': mt5.TIMEFRAME_H4,
                'D1': mt5.TIMEFRAME_D1,
                'W1': mt5.TIMEFRAME_W1,
                'MN1': mt5.TIMEFRAME_MN1
            }
            
            mt5_timeframe = timeframe_map.get(timeframe, mt5.TIMEFRAME_H1)
            
            # Get historical data
            rates = mt5.copy_rates_range(symbol, mt5_timeframe, start_date, end_date)
            
            if rates is None or len(rates) == 0:
                logger.warning(f"No data found for {symbol} {timeframe}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(rates)
            
            # Convert timestamp to datetime
            df['time'] = pd.to_datetime(df['time'], unit='s')
            
            # Rename columns to match our format
            df = df.rename(columns={
                'time': 'timestamp',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'tick_volume': 'volume',
                'spread': 'spread',
                'real_volume': 'real_volume'
            })
            
            # Set timestamp as index
            df = df.set_index('timestamp')
            
            logger.info(f"Retrieved {len(df)} candles for {symbol} {timeframe}")
            return df
            
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return pd.DataFrame()
    
    def get_current_price(self, symbol: str) -> Dict:
        """Get current price for a symbol"""
        try:
            if not self.connected:
                return {'error': 'Not connected to MT5'}
            
            # Get tick
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return {'error': f'No tick data for {symbol}'}
            
            return {
                'symbol': symbol,
                'bid': tick.bid,
                'ask': tick.ask,
                'last': tick.last,
                'volume': tick.volume,
                'time': pd.to_datetime(tick.time, unit='s')
            }
            
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return {'error': str(e)}
    
    def place_market_order(self, symbol: str, order_type: str, volume: float,
                          deviation: int = 20, magic: int = 234000) -> Dict:
        """
        Place a market order
        
        Args:
            symbol: Currency pair
            order_type: 'BUY' or 'SELL'
            volume: Position size in lots
            deviation: Maximum price deviation
            magic: Magic number for orders
            
        Returns:
            Order result
        """
        try:
            if not self.connected:
                return {'success': False, 'error': 'Not connected to MT5'}
            
            # Get symbol info
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return {'success': False, 'error': f'Symbol {symbol} not found'}
            
            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if tick is None:
                return {'success': False, 'error': f'No tick data for {symbol}'}
            
            # Determine price and order type
            if order_type.upper() == 'BUY':
                price = tick.ask
                mt5_type = mt5.ORDER_TYPE_BUY
                sl_price = price - 50 * symbol_info.point  # 50 pips SL
                tp_price = price + 100 * symbol_info.point  # 100 pips TP
            elif order_type.upper() == 'SELL':
                price = tick.bid
                mt5_type = mt5.ORDER_TYPE_SELL
                sl_price = price + 50 * symbol_info.point  # 50 pips SL
                tp_price = price - 100 * symbol_info.point  # 100 pips TP
            else:
                return {'success': False, 'error': 'Invalid order type'}
            
            # Build request
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": symbol,
                "volume": volume,
                "type": mt5_type,
                "price": price,
                "sl": sl_price,
                "tp": tp_price,
                "deviation": deviation,
                "magic": magic,
                "comment": "BrayoForexBot",
                "type_time": mt5.ORDER_TIME_GTC,
                "type_filling": mt5.ORDER_FILLING_IOC,
            }
            
            # Send order
            result = mt5.order_send(request)
            
            if result.retcode != mt5.TRADE_RETCODE_DONE:
                return {
                    'success': False,
                    'error': f'Order failed: {result.comment}',
                    'retcode': result.retcode
                }
            
            logger.info(f"Order executed: {order_type} {volume} {symbol} at {price}")
            
            return {
                'success': True,
                'order': result.order,
                'deal': result.deal,
                'volume': result.volume,
                'price': result.price,
                'bid': result.bid,
                'ask': result.ask,
                'comment': result.comment
            }
            
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {'success': False, 'error': str(e)}
    
    def close_position(self, position: Dict, deviation: int = 20) -> Dict:
        """
        Close an open position
        
        Args:
            position: Position dictionary from get_positions()
            deviation: Maximum price deviation
            
        Returns:
            Close result
        """
        try:
            if not self.connected:
                return {'success': False, 'error': 'Not connected to MT5'}
            
            # Build close request
            if position['type'] == mt5.POSITION_TYPE_BUY:
                order_type = mt5.ORDER_TYPE_SELL
                price = mt5.symbol_info_tick(position['symbol']).bid
            else:  # SELL
                order_type = mt5.ORDER_TYPE_BUY
                price = mt5.symbol_info_tick(position['symbol']).ask
            
            request = {
                "action": mt5.TRADE_ACTION_DEAL,
                "symbol": position['symbol'],
                "volume": position['volume'],
                "type": order_type,
                "position": position['ticket'],
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
            
            logger.info(f"Position closed: {position['ticket']} at {price}")
            
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
    
    def get_positions(self) -> List[Dict]:
        """Get all open positions"""
        try:
            if not self.connected:
                return []
            
            positions = mt5.positions_get()
            if positions is None:
                return []
            
            position_list = []
            for pos in positions:
                position_list.append({
                    'ticket': pos.ticket,
                    'symbol': pos.symbol,
                    'type': pos.type,
                    'volume': pos.volume,
                    'price_open': pos.price_open,
                    'price_current': pos.price_current,
                    'sl': pos.sl,
                    'tp': pos.tp,
                    'swap': pos.swap,
                    'profit': pos.profit,
                    'time': pd.to_datetime(pos.time, unit='s'),
                    'comment': pos.comment
                })
            
            return position_list
            
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def get_orders_history(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get order history"""
        try:
            if not self.connected:
                return []
            
            history = mt5.history_orders_get(start_date, end_date)
            if history is None:
                return []
            
            order_list = []
            for order in history:
                order_list.append({
                    'ticket': order.ticket,
                    'symbol': order.symbol,
                    'type': order.type,
                    'volume': order.volume,
                    'price_open': order.price_open,
                    'price_current': order.price_current,
                    'sl': order.sl,
                    'tp': order.tp,
                    'state': order.state,
                    'time_setup': pd.to_datetime(order.time_setup, unit='s'),
                    'time_done': pd.to_datetime(order.time_done, unit='s),
                    'comment': order.comment,
                    'commission': order.commission,
                    'swap': order.swap,
                    'profit': order.profit
                })
            
            return order_list
            
        except Exception as e:
            logger.error(f"Error getting order history: {e}")
            return []
    
    def get_deals_history(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Get deals (executed trades) history"""
        try:
            if not self.connected:
                return []
            
            deals = mt5.history_deals_get(start_date, end_date)
            if deals is None:
                return []
            
            deal_list = []
            for deal in deals:
                deal_list.append({
                    'ticket': deal.ticket,
                    'order': deal.order,
                    'symbol': deal.symbol,
                    'type': deal.type,
                    'volume': deal.volume,
                    'price': deal.price,
                    'commission': deal.commission,
                    'swap': deal.swap,
                    'profit': deal.profit,
                    'time': pd.to_datetime(deal.time, unit='s'),
                    'entry': deal.entry,
                    'comment': deal.comment
                })
            
            return deal_list
            
        except Exception as e:
            logger.error(f"Error getting deals history: {e}")
            return []
    
    def is_market_open(self, symbol: str) -> bool:
        """Check if market is open for symbol"""
        try:
            if not self.connected:
                return False
            
            symbol_info = mt5.symbol_info(symbol)
            if symbol_info is None:
                return False
            
            return symbol_info.visible and symbol_info.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED
            
        except Exception as e:
            logger.error(f"Error checking market status: {e}")
            return False
    
    def get_server_time(self) -> datetime:
        """Get MT5 server time"""
        try:
            if not self.connected:
                return datetime.now()
            
            terminal_info = mt5.terminal_info()
            if terminal_info is None:
                return datetime.now()
            
            return pd.to_datetime(terminal_info.time, unit='s')
            
        except Exception as e:
            logger.error(f"Error getting server time: {e}")
            return datetime.now()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
