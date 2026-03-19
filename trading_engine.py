"""
Trading Engine Module for BrayoForexBot
Handles trading decisions, position management, and order execution
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import Config
import logging

logger = logging.getLogger(__name__)

class TradingEngine:
    """Main trading decision engine"""
    
    def __init__(self, risk_manager=None):
        self.risk_manager = risk_manager
        self.positions = {}
        self.trading_history = []
        self.trading_mode = Config.TRADING_MODE
        
    def analyze_trading_opportunity(self, pair, data, signals):
        """
        Analyze a trading opportunity and make a decision
        
        Args:
            pair (str): Currency pair
            data (pd.DataFrame): Market data with indicators
            signals (dict): Technical analysis signals
            
        Returns:
            dict: Trading decision
        """
        try:
            decision = {
                'pair': pair,
                'action': 'WAIT',
                'confidence': 0,
                'entry_price': None,
                'stop_loss': None,
                'take_profit': None,
                'position_size': 0,
                'reasons': [],
                'timestamp': datetime.now()
            }
            
            # Check if we already have a position for this pair
            if pair in self.positions:
                decision['action'] = 'WAIT'
                decision['reasons'].append('Already have position')
                return decision
            
            # Get signal strength
            signal = signals.get('signal', 'WAIT')
            strength = signals.get('strength', 0)
            reasons = signals.get('reasons', [])
            
            # Minimum strength requirement
            if strength < 60:
                decision['action'] = 'WAIT'
                decision['reasons'].append(f'Low signal strength: {strength:.1f}%')
                return decision
            
            # Risk management check
            if self.risk_manager:
                risk_check = self.risk_manager.can_open_position(pair, signal)
                if not risk_check['allowed']:
                    decision['action'] = 'WAIT'
                    decision['reasons'].extend(risk_check['reasons'])
                    return decision
            
            # Get latest price data
            if data.empty:
                decision['action'] = 'WAIT'
                decision['reasons'].append('No market data available')
                return decision
            
            latest_candle = data.iloc[-1]
            entry_price = latest_candle['close']
            
            # Calculate stop loss and take profit
            if signal == 'BUY':
                stop_loss = entry_price - (Config.STOP_LOSS_PIPS * 0.0001)  # Convert pips to price
                take_profit = entry_price + (Config.TAKE_PROFIT_PIPS * 0.0001)
            elif signal == 'SELL':
                stop_loss = entry_price + (Config.STOP_LOSS_PIPS * 0.0001)
                take_profit = entry_price - (Config.TAKE_PROFIT_PIPS * 0.0001)
            else:
                decision['action'] = 'WAIT'
                decision['reasons'].append('No clear trading signal')
                return decision
            
            # Calculate position size
            if self.risk_manager:
                position_size = self.risk_manager.calculate_position_size(
                    pair, entry_price, stop_loss, signal
                )
            else:
                position_size = 0.01  # Default minimum size
            
            # Build final decision
            decision.update({
                'action': signal,
                'confidence': strength,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'take_profit': take_profit,
                'position_size': position_size,
                'reasons': reasons
            })
            
            logger.info(f"Trading decision for {pair}: {signal} at {entry_price:.5f}")
            return decision
            
        except Exception as e:
            logger.error(f"Error analyzing trading opportunity: {e}")
            return {
                'pair': pair,
                'action': 'WAIT',
                'confidence': 0,
                'reasons': [f"Error: {str(e)}"],
                'timestamp': datetime.now()
            }
    
    def execute_trade(self, decision):
        """
        Execute a trading decision
        
        Args:
            decision (dict): Trading decision
            
        Returns:
            dict: Execution result
        """
        try:
            result = {
                'success': False,
                'order_id': None,
                'message': '',
                'timestamp': datetime.now()
            }
            
            if decision['action'] == 'WAIT':
                result['message'] = 'No action needed'
                return result
            
            if self.trading_mode == 'paper':
                # Paper trading - simulate the trade
                result = self._simulate_trade(decision)
            else:
                # Live trading - would connect to broker API
                result = self._execute_live_trade(decision)
            
            if result['success']:
                # Record the position
                self._record_position(decision, result)
                logger.info(f"Trade executed: {decision['action']} {decision['pair']}")
            else:
                logger.error(f"Trade execution failed: {result['message']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return {
                'success': False,
                'message': f"Execution error: {str(e)}",
                'timestamp': datetime.now()
            }
    
    def _simulate_trade(self, decision):
        """Simulate a paper trade"""
        try:
            # Generate fake order ID
            order_id = f"PAPER_{int(datetime.now().timestamp())}"
            
            return {
                'success': True,
                'order_id': order_id,
                'message': f'Paper trade executed: {decision["action"]} {decision["pair"]}',
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Paper trade simulation error: {str(e)}',
                'timestamp': datetime.now()
            }
    
    def _execute_live_trade(self, decision):
        """Execute a live trade (placeholder for broker API)"""
        # This would integrate with actual broker API
        # For now, return not implemented
        return {
            'success': False,
            'message': 'Live trading not implemented yet',
            'timestamp': datetime.now()
        }
    
    def _record_position(self, decision, execution_result):
        """Record a new position"""
        try:
            position = {
                'pair': decision['pair'],
                'action': decision['action'],
                'entry_price': decision['entry_price'],
                'stop_loss': decision['stop_loss'],
                'take_profit': decision['take_profit'],
                'position_size': decision['position_size'],
                'order_id': execution_result['order_id'],
                'entry_time': datetime.now(),
                'status': 'OPEN',
                'unrealized_pnl': 0,
                'realized_pnl': 0
            }
            
            self.positions[decision['pair']] = position
            
            # Add to trading history
            self.trading_history.append({
                'type': 'OPEN',
                'position': position.copy(),
                'timestamp': datetime.now()
            })
            
        except Exception as e:
            logger.error(f"Error recording position: {e}")
    
    def manage_positions(self, market_data):
        """
        Manage existing positions (check for stop loss, take profit, etc.)
        
        Args:
            market_data (dict): Current market data for all pairs
        """
        try:
            for pair, position in list(self.positions.items()):
                if position['status'] != 'OPEN':
                    continue
                
                # Get current price
                if pair not in market_data or market_data[pair].empty:
                    continue
                
                current_price = market_data[pair]['close'].iloc[-1]
                
                # Calculate unrealized PnL
                if position['action'] == 'BUY':
                    unrealized_pnl = (current_price - position['entry_price']) * position['position_size']
                    should_close = (current_price <= position['stop_loss'] or 
                                  current_price >= position['take_profit'])
                else:  # SELL
                    unrealized_pnl = (position['entry_price'] - current_price) * position['position_size']
                    should_close = (current_price >= position['stop_loss'] or 
                                  current_price <= position['take_profit'])
                
                position['unrealized_pnl'] = unrealized_pnl
                
                # Check if position should be closed
                if should_close:
                    self._close_position(pair, current_price, market_data[pair])
                
        except Exception as e:
            logger.error(f"Error managing positions: {e}")
    
    def _close_position(self, pair, exit_price, market_data):
        """Close a position"""
        try:
            if pair not in self.positions:
                return
            
            position = self.positions[pair]
            
            # Calculate realized PnL
            if position['action'] == 'BUY':
                realized_pnl = (exit_price - position['entry_price']) * position['position_size']
            else:  # SELL
                realized_pnl = (position['entry_price'] - exit_price) * position['position_size']
            
            # Update position
            position['status'] = 'CLOSED'
            position['exit_price'] = exit_price
            position['exit_time'] = datetime.now()
            position['realized_pnl'] = realized_pnl
            
            # Record in history
            self.trading_history.append({
                'type': 'CLOSE',
                'position': position.copy(),
                'timestamp': datetime.now()
            })
            
            # Remove from active positions
            del self.positions[pair]
            
            # Determine close reason
            if position['action'] == 'BUY':
                if exit_price <= position['stop_loss']:
                    close_reason = 'Stop Loss'
                elif exit_price >= position['take_profit']:
                    close_reason = 'Take Profit'
                else:
                    close_reason = 'Manual'
            else:  # SELL
                if exit_price >= position['stop_loss']:
                    close_reason = 'Stop Loss'
                elif exit_price <= position['take_profit']:
                    close_reason = 'Take Profit'
                else:
                    close_reason = 'Manual'
            
            logger.info(f"Position closed: {pair} - {close_reason} - PnL: {realized_pnl:.2f}")
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
    
    def get_position_summary(self):
        """Get summary of current positions"""
        try:
            summary = {
                'total_positions': len(self.positions),
                'open_positions': [],
                'total_unrealized_pnl': 0,
                'total_realized_pnl': 0
            }
            
            for pair, position in self.positions.items():
                if position['status'] == 'OPEN':
                    summary['open_positions'].append(position.copy())
                    summary['total_unrealized_pnl'] += position['unrealized_pnl']
            
            # Calculate total realized PnL from history
            for trade in self.trading_history:
                if trade['type'] == 'CLOSE' and 'realized_pnl' in trade['position']:
                    summary['total_realized_pnl'] += trade['position']['realized_pnl']
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting position summary: {e}")
            return {'error': str(e)}
    
    def get_trading_statistics(self):
        """Get trading statistics"""
        try:
            stats = {
                'total_trades': len([t for t in self.trading_history if t['type'] == 'CLOSE']),
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0,
                'win_rate': 0,
                'average_win': 0,
                'average_loss': 0,
                'profit_factor': 0
            }
            
            wins = []
            losses = []
            
            for trade in self.trading_history:
                if trade['type'] == 'CLOSE' and 'realized_pnl' in trade['position']:
                    pnl = trade['position']['realized_pnl']
                    stats['total_pnl'] += pnl
                    
                    if pnl > 0:
                        stats['winning_trades'] += 1
                        wins.append(pnl)
                    elif pnl < 0:
                        stats['losing_trades'] += 1
                        losses.append(abs(pnl))
            
            # Calculate additional stats
            if wins:
                stats['average_win'] = np.mean(wins)
            if losses:
                stats['average_loss'] = np.mean(losses)
            
            if stats['total_trades'] > 0:
                stats['win_rate'] = (stats['winning_trades'] / stats['total_trades']) * 100
            
            if losses and wins:
                stats['profit_factor'] = sum(wins) / sum(losses)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating trading statistics: {e}")
            return {'error': str(e)}
