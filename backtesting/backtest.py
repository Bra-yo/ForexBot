"""
PROPER Backtesting Engine for BrayoForexBot
This is the CRITICAL component we were missing!
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

class BacktestEngine:
    """
    Professional Backtesting Engine
    Tests strategies on historical data with proper simulation
    """
    
    def __init__(self, initial_balance: float = 10000):
        self.initial_balance = initial_balance
        self.balance = initial_balance
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.metrics = {}
        
    def run_backtest(self, 
                     data: pd.DataFrame, 
                     strategy_func,
                     commission: float = 0.0002,
                     slippage: float = 0.0001,
                     max_duration_minutes: float = None) -> Dict:
        """
        Run backtest on historical data
        
        Args:
            data: Historical OHLCV data
            strategy_func: Function that returns trading signals
            commission: Trading commission per trade
            slippage: Price slippage per trade
            max_duration_minutes: If set, force-close any position still open
                after this many minutes (matches a live time-based timeout,
                e.g. MultiPairLiveBot's MAX_TRADE_DURATION_MINUTES). None
                means no time-based exit - only stop_loss/take_profit.
            
        Returns:
            Backtest results dictionary
        """
        print(f"🔥 Starting backtest on {len(data)} candles...")
        
        # Reset state
        self.balance = self.initial_balance
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        
        # Process each candle
        for i in range(len(data)):
            current_candle = data.iloc[i]
            current_time = data.index[i]
            
            # Check exit conditions (stop_loss/take_profit/max duration) for
            # any already-open position BEFORE evaluating new signals - the
            # engine previously never did this at all, so every trade simply
            # rode from entry to the very last candle of the whole dataset
            # regardless of its stop_loss/take_profit, which made results
            # meaningless (one trade, "held" for however long the remaining
            # data happened to span).
            self._check_exit_conditions(current_candle, current_time, slippage, max_duration_minutes)
            
            # Get strategy signal
            signal = strategy_func(data.iloc[:i+1])
            
            # Execute trades based on signal
            self._execute_signal(signal, current_candle, commission, slippage)
            
            # Update equity curve
            self._update_equity_curve(current_time, current_candle)
        
        # Close all positions at the end
        self._close_all_positions(data.iloc[-1], slippage)
        
        # Calculate metrics
        self._calculate_metrics()
        
        return self._get_results()
    
    def _check_exit_conditions(self, candle: pd.Series, current_time, slippage: float, max_duration_minutes: float = None):
        """
        Check every open position against its stop_loss/take_profit (using
        this candle's high/low, since price can touch a level intra-candle
        even if the close doesn't) and, if given, a max holding duration.
        If both stop_loss and take_profit are within this candle's range,
        assume stop_loss was hit first - the standard conservative
        assumption when candle-level (not tick-level) data can't tell you
        the actual intra-candle path.
        """
        for pair, pos in list(self.positions.items()):
            exit_price = None
            reason = None

            if pos['action'] == 'BUY':
                sl_hit = candle['low'] <= pos['stop_loss']
                tp_hit = candle['high'] >= pos['take_profit']
                if sl_hit:
                    exit_price, reason = pos['stop_loss'], 'stop_loss'
                elif tp_hit:
                    exit_price, reason = pos['take_profit'], 'take_profit'
            else:  # SELL
                sl_hit = candle['high'] >= pos['stop_loss']
                tp_hit = candle['low'] <= pos['take_profit']
                if sl_hit:
                    exit_price, reason = pos['stop_loss'], 'stop_loss'
                elif tp_hit:
                    exit_price, reason = pos['take_profit'], 'take_profit'

            if exit_price is None and max_duration_minutes is not None:
                held_minutes = (current_time - pos['entry_time']).total_seconds() / 60.0
                if held_minutes >= max_duration_minutes:
                    exit_price, reason = candle['close'], 'max_duration'

            if exit_price is not None:
                self._close_position(pair, exit_price, current_time, slippage, reason)

    def _close_position(self, pair: str, exit_price: float, exit_time, slippage: float, reason: str):
        """Close a single open position and record the trade."""
        pos = self.positions.pop(pair)
        exit_price = exit_price * (1 - slippage if pos['action'] == 'BUY' else 1 + slippage)

        if pos['action'] == 'BUY':
            pnl = (exit_price - pos['entry_price']) * pos['size']
        else:
            pnl = (pos['entry_price'] - exit_price) * pos['size']

        # Net commission out of the recorded P&L (commission was already
        # deducted from self.balance once, at open time, in _execute_signal -
        # this does NOT double-charge it, it just makes the *recorded* pnl
        # match what actually happened to the account, instead of every
        # downstream metric silently ignoring commission entirely).
        net_pnl = pnl - pos['commission']

        self.trades.append({
            'pair': pair,
            'action': pos['action'],
            'entry_price': pos['entry_price'],
            'exit_price': exit_price,
            'entry_time': pos['entry_time'],
            'exit_time': exit_time,
            'size': pos['size'],
            'pnl': net_pnl,
            'commission': pos['commission'],
            'exit_reason': reason,
            'duration': (exit_time - pos['entry_time']).total_seconds() / 3600,  # hours
        })
        self.balance += pnl

    def _execute_signal(self, signal: Dict, candle: pd.Series, commission: float, slippage: float):
        """Execute trading signal"""
        action = signal.get('action', 'WAIT')
        
        if action == 'WAIT':
            return
        
        pair = signal.get('pair', 'DEFAULT')
        
        # Check if we already have position
        if pair in self.positions:
            return
        
        # Calculate position size (2% risk)
        risk_amount = self.balance * 0.02
        stop_loss = signal.get('stop_loss', candle['close'] * 0.99)
        entry_price = candle['close'] * (1 + slippage if action == 'BUY' else 1 - slippage)
        
        # Position sizing
        if action == 'BUY':
            position_size = risk_amount / abs(entry_price - stop_loss)
        else:
            position_size = risk_amount / abs(stop_loss - entry_price)
        
        # Apply commission
        trade_cost = position_size * entry_price * commission
        
        if trade_cost > self.balance:
            return  # Not enough balance
        
        # Open position
        self.positions[pair] = {
            'action': action,
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': signal.get('take_profit', entry_price * 1.02 if action == 'BUY' else entry_price * 0.98),
            'size': position_size,
            'entry_time': candle.name,
            'commission': trade_cost
        }
        
        # Update balance
        self.balance -= trade_cost
    
    def _update_equity_curve(self, time, candle):
        """Update equity curve"""
        equity = self.balance
        
        # Add unrealized P&L from open positions
        for pair, pos in self.positions.items():
            if pos['action'] == 'BUY':
                unrealized = (candle['close'] - pos['entry_price']) * pos['size']
            else:
                unrealized = (pos['entry_price'] - candle['close']) * pos['size']
            equity += unrealized
        
        self.equity_curve.append({
            'time': time,
            'equity': equity,
            'balance': self.balance,
            'open_positions': len(self.positions)
        })
    
    def _close_all_positions(self, last_candle: pd.Series, slippage: float):
        """Close all positions at the end"""
        for pair, pos in list(self.positions.items()):
            exit_price = last_candle['close'] * (1 - slippage if pos['action'] == 'BUY' else 1 + slippage)
            
            # Calculate P&L
            if pos['action'] == 'BUY':
                pnl = (exit_price - pos['entry_price']) * pos['size']
            else:
                pnl = (pos['entry_price'] - exit_price) * pos['size']

            # Same commission fix as _close_position(): commission was
            # already deducted from self.balance at open time, so record the
            # NET pnl (matching what actually happened to the account)
            # rather than the raw pre-commission figure every metric was
            # silently being computed from.
            net_pnl = pnl - pos['commission']

            # Record trade
            self.trades.append({
                'pair': pair,
                'action': pos['action'],
                'entry_price': pos['entry_price'],
                'exit_price': exit_price,
                'entry_time': pos['entry_time'],
                'exit_time': last_candle.name,
                'size': pos['size'],
                'pnl': net_pnl,
                'commission': pos['commission'],
                'exit_reason': 'end_of_data',
                'duration': (last_candle.name - pos['entry_time']).total_seconds() / 3600  # hours
            })
            
            # Update balance
            self.balance += pnl
        
        self.positions.clear()
    
    def _calculate_metrics(self):
        """Calculate performance metrics"""
        if not self.trades:
            self.metrics = {
                'total_return': 0,
                'total_return_pct': 0,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'profit_factor': 0,
                'max_drawdown': 0,
                'max_drawdown_pct': 0,
                'sharpe_ratio': 0,
                'avg_trade_duration': 0
            }
            return
        
        # Basic metrics
        total_pnl = sum(t['pnl'] for t in self.trades)
        total_return_pct = (total_pnl / self.initial_balance) * 100

        # Cross-check against the real account balance rather than trusting
        # this sum blindly - this is exactly the kind of mismatch that went
        # undetected all session (commission deducted from self.balance at
        # open, but never netted into the recorded pnl, so every printed
        # "Total Return" was wrong while the balance itself was fine).
        actual_return = self.balance - self.initial_balance
        if abs(total_pnl - actual_return) > 0.01:
            print(f"⚠️ WARNING: sum(trade pnl)=${total_pnl:.2f} does not match "
                  f"actual balance change=${actual_return:.2f} (diff=${total_pnl - actual_return:.2f}). "
                  f"Using the real balance-based figure for Total Return - "
                  f"this mismatch means something else isn't accounting for "
                  f"P&L correctly and is worth investigating.")
            total_pnl = actual_return
            total_return_pct = (total_pnl / self.initial_balance) * 100
        
        # Win/Loss analysis
        wins = [t['pnl'] for t in self.trades if t['pnl'] > 0]
        losses = [abs(t['pnl']) for t in self.trades if t['pnl'] < 0]
        
        win_rate = (len(wins) / len(self.trades)) * 100
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        # Profit factor
        total_wins = sum(wins)
        total_losses = sum(losses)
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Drawdown
        max_dd, max_dd_pct = self._calculate_drawdown()
        
        # Sharpe ratio
        returns = [t['pnl'] / self.initial_balance for t in self.trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        # Average trade duration
        avg_duration = np.mean([t['duration'] for t in self.trades]) if self.trades else 0
        
        self.metrics = {
            'total_return': total_pnl,
            'total_return_pct': total_return_pct,
            'total_trades': len(self.trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown': max_dd,
            'max_drawdown_pct': max_dd_pct,
            'sharpe_ratio': sharpe_ratio,
            'avg_trade_duration': avg_duration
        }
    
    def _calculate_drawdown(self) -> Tuple[float, float]:
        """Calculate maximum drawdown"""
        if not self.equity_curve:
            return 0, 0
        
        equity_values = [point['equity'] for point in self.equity_curve]
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
    
    def _get_results(self) -> Dict:
        """Get backtest results"""
        return {
            'initial_balance': self.initial_balance,
            'final_balance': self.balance,
            'metrics': self.metrics,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
    
    def plot_results(self, results: Dict, save_path: Optional[str] = None):
        """Plot backtest results"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Backtest Results', fontsize=16)
        
        # Equity Curve
        if results['equity_curve']:
            equity_df = pd.DataFrame(results['equity_curve'])
            equity_df['time'] = pd.to_datetime(equity_df['time'])
            
            axes[0, 0].plot(equity_df['time'], equity_df['equity'], linewidth=2)
            axes[0, 0].set_title('Equity Curve')
            axes[0, 0].set_ylabel('Equity ($)')
            axes[0, 0].grid(True, alpha=0.3)
        
        # Trade Distribution
        if results['trades']:
            trade_pnls = [t['pnl'] for t in results['trades']]
            axes[0, 1].hist(trade_pnls, bins=30, alpha=0.7, edgecolor='black')
            axes[0, 1].set_title('Trade P&L Distribution')
            axes[0, 1].set_xlabel('Profit/Loss ($)')
            axes[0, 1].set_ylabel('Frequency')
            axes[0, 1].grid(True, alpha=0.3)
        
        # Cumulative Returns
        if results['trades']:
            cumulative_returns = np.cumsum([t['pnl'] for t in results['trades']])
            axes[1, 0].plot(cumulative_returns, linewidth=2)
            axes[1, 0].set_title('Cumulative Returns')
            axes[1, 0].set_xlabel('Trade Number')
            axes[1, 0].set_ylabel('Cumulative P&L ($)')
            axes[1, 0].grid(True, alpha=0.3)
        
        # Metrics Summary
        metrics = results['metrics']
        metrics_text = f"""
        Total Return: {metrics['total_return_pct']:.2f}%
        Win Rate: {metrics['win_rate']:.1f}%
        Profit Factor: {metrics['profit_factor']:.2f}
        Max Drawdown: {metrics['max_drawdown_pct']:.2f}%
        Sharpe Ratio: {metrics['sharpe_ratio']:.2f}
        Total Trades: {metrics['total_trades']}
        """
        axes[1, 1].text(0.1, 0.5, metrics_text, fontsize=12, verticalalignment='center')
        axes[1, 1].set_title('Performance Metrics')
        axes[1, 1].axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            plt.close()  # Never call show() when saving to a file - this was
            # blocking indefinitely on plt.show()'s Tkinter mainloop with
            # nobody there to close the popup window, in a script meant to
            # run multiple backtests back-to-back unattended. That's why
            # the M15/M30/H1 comparison run appeared to hang after M15 -
            # it wasn't stuck, it was waiting for a window nobody knew existed.
        else:
            plt.show()
    
    def print_summary(self, results: Dict):
        """Print backtest summary"""
        metrics = results['metrics']
        
        print("\n" + "="*60)
        print("🔥 BACKTEST RESULTS SUMMARY")
        print("="*60)
        print(f"💰 Initial Balance: ${results['initial_balance']:,.2f}")
        print(f"💰 Final Balance: ${results['final_balance']:,.2f}")
        print(f"📈 Total Return: {metrics['total_return_pct']:.2f}%")
        print(f"📊 Total Trades: {metrics['total_trades']}")
        print(f"🎯 Win Rate: {metrics['win_rate']:.1f}%")
        print(f"💵 Average Win: ${metrics['avg_win']:.2f}")
        print(f"💸 Average Loss: ${metrics['avg_loss']:.2f}")
        print(f"⚖️ Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"📉 Max Drawdown: {metrics['max_drawdown_pct']:.2f}%")
        print(f"📈 Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"⏱️ Avg Trade Duration: {metrics['avg_trade_duration']:.1f} hours")
        print("="*60)


# Example strategy function
def simple_rsi_strategy(data: pd.DataFrame) -> Dict:
    """
    Simple RSI strategy for testing
    """
    if len(data) < 20:
        return {'action': 'WAIT'}
    
    # Calculate RSI
    close = data['close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    current_rsi = rsi.iloc[-1]
    current_price = close.iloc[-1]
    
    # Generate signals
    if current_rsi < 30:  # Oversold
        return {
            'action': 'BUY',
            'pair': 'TEST',
            'stop_loss': current_price * 0.98,
            'take_profit': current_price * 1.02
        }
    elif current_rsi > 70:  # Overbought
        return {
            'action': 'SELL',
            'pair': 'TEST',
            'stop_loss': current_price * 1.02,
            'take_profit': current_price * 0.98
        }
    else:
        return {'action': 'WAIT'}