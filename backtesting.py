"""
Backtesting Module for BrayoForexBot
Tests trading strategies on historical data
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from market_data import MarketDataReader
from technical_analysis import TechnicalAnalysis
from trading_engine import TradingEngine
from risk_management import RiskManager
from config import Config
import logging

logger = logging.getLogger(__name__)

class Backtester:
    """Backtesting engine for trading strategies"""
    
    def __init__(self, initial_balance=10000):
        self.initial_balance = initial_balance
        self.market_data = MarketDataReader()
        self.technical_analysis = TechnicalAnalysis()
        self.trading_engine = TradingEngine()
        self.risk_manager = RiskManager(initial_balance)
        
    def run_backtest(self, pair, start_date, end_date, timeframe='1h'):
        """
        Run a backtest on historical data
        
        Args:
            pair (str): Currency pair
            start_date (str): Start date (YYYY-MM-DD)
            end_date (str): End date (YYYY-MM-DD)
            timeframe (str): Timeframe for analysis
            
        Returns:
            dict: Backtest results
        """
        try:
            logger.info(f"Starting backtest for {pair} from {start_date} to {end_date}")
            
            # Get historical data
            data = self._get_historical_data(pair, start_date, end_date, timeframe)
            if data.empty:
                return {'error': 'No historical data available'}
            
            # Calculate indicators
            data = self.technical_analysis.get_all_indicators(data)
            
            # Run backtest simulation
            results = self._simulate_trading(data, pair)
            
            # Calculate performance metrics
            metrics = self._calculate_performance_metrics(results)
            
            # Generate report
            report = {
                'pair': pair,
                'period': f"{start_date} to {end_date}",
                'timeframe': timeframe,
                'initial_balance': self.initial_balance,
                'final_balance': results['final_balance'],
                'total_trades': results['total_trades'],
                'winning_trades': results['winning_trades'],
                'losing_trades': results['losing_trades'],
                'metrics': metrics,
                'trades': results['trades'],
                'equity_curve': results['equity_curve'],
                'data_points': len(data)
            }
            
            logger.info(f"Backtest completed for {pair}: {metrics['total_return']:.2f}% return")
            return report
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return {'error': str(e)}
    
    def _get_historical_data(self, pair, start_date, end_date, timeframe):
        """Get historical data for backtesting"""
        try:
            # Calculate period for yfinance
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d')
            days_diff = (end - start).days
            
            # Map days to yfinance period
            if days_diff <= 7:
                period = '7d'
            elif days_diff <= 30:
                period = '1mo'
            elif days_diff <= 90:
                period = '3mo'
            elif days_diff <= 180:
                period = '6mo'
            elif days_diff <= 365:
                period = '1y'
            else:
                period = '2y'
            
            data = self.market_data.get_forex_data(pair, timeframe, period)
            
            # Filter by date range
            if not data.empty:
                data = data.loc[start:end]
            
            return data
            
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return pd.DataFrame()
    
    def _simulate_trading(self, data, pair):
        """Simulate trading on historical data"""
        try:
            # Initialize tracking variables
            balance = self.initial_balance
            positions = {}
            trades = []
            equity_curve = []
            
            for i in range(len(data)):
                current_data = data.iloc[:i+1]
                current_candle = data.iloc[i]
                current_time = current_candle.name
                
                # Update equity curve
                if positions:
                    unrealized_pnl = sum(pos['unrealized_pnl'] for pos in positions.values())
                    current_equity = balance + unrealized_pnl
                else:
                    current_equity = balance
                
                equity_curve.append({
                    'timestamp': current_time,
                    'equity': current_equity,
                    'balance': balance,
                    'open_positions': len(positions)
                })
                
                # Skip if not enough data for analysis
                if i < 50:  # Need minimum data for indicators
                    continue
                
                # Analyze signals
                signals = self.technical_analysis.analyze_signals(current_data)
                
                # Check for trading opportunities
                decision = self.trading_engine.analyze_trading_opportunity(
                    pair, current_data, signals
                )
                
                # Execute trade if signal is strong enough
                if decision['action'] in ['BUY', 'SELL']:
                    # Risk management check
                    risk_check = self.risk_manager.can_open_position(pair, decision['action'])
                    if risk_check['allowed']:
                        # Simulate trade execution
                        trade_result = self._simulate_trade_execution(decision, current_candle)
                        if trade_result['success']:
                            # Record position
                            position = {
                                'pair': pair,
                                'action': decision['action'],
                                'entry_price': decision['entry_price'],
                                'stop_loss': decision['stop_loss'],
                                'take_profit': decision['take_profit'],
                                'position_size': decision['position_size'],
                                'entry_time': current_time,
                                'status': 'OPEN'
                            }
                            positions[pair] = position
                
                # Manage existing positions
                self._manage_backtest_positions(positions, current_candle, trades, balance)
            
            # Close any remaining positions at the end
            if positions:
                for pair, pos in positions.items():
                    final_pnl = self._calculate_position_pnl(pos, current_candle['close'])
                    balance += final_pnl
                    trades.append({
                        'pair': pos['pair'],
                        'action': pos['action'],
                        'entry_price': pos['entry_price'],
                        'exit_price': current_candle['close'],
                        'entry_time': pos['entry_time'],
                        'exit_time': current_time,
                        'pnl': final_pnl,
                        'position_size': pos['position_size']
                    })
            
            # Calculate final statistics
            winning_trades = len([t for t in trades if t['pnl'] > 0])
            losing_trades = len([t for t in trades if t['pnl'] < 0])
            
            return {
                'final_balance': balance,
                'total_trades': len(trades),
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'trades': trades,
                'equity_curve': equity_curve
            }
            
        except Exception as e:
            logger.error(f"Error simulating trading: {e}")
            return {
                'final_balance': self.initial_balance,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'trades': [],
                'equity_curve': []
            }
    
    def _simulate_trade_execution(self, decision, current_candle):
        """Simulate trade execution"""
        try:
            return {
                'success': True,
                'order_id': f"BACKTEST_{int(datetime.now().timestamp())}",
                'executed_price': current_candle['close']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _manage_backtest_positions(self, positions, current_candle, trades, balance):
        """Manage positions during backtest"""
        try:
            current_price = current_candle['close']
            
            for pair, position in list(positions.items()):
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
                    # Close position
                    final_pnl = self._calculate_position_pnl(position, current_price)
                    balance += final_pnl
                    
                    # Record trade
                    trades.append({
                        'pair': position['pair'],
                        'action': position['action'],
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'entry_time': position['entry_time'],
                        'exit_time': current_candle.name,
                        'pnl': final_pnl,
                        'position_size': position['position_size']
                    })
                    
                    # Remove from positions
                    del positions[pair]
                    
        except Exception as e:
            logger.error(f"Error managing backtest positions: {e}")
    
    def _calculate_position_pnl(self, position, exit_price):
        """Calculate PnL for a closed position"""
        try:
            if position['action'] == 'BUY':
                return (exit_price - position['entry_price']) * position['position_size']
            else:  # SELL
                return (position['entry_price'] - exit_price) * position['position_size']
        except Exception as e:
            logger.error(f"Error calculating position PnL: {e}")
            return 0
    
    def _calculate_performance_metrics(self, results):
        """Calculate performance metrics"""
        try:
            trades = results['trades']
            equity_curve = results['equity_curve']
            
            if not trades:
                return {
                    'total_return': 0,
                    'total_return_pct': 0,
                    'win_rate': 0,
                    'average_win': 0,
                    'average_loss': 0,
                    'profit_factor': 0,
                    'max_drawdown': 0,
                    'max_drawdown_pct': 0,
                    'sharpe_ratio': 0,
                    'average_trade_duration': 0
                }
            
            # Basic metrics
            total_pnl = sum(t['pnl'] for t in trades)
            total_return_pct = (total_pnl / self.initial_balance) * 100
            
            # Win/Loss metrics
            wins = [t['pnl'] for t in trades if t['pnl'] > 0]
            losses = [abs(t['pnl']) for t in trades if t['pnl'] < 0]
            
            win_rate = (len(wins) / len(trades)) * 100 if trades else 0
            avg_win = np.mean(wins) if wins else 0
            avg_loss = np.mean(losses) if losses else 0
            
            # Profit factor
            total_wins = sum(wins)
            total_losses = sum(losses)
            profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
            
            # Drawdown
            max_drawdown, max_drawdown_pct = self._calculate_max_drawdown(equity_curve)
            
            # Sharpe ratio (simplified)
            returns = [t['pnl'] / self.initial_balance for t in trades]
            sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
            
            # Average trade duration
            durations = []
            for trade in trades:
                if 'entry_time' in trade and 'exit_time' in trade:
                    duration = (trade['exit_time'] - trade['entry_time']).total_seconds() / 3600  # hours
                    durations.append(duration)
            avg_duration = np.mean(durations) if durations else 0
            
            return {
                'total_return': total_pnl,
                'total_return_pct': total_return_pct,
                'win_rate': win_rate,
                'average_win': avg_win,
                'average_loss': avg_loss,
                'profit_factor': profit_factor,
                'max_drawdown': max_drawdown,
                'max_drawdown_pct': max_drawdown_pct,
                'sharpe_ratio': sharpe_ratio,
                'average_trade_duration': avg_duration
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {'error': str(e)}
    
    def _calculate_max_drawdown(self, equity_curve):
        """Calculate maximum drawdown"""
        try:
            if not equity_curve:
                return 0, 0
            
            equity_values = [point['equity'] for point in equity_curve]
            peak = equity_values[0]
            max_dd = 0
            max_dd_pct = 0
            
            for equity in equity_values:
                if equity > peak:
                    peak = equity
                
                drawdown = peak - equity
                drawdown_pct = (drawdown / peak) * 100 if peak > 0 else 0
                
                if drawdown > max_dd:
                    max_dd = drawdown
                    max_dd_pct = drawdown_pct
            
            return max_dd, max_dd_pct
            
        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0, 0
    
    def generate_backtest_report(self, results):
        """Generate a comprehensive backtest report"""
        try:
            report = f"""
