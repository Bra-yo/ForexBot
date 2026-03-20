"""
MT5 Integrated Trading Engine for BrayoForexBot
Combines our existing trading logic with MT5 professional execution
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Import existing components
from trading_engine import TradingEngine
from technical_analysis import TechnicalAnalysis
from risk_management import RiskManager
from notifications import NotificationManager

# Import MT5 components
from .mt5_connector import MT5Connector
from .mt5_data_reader import MT5DataReader
from .mt5_order_executor import MT5OrderExecutor, OrderRequest, OrderType
from .mt5_streaming import MT5Streamer, TickData, BarData

logger = logging.getLogger(__name__)

@dataclass
class MT5TradingDecision:
    """Enhanced trading decision with MT5 specifics"""
    symbol: str
    action: str  # BUY, SELL, WAIT
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    position_size: float
    reasons: List[str]
    timestamp: datetime
    market_conditions: Dict
    indicators: Dict

class MT5TradingEngine(TradingEngine):
    """
    Enhanced Trading Engine with MT5 integration
    Combines our proven logic with professional broker execution
    """
    
    def __init__(self, risk_manager: RiskManager = None, 
                 mt5_login: int = None, mt5_password: str = None, 
                 mt5_server: str = None):
        # Initialize parent class
        super().__init__(risk_manager)
        
        # MT5 components
        self.mt5_connector = MT5Connector()
        self.mt5_data_reader = None
        self.mt5_order_executor = None
        self.mt5_streamer = None
        
        # MT5 credentials
        self.mt5_login = mt5_login
        self.mt5_password = mt5_password
        self.mt5_server = mt5_server
        
        # Enhanced features
        self.real_time_analysis = True
        self.streaming_active = False
        self.last_analysis_time = {}
        
        # Performance tracking
        self.execution_stats = {
            'orders_placed': 0,
            'orders_executed': 0,
            'orders_failed': 0,
            'total_pnl': 0,
            'win_rate': 0
        }
        
    def initialize_mt5(self) -> bool:
        """Initialize MT5 connection and components"""
        try:
            # Connect to MT5
            success = self.mt5_connector.initialize(
                login=self.mt5_login,
                password=self.mt5_password,
                server=self.mt5_server
            )
            
            if not success:
                logger.error("Failed to initialize MT5 connection")
                return False
            
            # Initialize components
            self.mt5_data_reader = MT5DataReader(self.mt5_connector)
            self.mt5_order_executor = MT5OrderExecutor(self.mt5_connector)
            self.mt5_streamer = MT5Streamer(self.mt5_connector)
            
            # Start order execution thread
            self.mt5_order_executor.start_execution_thread()
            
            logger.info("MT5 components initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing MT5: {e}")
            return False
    
    def start_real_time_trading(self, symbols: List[str], timeframes: List[str] = None):
        """Start real-time trading with streaming data"""
        try:
            if not self.mt5_connector.connected:
                logger.error("MT5 not connected")
                return False
            
            if timeframes is None:
                timeframes = ['M1', 'M5', 'M15', 'H1']
            
            # Start streaming
            self.mt5_streamer.start_streaming(symbols, timeframes)
            self.streaming_active = True
            
            # Subscribe to tick updates for each symbol
            for symbol in symbols:
                self.mt5_streamer.subscribe_to_ticks(symbol, self._on_tick_update)
                
                # Subscribe to bar updates for each timeframe
                for timeframe in timeframes:
                    self.mt5_streamer.subscribe_to_bars(symbol, timeframe, self._on_bar_update)
            
            # Add analytics callback
            self.mt5_streamer.add_analytics_callback(self._on_analytics_update)
            
            logger.info(f"Started real-time trading for {len(symbols)} symbols")
            return True
            
        except Exception as e:
            logger.error(f"Error starting real-time trading: {e}")
            return False
    
    def stop_real_time_trading(self):
        """Stop real-time trading"""
        try:
            if self.mt5_streamer:
                self.mt5_streamer.stop_streaming()
            
            if self.mt5_order_executor:
                self.mt5_order_executor.stop_execution_thread()
            
            self.streaming_active = False
            logger.info("Stopped real-time trading")
            
        except Exception as e:
            logger.error(f"Error stopping real-time trading: {e}")
    
    def analyze_symbol_real_time(self, symbol: str, timeframe: str = 'M1') -> Optional[MT5TradingDecision]:
        """
        Analyze a symbol in real-time using streaming data
        
        Args:
            symbol: Currency pair
            timeframe: Analysis timeframe
            
        Returns:
            Trading decision or None
        """
        try:
            # Get latest bar data
            latest_bar = self.mt5_streamer.get_latest_bar(symbol, timeframe)
            if latest_bar is None:
                return None
            
            # Get historical data for technical analysis
            bars_history = self.mt5_streamer.get_bar_history(symbol, timeframe, limit=100)
            if len(bars_history) < 50:
                return None
            
            # Convert to DataFrame for analysis
            data = self._bars_to_dataframe(bars_history)
            
            # Get technical indicators
            indicators = self.mt5_streamer.calculate_real_time_indicators(symbol, timeframe)
            
            # Perform technical analysis
            signals = self.technical_analysis.analyze_signals(data)
            
            # Get market conditions
            market_conditions = self._get_market_conditions(symbol)
            
            # Make trading decision
            decision = self._make_trading_decision(
                symbol, data, signals, indicators, market_conditions
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None
    
    def execute_mt5_trade(self, decision: MT5TradingDecision) -> Dict:
        """
        Execute a trade using MT5
        
        Args:
            decision: Trading decision
            
        Returns:
            Execution result
        """
        try:
            if decision.action == 'WAIT':
                return {'success': True, 'action': 'WAIT', 'reason': 'No trading signal'}
            
            # Validate with risk manager
            if self.risk_manager:
                risk_check = self.risk_manager.can_open_position(decision.symbol, decision.action)
                if not risk_check['allowed']:
                    return {
                        'success': False,
                        'action': decision.action,
                        'reason': f'Risk check failed: {risk_check["reasons"]}'
                    }
            
            # Create order request
            order_type = OrderType.BUY if decision.action == 'BUY' else OrderType.SELL
            order_request = OrderRequest(
                symbol=decision.symbol,
                order_type=order_type,
                volume=decision.position_size,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                comment=f"BrayoForexBot-{decision.confidence:.0f}%"
            )
            
            # Execute order
            result = self.mt5_order_executor.place_market_order(order_request)
            
            # Update stats
            self.execution_stats['orders_placed'] += 1
            
            if result['success']:
                self.execution_stats['orders_executed'] += 1
                
                # Update risk manager
                if self.risk_manager:
                    exposure = decision.position_size * decision.entry_price
                    self.risk_manager.update_pair_exposure(decision.symbol, exposure)
                
                # Record position
                self._record_mt5_position(decision, result)
                
                logger.info(f"Trade executed: {decision.action} {decision.symbol} at {decision.entry_price}")
            else:
                self.execution_stats['orders_failed'] += 1
                logger.error(f"Trade failed: {result['error']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing MT5 trade: {e}")
            return {'success': False, 'error': str(e)}
    
    def manage_mt5_positions(self):
        """Manage open positions with real-time data"""
        try:
            # Get open positions
            positions = self.mt5_order_executor.get_open_positions()
            
            for position in positions:
                # Get current price
                current_price_data = self.mt5_streamer.get_latest_tick(position.symbol)
                if current_price_data is None:
                    continue
                
                current_price = current_price_data.bid if position.type == 0 else current_price_data.ask
                
                # Calculate P&L
                if position.type == 0:  # BUY
                    pnl = (current_price - position.price_open) * position.volume
                    should_close = current_price <= position.sl or current_price >= position.tp
                else:  # SELL
                    pnl = (position.price_open - current_price) * position.volume
                    should_close = current_price >= position.sl or current_price <= position.tp
                
                # Check if position should be closed
                if should_close:
                    close_result = self.mt5_order_executor.close_position(position.ticket)
                    
                    if close_result['success']:
                        # Update risk manager
                        if self.risk_manager:
                            self.risk_manager.update_pair_exposure(position.symbol, -position.volume * position.price_open)
                        
                        # Record in history
                        self._record_mt5_close(position, current_price, close_result)
                        
                        logger.info(f"Position closed: {position.symbol} - PnL: {pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error managing MT5 positions: {e}")
    
    def get_mt5_account_summary(self) -> Dict:
        """Get comprehensive account summary"""
        try:
            # Get account info
            account_info = self.mt5_connector.get_account_info()
            
            # Get open positions
            positions = self.mt5_order_executor.get_open_positions()
            
            # Calculate total exposure
            total_exposure = sum(pos.volume * pos.price_open for pos in positions)
            
            # Calculate unrealized P&L
            unrealized_pnl = sum(pos.profit for pos in positions)
            
            # Get streaming stats
            streaming_stats = self.mt5_streamer.get_streaming_stats() if self.mt5_streamer else {}
            
            summary = {
                'account': account_info,
                'positions': {
                    'count': len(positions),
                    'total_exposure': total_exposure,
                    'unrealized_pnl': unrealized_pnl,
                    'symbols': list(set(pos.symbol for pos in positions))
                },
                'execution_stats': self.execution_stats,
                'streaming_stats': streaming_stats,
                'timestamp': datetime.now()
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting account summary: {e}")
            return {'error': str(e)}
    
    def _on_tick_update(self, tick: TickData):
        """Handle tick updates"""
        try:
            # Update position P&L
            self.manage_mt5_positions()
            
        except Exception as e:
            logger.error(f"Error handling tick update: {e}")
    
    def _on_bar_update(self, bar: BarData):
        """Handle bar updates"""
        try:
            # Analyze for new trading opportunities
            decision = self.analyze_symbol_real_time(bar.symbol, bar.timeframe)
            
            if decision and decision.action in ['BUY', 'SELL']:
                # Execute trade
                result = self.execute_mt5_trade(decision)
                
                # Send notification
                if self.notifications:
                    self.notifications.send_trade_alert({
                        'action': decision.action,
                        'pair': decision.symbol,
                        'entry_price': decision.entry_price,
                        'position_size': decision.position_size,
                        'confidence': decision.confidence,
                        'reasons': decision.reasons
                    })
            
        except Exception as e:
            logger.error(f"Error handling bar update: {e}")
    
    def _on_analytics_update(self, symbol: str, timeframe: str, indicators: Dict):
        """Handle analytics updates"""
        try:
            # Store latest indicators
            if not hasattr(self, 'latest_indicators'):
                self.latest_indicators = {}
            
            key = f"{symbol}_{timeframe}"
            self.latest_indicators[key] = indicators
            
        except Exception as e:
            logger.error(f"Error handling analytics update: {e}")
    
    def _make_trading_decision(self, symbol: str, data: pd.DataFrame, signals: Dict, 
                             indicators: Dict, market_conditions: Dict) -> MT5TradingDecision:
        """Make enhanced trading decision"""
        try:
            # Get current price
            current_price = data['close'].iloc[-1]
            
            # Base decision from signals
            action = signals.get('signal', 'WAIT')
            confidence = signals.get('strength', 0)
            reasons = signals.get('reasons', [])
            
            # Enhance with real-time indicators
            if indicators:
                # RSI confirmation
                if 'rsi' in indicators:
                    rsi = indicators['rsi']
                    if rsi and action == 'BUY' and rsi > 70:
                        confidence *= 0.5  # Reduce confidence if overbought
                        reasons.append("RSI overbought - reducing confidence")
                    elif rsi and action == 'SELL' and rsi < 30:
                        confidence *= 0.5  # Reduce confidence if oversold
                        reasons.append("RSI oversold - reducing confidence")
                
                # Volume confirmation
                if 'volume_ratio' in indicators:
                    volume_ratio = indicators['volume_ratio']
                    if volume_ratio and volume_ratio < 0.5:
                        confidence *= 0.8  # Reduce confidence on low volume
                        reasons.append("Low volume - reducing confidence")
            
            # Market conditions adjustment
            if market_conditions.get('spread', 0) > 0.0002:  # High spread
                confidence *= 0.7
                reasons.append("High spread - reducing confidence")
            
            # Calculate position size
            position_size = self._calculate_position_size(symbol, current_price, confidence)
            
            # Calculate stop loss and take profit
            if action == 'BUY':
                stop_loss = current_price * 0.998  # 20 pips
                take_profit = current_price * 1.002  # 20 pips
            elif action == 'SELL':
                stop_loss = current_price * 1.002  # 20 pips
                take_profit = current_price * 0.998  # 20 pips
            else:
                stop_loss = take_profit = 0
                position_size = 0
            
            return MT5TradingDecision(
                symbol=symbol,
                action=action,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                position_size=position_size,
                reasons=reasons,
                timestamp=datetime.now(),
                market_conditions=market_conditions,
                indicators=indicators
            )
            
        except Exception as e:
            logger.error(f"Error making trading decision: {e}")
            return MT5TradingDecision(
                symbol=symbol, action='WAIT', confidence=0, entry_price=0,
                stop_loss=0, take_profit=0, position_size=0, reasons=[f"Error: {str(e)}"],
                timestamp=datetime.now(), market_conditions={}, indicators={}
            )
    
    def _get_market_conditions(self, symbol: str) -> Dict:
        """Get current market conditions"""
        try:
            tick = self.mt5_streamer.get_latest_tick(symbol)
            if tick is None:
                return {}
            
            return {
                'spread': tick.spread,
                'bid': tick.bid,
                'ask': tick.ask,
                'volume': tick.volume,
                'time': tick.time
            }
            
        except Exception as e:
            logger.error(f"Error getting market conditions: {e}")
            return {}
    
    def _calculate_position_size(self, symbol: str, price: float, confidence: float) -> float:
        """Calculate position size based on confidence and risk"""
        try:
            # Base position size
            base_size = 0.01  # Minimum 0.01 lots
            
            # Scale by confidence
            if self.risk_manager:
                risk_amount = self.risk_manager.account_balance * 0.02  # 2% risk
                stop_distance = price * 0.002  # 20 pips
                size = self.mt5_order_executor.calculate_position_size(symbol, risk_amount, stop_distance)
            else:
                size = base_size
            
            # Adjust by confidence
            adjusted_size = size * (confidence / 100)
            
            # Ensure minimum and maximum
            return max(base_size, min(adjusted_size, 1.0))  # Max 1 lot
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.01
    
    def _bars_to_dataframe(self, bars: List[BarData]) -> pd.DataFrame:
        """Convert bar data to DataFrame"""
        try:
            data = []
            for bar in bars:
                data.append({
                    'timestamp': bar.time,
                    'open': bar.open,
                    'high': bar.high,
                    'low': bar.low,
                    'close': bar.close,
                    'volume': bar.volume
                })
            
            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)
            return df
            
        except Exception as e:
            logger.error(f"Error converting bars to DataFrame: {e}")
            return pd.DataFrame()
    
    def _record_mt5_position(self, decision: MT5TradingDecision, result: Dict):
        """Record MT5 position"""
        try:
            position = {
                'symbol': decision.symbol,
                'action': decision.action,
                'entry_price': decision.entry_price,
                'stop_loss': decision.stop_loss,
                'take_profit': decision.take_profit,
                'position_size': decision.position_size,
                'order_id': result.get('order'),
                'entry_time': decision.timestamp,
                'status': 'OPEN',
                'unrealized_pnl': 0,
                'realized_pnl': 0,
                'confidence': decision.confidence,
                'reasons': decision.reasons
            }
            
            self.positions[decision.symbol] = position
            
            # Add to trading history
            self.trading_history.append({
                'type': 'OPEN',
                'position': position.copy(),
                'timestamp': decision.timestamp
            })
            
        except Exception as e:
            logger.error(f"Error recording MT5 position: {e}")
    
    def _record_mt5_close(self, position, exit_price: float, result: Dict):
        """Record MT5 position close"""
        try:
            # Calculate P&L
            if position.type == 0:  # BUY
                pnl = (exit_price - position.price_open) * position.volume
            else:  # SELL
                pnl = (position.price_open - exit_price) * position.volume
            
            # Update position
            if position.symbol in self.positions:
                self.positions[position.symbol]['status'] = 'CLOSED'
                self.positions[position.symbol]['exit_price'] = exit_price
                self.positions[position.symbol]['exit_time'] = datetime.now()
                self.positions[position.symbol]['realized_pnl'] = pnl
                
                # Update execution stats
                self.execution_stats['total_pnl'] += pnl
                
                # Add to trading history
                self.trading_history.append({
                    'type': 'CLOSE',
                    'position': self.positions[position.symbol].copy(),
                    'timestamp': datetime.now()
                })
                
                # Remove from active positions
                del self.positions[position.symbol]
            
        except Exception as e:
            logger.error(f"Error recording MT5 close: {e}")
    
    def run_real_time_loop(self, symbols: List[str], duration_minutes: int = 60):
        """Run real-time trading loop for specified duration"""
        try:
            logger.info(f"Starting real-time trading loop for {duration_minutes} minutes")
            
            start_time = datetime.now()
            end_time = start_time + timedelta(minutes=duration_minutes)
            
            while datetime.now() < end_time and self.streaming_active:
                try:
                    # Check each symbol for opportunities
                    for symbol in symbols:
                        # Rate limit analysis per symbol
                        last_analysis = self.last_analysis_time.get(symbol, 0)
                        if time.time() - last_analysis < 30:  # Analyze every 30 seconds
                            continue
                        
                        # Analyze symbol
                        decision = self.analyze_symbol_real_time(symbol)
                        
                        if decision and decision.action in ['BUY', 'SELL']:
                            # Execute trade
                            result = self.execute_mt5_trade(decision)
                            
                            if result['success']:
                                logger.info(f"Trade executed: {decision.action} {symbol}")
                            else:
                                logger.warning(f"Trade failed: {result['error']}")
                        
                        self.last_analysis_time[symbol] = time.time()
                    
                    # Manage positions
                    self.manage_mt5_positions()
                    
                    # Small delay
                    time.sleep(5)
                    
                except KeyboardInterrupt:
                    logger.info("Trading loop interrupted by user")
                    break
                except Exception as e:
                    logger.error(f"Error in trading loop: {e}")
                    time.sleep(10)
            
            logger.info("Real-time trading loop completed")
            
        except Exception as e:
            logger.error(f"Error in real-time loop: {e}")
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            self.stop_real_time_trading()
            if self.mt5_connector:
                self.mt5_connector.disconnect()
        except:
            pass
