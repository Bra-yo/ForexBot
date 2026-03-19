"""
Performance Metrics Module for BrayoForexBot
Measures what actually matters in trading performance
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

class PerformanceMetrics:
    """
    Comprehensive Performance Analysis
    Goes beyond basic win/loss to real trading metrics
    """
    
    def __init__(self):
        self.metrics_cache = {}
    
    def calculate_all_metrics(self, trades: List[Dict], equity_curve: List[Dict], 
                            initial_balance: float) -> Dict:
        """
        Calculate comprehensive performance metrics
        
        Args:
            trades: List of completed trades
            equity_curve: Equity curve data
            initial_balance: Starting account balance
            
        Returns:
            Complete metrics dictionary
        """
        if not trades:
            return self._empty_metrics()
        
        # Basic metrics
        basic_metrics = self._calculate_basic_metrics(trades, initial_balance)
        
        # Risk metrics
        risk_metrics = self._calculate_risk_metrics(trades, equity_curve, initial_balance)
        
        # Consistency metrics
        consistency_metrics = self._calculate_consistency_metrics(trades)
        
        # Time-based metrics
        time_metrics = self._calculate_time_metrics(trades)
        
        # Advanced metrics
        advanced_metrics = self._calculate_advanced_metrics(trades, equity_curve, initial_balance)
        
        # Combine all metrics
        all_metrics = {
            **basic_metrics,
            **risk_metrics,
            **consistency_metrics,
            **time_metrics,
            **advanced_metrics
        }
        
        # Performance rating
        all_metrics['performance_rating'] = self._calculate_performance_rating(all_metrics)
        
        return all_metrics
    
    def _empty_metrics(self) -> Dict:
        """Return empty metrics structure"""
        return {
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
            'sortino_ratio': 0,
            'calmar_ratio': 0,
            'avg_trade_duration': 0,
            'best_trade': 0,
            'worst_trade': 0,
            'largest_win_streak': 0,
            'largest_loss_streak': 0,
            'recovery_factor': 0,
            'var_95': 0,
            'performance_rating': 'NO_DATA'
        }
    
    def _calculate_basic_metrics(self, trades: List[Dict], initial_balance: float) -> Dict:
        """Calculate basic performance metrics"""
        total_pnl = sum(t['pnl'] for t in trades)
        total_return_pct = (total_pnl / initial_balance) * 100
        
        # Win/Loss analysis
        wins = [t['pnl'] for t in trades if t['pnl'] > 0]
        losses = [abs(t['pnl']) for t in trades if t['pnl'] < 0]
        
        win_rate = (len(wins) / len(trades)) * 100 if trades else 0
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        # Profit factor
        total_wins = sum(wins)
        total_losses = sum(losses)
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Best/Worst trades
        best_trade = max(wins) if wins else 0
        worst_trade = -min(losses) if losses else 0
        
        return {
            'total_return': total_pnl,
            'total_return_pct': total_return_pct,
            'total_trades': len(trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'best_trade': best_trade,
            'worst_trade': worst_trade
        }
    
    def _calculate_risk_metrics(self, trades: List[Dict], equity_curve: List[Dict], 
                              initial_balance: float) -> Dict:
        """Calculate risk-related metrics"""
        # Drawdown
        max_dd, max_dd_pct = self._calculate_max_drawdown(equity_curve)
        
        # Sharpe ratio
        returns = [t['pnl'] / initial_balance for t in trades]
        sharpe_ratio = np.mean(returns) / np.std(returns) if np.std(returns) > 0 else 0
        
        # Sortino ratio (downside deviation only)
        negative_returns = [r for r in returns if r < 0]
        downside_deviation = np.std(negative_returns) if negative_returns else 0
        sortino_ratio = np.mean(returns) / downside_deviation if downside_deviation > 0 else 0
        
        # Calmar ratio (return / max drawdown)
        calmar_ratio = (sum(returns) / len(returns) * 252) / (max_dd_pct / 100) if max_dd_pct > 0 else 0
        
        # Value at Risk (95%)
        var_95 = np.percentile(returns, 5) if returns else 0
        
        # Recovery factor
        recovery_factor = sum(returns) / abs(max_dd_pct / 100) if max_dd_pct > 0 else 0
        
        return {
            'max_drawdown': max_dd,
            'max_drawdown_pct': max_dd_pct,
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'var_95': var_95,
            'recovery_factor': recovery_factor
        }
    
    def _calculate_consistency_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate consistency metrics"""
        if not trades:
            return {
                'largest_win_streak': 0,
                'largest_loss_streak': 0,
                'avg_win_streak': 0,
                'avg_loss_streak': 0,
                'consistency_score': 0
            }
        
        # Calculate streaks
        win_streaks = []
        loss_streaks = []
        current_win_streak = 0
        current_loss_streak = 0
        
        for trade in trades:
            if trade['pnl'] > 0:
                current_win_streak += 1
                if current_loss_streak > 0:
                    loss_streaks.append(current_loss_streak)
                    current_loss_streak = 0
            else:
                current_loss_streak += 1
                if current_win_streak > 0:
                    win_streaks.append(current_win_streak)
                    current_win_streak = 0
        
        # Don't forget the last streak
        if current_win_streak > 0:
            win_streaks.append(current_win_streak)
        if current_loss_streak > 0:
            loss_streaks.append(current_loss_streak)
        
        largest_win_streak = max(win_streaks) if win_streaks else 0
        largest_loss_streak = max(loss_streaks) if loss_streaks else 0
        avg_win_streak = np.mean(win_streaks) if win_streaks else 0
        avg_loss_streak = np.mean(loss_streaks) if loss_streaks else 0
        
        # Consistency score (lower is better for loss streaks, higher for win streaks)
        consistency_score = (largest_win_streak - largest_loss_streak) / max(largest_win_streak + largest_loss_streak, 1)
        
        return {
            'largest_win_streak': largest_win_streak,
            'largest_loss_streak': largest_loss_streak,
            'avg_win_streak': avg_win_streak,
            'avg_loss_streak': avg_loss_streak,
            'consistency_score': consistency_score
        }
    
    def _calculate_time_metrics(self, trades: List[Dict]) -> Dict:
        """Calculate time-based metrics"""
        if not trades:
            return {
                'avg_trade_duration': 0,
                'longest_trade': 0,
                'shortest_trade': 0,
                'trades_per_month': 0
            }
        
        durations = [t.get('duration', 0) for t in trades]
        avg_duration = np.mean(durations)
        longest_trade = max(durations)
        shortest_trade = min(durations)
        
        # Calculate trading frequency
        if len(trades) > 1:
            first_trade = min(t.get('entry_time', datetime.now()) for t in trades)
            last_trade = max(t.get('exit_time', datetime.now()) for t in trades)
            months = (last_trade - first_trade).days / 30.44
            trades_per_month = len(trades) / max(months, 1)
        else:
            trades_per_month = 0
        
        return {
            'avg_trade_duration': avg_duration,
            'longest_trade': longest_trade,
            'shortest_trade': shortest_trade,
            'trades_per_month': trades_per_month
        }
    
    def _calculate_advanced_metrics(self, trades: List[Dict], equity_curve: List[Dict], 
                                  initial_balance: float) -> Dict:
        """Calculate advanced metrics"""
        if not trades:
            return {
                'expectancy': 0,
                'kelly_criterion': 0,
                'roi_per_trade': 0,
                'monthly_compound_return': 0
            }
        
        # Expectancy (average profit/loss per trade)
        expectancy = np.mean([t['pnl'] for t in trades])
        
        # Kelly Criterion (optimal position size)
        wins = [t['pnl'] for t in trades if t['pnl'] > 0]
        losses = [abs(t['pnl']) for t in trades if t['pnl'] < 0]
        
        win_rate = len(wins) / len(trades)
        avg_win = np.mean(wins) if wins else 0
        avg_loss = np.mean(losses) if losses else 0
        
        kelly_criterion = win_rate - ((1 - win_rate) / (avg_win / avg_loss)) if avg_loss > 0 else 0
        
        # ROI per trade
        roi_per_trade = expectancy / initial_balance * 100
        
        # Monthly compound return
        if equity_curve and len(equity_curve) > 1:
            first_equity = equity_curve[0]['equity']
            last_equity = equity_curve[-1]['equity']
            months = len(equity_curve) / (30 * 24)  # Assuming hourly data
            monthly_compound_return = (last_equity / first_equity) ** (1/months) - 1 if months > 0 else 0
        else:
            monthly_compound_return = 0
        
        return {
            'expectancy': expectancy,
            'kelly_criterion': kelly_criterion,
            'roi_per_trade': roi_per_trade,
            'monthly_compound_return': monthly_compound_return
        }
    
    def _calculate_max_drawdown(self, equity_curve: List[Dict]) -> Tuple[float, float]:
        """Calculate maximum drawdown"""
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
    
    def _calculate_performance_rating(self, metrics: Dict) -> str:
        """Calculate overall performance rating"""
        score = 0
        
        # Return score (30%)
        if metrics['total_return_pct'] > 20:
            score += 30
        elif metrics['total_return_pct'] > 10:
            score += 20
        elif metrics['total_return_pct'] > 0:
            score += 10
        
        # Win rate score (20%)
        if metrics['win_rate'] > 60:
            score += 20
        elif metrics['win_rate'] > 50:
            score += 15
        elif metrics['win_rate'] > 40:
            score += 10
        
        # Risk score (25%)
        if metrics['max_drawdown_pct'] < 5:
            score += 25
        elif metrics['max_drawdown_pct'] < 10:
            score += 20
        elif metrics['max_drawdown_pct'] < 20:
            score += 15
        
        # Sharpe ratio score (15%)
        if metrics['sharpe_ratio'] > 2:
            score += 15
        elif metrics['sharpe_ratio'] > 1:
            score += 10
        elif metrics['sharpe_ratio'] > 0.5:
            score += 5
        
        # Profit factor score (10%)
        if metrics['profit_factor'] > 2:
            score += 10
        elif metrics['profit_factor'] > 1.5:
            score += 7
        elif metrics['profit_factor'] > 1:
            score += 5
        
        # Determine rating
        if score >= 80:
            return 'EXCELLENT'
        elif score >= 60:
            return 'GOOD'
        elif score >= 40:
            return 'AVERAGE'
        elif score >= 20:
            return 'POOR'
        else:
            return 'VERY_POOR'
    
    def generate_report(self, metrics: Dict) -> str:
        """Generate comprehensive performance report"""
        rating_emoji = {
            'EXCELLENT': '🏆',
            'GOOD': '🌟',
            'AVERAGE': '📊',
            'POOR': '⚠️',
            'VERY_POOR': '❌',
            'NO_DATA': '📝'
        }
        
        emoji = rating_emoji.get(metrics['performance_rating'], '📊')
        
        report = f"""
{emoji} PERFORMANCE ANALYSIS REPORT
{'='*50}

📈 RETURNS & PROFITABILITY
• Total Return: {metrics['total_return_pct']:.2f}%
• Total Trades: {metrics['total_trades']}
• Win Rate: {metrics['win_rate']:.1f}%
• Profit Factor: {metrics['profit_factor']:.2f}
• Expectancy: ${metrics['expectancy']:.2f} per trade

🎯 BEST & WORST
• Best Trade: ${metrics['best_trade']:.2f}
• Worst Trade: ${metrics['worst_trade']:.2f}
• Average Win: ${metrics['avg_win']:.2f}
• Average Loss: ${metrics['avg_loss']:.2f}

⚠️ RISK METRICS
• Max Drawdown: {metrics['max_drawdown_pct']:.2f}%
• Sharpe Ratio: {metrics['sharpe_ratio']:.2f}
• Sortino Ratio: {metrics['sortino_ratio']:.2f}
• Value at Risk (95%): {metrics['var_95']*100:.2f}%

📊 CONSISTENCY
• Largest Win Streak: {metrics['largest_win_streak']}
• Largest Loss Streak: {metrics['largest_loss_streak']}
• Consistency Score: {metrics['consistency_score']:.2f}

⏱️ TIME ANALYSIS
• Avg Trade Duration: {metrics['avg_trade_duration']:.1f} hours
• Trades per Month: {metrics['trades_per_month']:.1f}

🧠 ADVANCED METRICS
• Kelly Criterion: {metrics['kelly_criterion']:.2f}
• ROI per Trade: {metrics['roi_per_trade']:.2f}%
• Recovery Factor: {metrics['recovery_factor']:.2f}

🏆 OVERALL RATING: {metrics['performance_rating']} {emoji}
"""
        
        return report
    
    def plot_performance_dashboard(self, metrics: Dict, trades: List[Dict], 
                                 equity_curve: List[Dict], save_path: str = None):
        """Create comprehensive performance dashboard"""
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle(f'Performance Dashboard - Rating: {metrics["performance_rating"]}', fontsize=16)
        
        # 1. Equity Curve
        if equity_curve:
            equity_df = pd.DataFrame(equity_curve)
            equity_df['time'] = pd.to_datetime(equity_df['time'])
            axes[0, 0].plot(equity_df['time'], equity_df['equity'], linewidth=2, color='green')
            axes[0, 0].set_title('Equity Curve')
            axes[0, 0].set_ylabel('Equity ($)')
            axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Trade Distribution
        if trades:
            trade_pnls = [t['pnl'] for t in trades]
            colors = ['green' if pnl > 0 else 'red' for pnl in trade_pnls]
            axes[0, 1].hist(trade_pnls, bins=30, alpha=0.7, color=colors, edgecolor='black')
            axes[0, 1].set_title('Trade P&L Distribution')
            axes[0, 1].set_xlabel('Profit/Loss ($)')
            axes[0, 1].set_ylabel('Frequency')
            axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Monthly Returns
        if trades:
            monthly_returns = {}
            for trade in trades:
                month = trade.get('entry_time', datetime.now()).strftime('%Y-%m')
                if month not in monthly_returns:
                    monthly_returns[month] = 0
                monthly_returns[month] += trade['pnl']
            
            months = sorted(monthly_returns.keys())
            returns = [monthly_returns[month] for month in months]
            
            axes[0, 2].bar(months, returns, color=['green' if r > 0 else 'red' for r in returns])
            axes[0, 2].set_title('Monthly Returns')
            axes[0, 2].set_ylabel('P&L ($)')
            axes[0, 2].tick_params(axis='x', rotation=45)
            axes[0, 2].grid(True, alpha=0.3)
        
        # 4. Risk Metrics Radar Chart
        risk_metrics = ['Win Rate', 'Sharpe', 'Profit Factor', 'Recovery', 'Consistency']
        risk_values = [
            metrics['win_rate'] / 100,
            min(metrics['sharpe_ratio'] / 3, 1),  # Cap at 1
            min(metrics['profit_factor'] / 3, 1),
            min(metrics['recovery_factor'] / 2, 1),
            (metrics['consistency_score'] + 1) / 2  # Convert to 0-1 scale
        ]
        
        angles = np.linspace(0, 2 * np.pi, len(risk_metrics), endpoint=False).tolist()
        angles += angles[:1]  # Complete the circle
        risk_values += risk_values[:1]
        
        axes[1, 0] = plt.subplot(2, 3, 5, projection='polar')
        axes[1, 0].plot(angles, risk_values, 'o-', linewidth=2)
        axes[1, 0].fill(angles, risk_values, alpha=0.25)
        axes[1, 0].set_xticks(angles[:-1])
        axes[1, 0].set_xticklabels(risk_metrics)
        axes[1, 0].set_title('Risk Profile')
        
        # 5. Key Metrics Table
        key_metrics = [
            ['Total Return', f"{metrics['total_return_pct']:.2f}%"],
            ['Win Rate', f"{metrics['win_rate']:.1f}%"],
            ['Profit Factor', f"{metrics['profit_factor']:.2f}"],
            ['Max Drawdown', f"{metrics['max_drawdown_pct']:.2f}%"],
            ['Sharpe Ratio', f"{metrics['sharpe_ratio']:.2f}"],
            ['Expectancy', f"${metrics['expectancy']:.2f}"]
        ]
        
        axes[1, 1].axis('tight')
        axes[1, 1].axis('off')
        table = axes[1, 1].table(cellText=key_metrics, colLabels=['Metric', 'Value'],
                                cellLoc='center', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.5)
        axes[1, 1].set_title('Key Metrics', pad=20)
        
        # 6. Performance Rating
        rating_colors = {
            'EXCELLENT': 'gold',
            'GOOD': 'lightgreen',
            'AVERAGE': 'lightblue',
            'POOR': 'orange',
            'VERY_POOR': 'lightcoral'
        }
        
        color = rating_colors.get(metrics['performance_rating'], 'gray')
        axes[1, 2].barh(0, 1, color=color, height=0.5)
        axes[1, 2].set_xlim(0, 1)
        axes[1, 2].set_ylim(-0.5, 0.5)
        axes[1, 2].set_title(f'Performance Rating: {metrics["performance_rating"]}', fontsize=14, fontweight='bold')
        axes[1, 2].set_xticks([])
        axes[1, 2].set_yticks([])
        axes[1, 2].text(0.5, 0, metrics['performance_rating'], ha='center', va='center', 
                        fontsize=16, fontweight='bold', color='white')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        
        plt.show()