# 📊 BACKTEST REPORT

## 📈 Summary
- **Pair:** {results['pair']}
- **Period:** {results['period']}
- **Timeframe:** {results['timeframe']}
- **Initial Balance:** ${results['initial_balance']:,.2f}
- **Final Balance:** ${results['final_balance']:,.2f}
- **Total Return:** {results['metrics']['total_return_pct']:.2f}%

## 📋 Trading Statistics
- **Total Trades:** {results['total_trades']}
- **Winning Trades:** {results['winning_trades']}
- **Losing Trades:** {results['losing_trades']}
- **Win Rate:** {results['metrics']['win_rate']:.1f}%

## 💰 Performance Metrics
- **Average Win:** ${results['metrics']['average_win']:.2f}
- **Average Loss:** ${results['metrics']['average_loss']:.2f}
- **Profit Factor:** {results['metrics']['profit_factor']:.2f}
- **Max Drawdown:** ${results['metrics']['max_drawdown']:.2f} ({results['metrics']['max_drawdown_pct']:.2f}%)
- **Sharpe Ratio:** {results['metrics']['sharpe_ratio']:.2f}
- **Avg Trade Duration:** {results['metrics']['average_trade_duration']:.1f} hours

## 📊 Risk Assessment
"""
            # Add risk assessment
            if results['metrics']['max_drawdown_pct'] > 20:
                report += "- ⚠️ **High Risk:** Maximum drawdown exceeds 20%\n"
            elif results['metrics']['max_drawdown_pct'] > 10:
                report += "- ⚡ **Medium Risk:** Maximum drawdown between 10-20%\n"
            else:
                report += "- ✅ **Low Risk:** Maximum drawdown below 10%\n"
            
            if results['metrics']['win_rate'] > 60:
                report += "- 🎯 **Excellent Win Rate:** Above 60%\n"
            elif results['metrics']['win_rate'] > 40:
                report += "- 📈 **Good Win Rate:** Between 40-60%\n"
            else:
                report += "- ⚠️ **Low Win Rate:** Below 40%\n"
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating backtest report: {e}")
            return f"Error generating report: {str(e)}"
    
    def plot_equity_curve(self, results, save_path=None):
        """Plot equity curve"""
        try:
            equity_curve = results['equity_curve']
            if not equity_curve:
                return None
            
            df = pd.DataFrame(equity_curve)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            plt.figure(figsize=(12, 6))
            plt.plot(df['timestamp'], df['equity'], label='Equity', linewidth=2)
            plt.fill_between(df['timestamp'], df['equity'], alpha=0.3)
            
            plt.title(f"Equity Curve - {results['pair']} ({results['period']})")
            plt.xlabel('Date')
            plt.ylabel('Equity ($)')
            plt.grid(True, alpha=0.3)
            plt.legend()
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Equity curve saved to {save_path}")
            
            return plt
            
        except Exception as e:
            logger.error(f"Error plotting equity curve: {e}")
            return None
    
    def compare_strategies(self, backtest_results):
        """Compare multiple backtest results"""
        try:
            comparison = pd.DataFrame()
            
            for i, result in enumerate(backtest_results):
                metrics = result['metrics']
                comparison.loc[i, 'Pair'] = result['pair']
                comparison.loc[i, 'Return %'] = metrics['total_return_pct']
                comparison.loc[i, 'Win Rate %'] = metrics['win_rate']
                comparison.loc[i, 'Profit Factor'] = metrics['profit_factor']
                comparison.loc[i, 'Max DD %'] = metrics['max_drawdown_pct']
                comparison.loc[i, 'Sharpe Ratio'] = metrics['sharpe_ratio']
                comparison.loc[i, 'Trades'] = result['total_trades']
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing strategies: {e}")
            return pd.DataFrame()
