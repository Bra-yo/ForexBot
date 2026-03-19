"""
Risk Management Module for BrayoForexBot
Handles position sizing, risk limits, and money management
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import Config
import logging

logger = logging.getLogger(__name__)

class RiskManager:
    """Risk management and position sizing"""
    
    def __init__(self, account_balance=10000):
        self.account_balance = account_balance
        self.risk_per_trade = Config.RISK_PERCENTAGE / 100
        self.max_positions = Config.MAX_POSITIONS
        self.daily_loss_limit = account_balance * 0.05  # 5% daily loss limit
        self.max_risk_per_pair = account_balance * 0.02  # 2% max risk per pair
        self.daily_pnl = 0
        self.trades_today = 0
        self.last_trade_date = None
        self.pair_exposure = {}  # Track exposure per currency pair
        
    def can_open_position(self, pair, signal):
        """
        Check if we can open a new position based on risk rules
        
        Args:
            pair (str): Currency pair
            signal (str): Trading signal (BUY/SELL)
            
        Returns:
            dict: Risk check result
        """
        try:
            result = {
                'allowed': True,
                'reasons': []
            }
            
            # Check daily loss limit
            if self.daily_pnl < -self.daily_loss_limit:
                result['allowed'] = False
                result['reasons'].append(f'Daily loss limit exceeded: {self.daily_pnl:.2f}')
                return result
            
            # Check max positions
            if self.max_positions <= 0:
                result['allowed'] = False
                result['reasons'].append('Maximum positions limit reached')
                return result
            
            # Check pair exposure
            current_exposure = self.pair_exposure.get(pair, 0)
            if current_exposure >= self.max_risk_per_pair:
                result['allowed'] = False
                result['reasons'].append(f'Maximum exposure for {pair} reached')
                return result
            
            # Check if we're already in this pair
            if pair in self.pair_exposure and self.pair_exposure[pair] > 0:
                result['allowed'] = False
                result['reasons'].append(f'Already have position in {pair}')
                return result
            
            # Check account balance
            if self.account_balance <= 0:
                result['allowed'] = False
                result['reasons'].append('Insufficient account balance')
                return result
            
            return result
            
        except Exception as e:
            logger.error(f"Error in risk check: {e}")
            return {'allowed': False, 'reasons': [f"Risk check error: {str(e)}"]}
    
    def calculate_position_size(self, pair, entry_price, stop_loss, signal):
        """
        Calculate optimal position size based on risk management rules
        
        Args:
            pair (str): Currency pair
            entry_price (float): Entry price
            stop_loss (float): Stop loss price
            signal (str): Trading signal
            
        Returns:
            float: Position size in lots
        """
        try:
            # Calculate risk amount in dollars
            risk_amount = self.account_balance * self.risk_per_trade
            
            # Calculate pip distance to stop loss
            if signal == 'BUY':
                pip_distance = abs(entry_price - stop_loss)
            else:  # SELL
                pip_distance = abs(stop_loss - entry_price)
            
            if pip_distance == 0:
                logger.warning(f"Zero pip distance for {pair}")
                return 0.01  # Minimum position
            
            # For forex, 1 pip = 0.0001 for most pairs, 0.01 for JPY pairs
            if 'JPY' in pair:
                pip_value = 0.01
            else:
                pip_value = 0.0001
            
            # Calculate position size (in lots)
            # Position size = Risk Amount / (Pip Distance * Pip Value * 10000)
            position_size = risk_amount / (pip_distance * pip_value * 10000)
            
            # Apply position size limits
            max_position = self.account_balance * 0.1  # Max 10% of account per trade
            position_size = min(position_size, max_position)
            
            # Minimum position size
            position_size = max(position_size, 0.01)
            
            # Round to 2 decimal places
            position_size = round(position_size, 2)
            
            logger.info(f"Position size calculated for {pair}: {position_size} lots (Risk: ${risk_amount:.2f})")
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.01  # Return minimum position on error
    
    def update_daily_stats(self, pnl):
        """
        Update daily P&L and trade statistics
        
        Args:
            pnl (float): Profit/Loss from closed trade
        """
        try:
            today = datetime.now().date()
            
            # Reset daily stats if it's a new day
            if self.last_trade_date != today:
                self.daily_pnl = 0
                self.trades_today = 0
                self.last_trade_date = today
                logger.info("Daily trading statistics reset")
            
            self.daily_pnl += pnl
            self.trades_today += 1
            
            logger.info(f"Daily P&L updated: ${self.daily_pnl:.2f} ({self.trades_today} trades)")
            
        except Exception as e:
            logger.error(f"Error updating daily stats: {e}")
    
    def update_pair_exposure(self, pair, exposure_change):
        """
        Update exposure for a specific currency pair
        
        Args:
            pair (str): Currency pair
            exposure_change (float): Change in exposure (positive for opening, negative for closing)
        """
        try:
            current_exposure = self.pair_exposure.get(pair, 0)
            new_exposure = current_exposure + exposure_change
            
            if new_exposure <= 0:
                # Remove pair from exposure tracking if no exposure
                if pair in self.pair_exposure:
                    del self.pair_exposure[pair]
            else:
                self.pair_exposure[pair] = new_exposure
            
            logger.debug(f"Exposure updated for {pair}: {current_exposure:.2f} -> {new_exposure:.2f}")
            
        except Exception as e:
            logger.error(f"Error updating pair exposure: {e}")
    
    def get_risk_metrics(self):
        """
        Get current risk metrics and status
        
        Returns:
            dict: Risk metrics
        """
        try:
            metrics = {
                'account_balance': self.account_balance,
                'daily_pnl': self.daily_pnl,
                'daily_loss_limit': self.daily_loss_limit,
                'daily_loss_used': abs(self.daily_pnl) / self.daily_loss_limit * 100 if self.daily_pnl < 0 else 0,
                'trades_today': self.trades_today,
                'max_positions': self.max_positions,
                'risk_per_trade': self.risk_per_trade * 100,
                'total_exposure': sum(self.pair_exposure.values()),
                'pair_exposure': self.pair_exposure.copy(),
                'risk_status': 'HEALTHY'
            }
            
            # Determine risk status
            if metrics['daily_loss_used'] > 80:
                metrics['risk_status'] = 'HIGH_RISK'
            elif metrics['daily_loss_used'] > 50:
                metrics['risk_status'] = 'MEDIUM_RISK'
            elif metrics['total_exposure'] > self.account_balance * 0.5:
                metrics['risk_status'] = 'HIGH_EXPOSURE'
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error getting risk metrics: {e}")
            return {'error': str(e)}
    
    def should_stop_trading(self):
        """
        Check if trading should be stopped based on risk rules
        
        Returns:
            tuple: (should_stop, reason)
        """
        try:
            # Check daily loss limit
            if self.daily_pnl < -self.daily_loss_limit:
                return True, f"Daily loss limit exceeded: ${self.daily_pnl:.2f}"
            
            # Check account balance
            if self.account_balance <= 0:
                return True, "Account balance depleted"
            
            # Check if we've lost too much of the account
            if self.daily_pnl < -self.account_balance * 0.1:
                return True, f"10% account loss reached: ${self.daily_pnl:.2f}"
            
            return False, ""
            
        except Exception as e:
            logger.error(f"Error checking trading stop condition: {e}")
            return False, f"Error: {str(e)}"
    
    def calculate_portfolio_risk(self, positions):
        """
        Calculate overall portfolio risk
        
        Args:
            positions (dict): Current positions
            
        Returns:
            dict: Portfolio risk metrics
        """
        try:
            portfolio_risk = {
                'total_positions': len(positions),
                'total_risk_amount': 0,
                'max_single_loss': 0,
                'correlation_risk': 'LOW',
                'risk_score': 0
            }
            
            for pair, position in positions.items():
                if position['status'] == 'OPEN':
                    # Calculate potential loss for this position
                    if position['action'] == 'BUY':
                        potential_loss = (position['entry_price'] - position['stop_loss']) * position['position_size']
                    else:  # SELL
                        potential_loss = (position['stop_loss'] - position['entry_price']) * position['position_size']
                    
                    portfolio_risk['total_risk_amount'] += potential_loss
                    portfolio_risk['max_single_loss'] = max(portfolio_risk['max_single_loss'], potential_loss)
            
            # Calculate risk score (0-100)
            if self.account_balance > 0:
                risk_percentage = (portfolio_risk['total_risk_amount'] / self.account_balance) * 100
                portfolio_risk['risk_score'] = min(risk_percentage * 2, 100)  # Scale and cap at 100
            
            # Determine correlation risk (simplified)
            if portfolio_risk['total_positions'] > 3:
                portfolio_risk['correlation_risk'] = 'MEDIUM'
            if portfolio_risk['total_positions'] > 5:
                portfolio_risk['correlation_risk'] = 'HIGH'
            
            return portfolio_risk
            
        except Exception as e:
            logger.error(f"Error calculating portfolio risk: {e}")
            return {'error': str(e)}
    
    def adjust_risk_parameters(self, recent_performance):
        """
        Adjust risk parameters based on recent performance
        
        Args:
            recent_performance (dict): Recent trading performance metrics
        """
        try:
            win_rate = recent_performance.get('win_rate', 50)
            avg_win = recent_performance.get('average_win', 0)
            avg_loss = recent_performance.get('average_loss', 0)
            
            # Adjust risk based on performance
            if win_rate > 60 and avg_win > avg_loss:
                # Good performance - can increase risk slightly
                new_risk = min(self.risk_per_trade * 1.1, 0.05)  # Max 5% per trade
                logger.info(f"Increasing risk per trade to {new_risk*100:.1f}% based on good performance")
            elif win_rate < 40 or (avg_loss > 0 and avg_win / avg_loss < 1):
                # Poor performance - reduce risk
                new_risk = max(self.risk_per_trade * 0.8, 0.01)  # Min 1% per trade
                logger.info(f"Reducing risk per trade to {new_risk*100:.1f}% based on poor performance")
            else:
                # Stable performance - keep current risk
                logger.info("Maintaining current risk parameters")
            
        except Exception as e:
            logger.error(f"Error adjusting risk parameters: {e}")
