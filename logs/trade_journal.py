"""
Trade Journaling System for BrayoForexBot
Structured logging of all trading activities for analysis
"""

import pandas as pd
import json
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import os
import logging

logger = logging.getLogger(__name__)

class TradeJournal:
    """
    Professional Trade Journal
    Records every trade with structured data for analysis
    """
    
    def __init__(self, db_path: str = "logs/trades.db"):
        self.db_path = db_path
        self._ensure_db_directory()
        self._init_database()
    
    def _ensure_db_directory(self):
        """Ensure logs directory exists"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
    
    def _init_database(self):
        """Initialize SQLite database with trades table"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Create trades table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id TEXT UNIQUE,
                    pair TEXT NOT NULL,
                    action TEXT NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    position_size REAL NOT NULL,
                    stop_loss REAL,
                    take_profit REAL,
                    pnl REAL,
                    commission REAL,
                    duration_hours REAL,
                    strategy TEXT,
                    signal_strength REAL,
                    market_conditions TEXT,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create daily_summary table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_summary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE,
                    total_trades INTEGER,
                    winning_trades INTEGER,
                    losing_trades INTEGER,
                    total_pnl REAL,
                    win_rate REAL,
                    max_drawdown REAL,
                    sharpe_ratio REAL,
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Trade journal database initialized")
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    def record_trade(self, trade_data: Dict) -> bool:
        """
        Record a completed trade in the journal
        
        Args:
            trade_data: Dictionary with trade information
            
        Returns:
            Success status
        """
        try:
            # Generate unique trade ID if not provided
            if 'trade_id' not in trade_data:
                trade_data['trade_id'] = f"TRD_{int(datetime.now().timestamp())}"
            
            # Validate required fields
            required_fields = ['pair', 'action', 'entry_price', 'entry_time', 'position_size']
            for field in required_fields:
                if field not in trade_data:
                    logger.error(f"Missing required field: {field}")
                    return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert trade
            cursor.execute('''
                INSERT OR REPLACE INTO trades (
                    trade_id, pair, action, entry_price, exit_price,
                    entry_time, exit_time, position_size, stop_loss,
                    take_profit, pnl, commission, duration_hours,
                    strategy, signal_strength, market_conditions, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_data['trade_id'],
                trade_data['pair'],
                trade_data['action'],
                trade_data['entry_price'],
                trade_data.get('exit_price'),
                trade_data['entry_time'],
                trade_data.get('exit_time'),
                trade_data['position_size'],
                trade_data.get('stop_loss'),
                trade_data.get('take_profit'),
                trade_data.get('pnl'),
                trade_data.get('commission'),
                trade_data.get('duration_hours'),
                trade_data.get('strategy'),
                trade_data.get('signal_strength'),
                trade_data.get('market_conditions'),
                trade_data.get('notes', '')
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Trade recorded: {trade_data['trade_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
            return False
    
    def get_trades(self, 
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   pair: Optional[str] = None,
                   limit: Optional[int] = None) -> List[Dict]:
        """
        Get trades from journal with filters
        
        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            pair: Currency pair filter
            limit: Maximum number of trades to return
            
        Returns:
            List of trade dictionaries
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            query = "SELECT * FROM trades WHERE 1=1"
            params = []
            
            if start_date:
                query += " AND date(entry_time) >= ?"
                params.append(start_date)
            
            if end_date:
                query += " AND date(entry_time) <= ?"
                params.append(end_date)
            
            if pair:
                query += " AND pair = ?"
                params.append(pair)
            
            query += " ORDER BY entry_time DESC"
            
            if limit:
                query += " LIMIT ?"
                params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Get column names
            columns = [description[0] for description in cursor.description]
            
            # Convert to list of dictionaries
            trades = []
            for row in rows:
                trade = dict(zip(columns, row))
                # Convert numeric fields
                for field in ['entry_price', 'exit_price', 'position_size', 'stop_loss', 
                             'take_profit', 'pnl', 'commission', 'duration_hours', 'signal_strength']:
                    if trade[field] is not None:
                        trade[field] = float(trade[field])
                trades.append(trade)
            
            conn.close()
            return trades
            
        except Exception as e:
            logger.error(f"Error getting trades: {e}")
            return []
    
    def update_trade(self, trade_id: str, update_data: Dict) -> bool:
        """
        Update an existing trade
        
        Args:
            trade_id: Trade ID to update
            update_data: Fields to update
            
        Returns:
            Success status
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Build update query
            set_clauses = []
            params = []
            
            for field, value in update_data.items():
                if field in ['exit_price', 'exit_time', 'pnl', 'duration_hours', 'notes']:
                    set_clauses.append(f"{field} = ?")
                    params.append(value)
            
            if not set_clauses:
                logger.warning("No valid fields to update")
                return False
            
            query = f"UPDATE trades SET {', '.join(set_clauses)} WHERE trade_id = ?"
            params.append(trade_id)
            
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            
            logger.info(f"Trade updated: {trade_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating trade: {e}")
            return False
    
    def get_daily_summary(self, date: str) -> Dict:
        """
        Get daily trading summary
        
        Args:
            date: Date in YYYY-MM-DD format
            
        Returns:
            Daily summary dictionary
        """
        try:
            trades = self.get_trades(start_date=date, end_date=date)
            
            if not trades:
                return {
                    'date': date,
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_pnl': 0,
                    'win_rate': 0,
                    'notes': 'No trades'
                }
            
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
            losing_trades = len([t for t in trades if t.get('pnl', 0) < 0])
            total_pnl = sum(t.get('pnl', 0) for t in trades)
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            summary = {
                'date': date,
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'notes': ''
            }
            
            # Save to database
            self._save_daily_summary(summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting daily summary: {e}")
            return {}
    
    def _save_daily_summary(self, summary: Dict):
        """Save daily summary to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO daily_summary (
                    date, total_trades, winning_trades, losing_trades,
                    total_pnl, win_rate, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                summary['date'],
                summary['total_trades'],
                summary['winning_trades'],
                summary['losing_trades'],
                summary['total_pnl'],
                summary['win_rate'],
                summary['notes']
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error saving daily summary: {e}")
    
    def export_to_csv(self, filepath: str, start_date: Optional[str] = None, 
                     end_date: Optional[str] = None) -> bool:
        """
        Export trades to CSV file
        
        Args:
            filepath: Path to save CSV file
            start_date: Start date filter
            end_date: End date filter
            
        Returns:
            Success status
        """
        try:
            trades = self.get_trades(start_date=start_date, end_date=end_date)
            
            if not trades:
                logger.warning("No trades to export")
                return False
            
            df = pd.DataFrame(trades)
            df.to_csv(filepath, index=False)
            
            logger.info(f"Exported {len(trades)} trades to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False
    
    def get_trade_statistics(self) -> Dict:
        """
        Get comprehensive trade statistics
        
        Returns:
            Statistics dictionary
        """
        try:
            trades = self.get_trades()
            
            if not trades:
                return {'error': 'No trades found'}
            
            # Basic stats
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
            losing_trades = len([t for t in trades if t.get('pnl', 0) < 0])
            total_pnl = sum(t.get('pnl', 0) for t in trades)
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            # Profit/Loss stats
            wins = [t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0]
            losses = [abs(t.get('pnl', 0)) for t in trades if t.get('pnl', 0) < 0]
            
            avg_win = sum(wins) / len(wins) if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 0
            best_trade = max(wins) if wins else 0
            worst_trade = -min(losses) if losses else 0
            
            # Pair performance
            pair_performance = {}
            for trade in trades:
                pair = trade['pair']
                if pair not in pair_performance:
                    pair_performance[pair] = {'trades': 0, 'pnl': 0, 'wins': 0}
                pair_performance[pair]['trades'] += 1
                pair_performance[pair]['pnl'] += trade.get('pnl', 0)
                if trade.get('pnl', 0) > 0:
                    pair_performance[pair]['wins'] += 1
            
            # Calculate win rates per pair
            for pair in pair_performance:
                pair_performance[pair]['win_rate'] = (
                    pair_performance[pair]['wins'] / pair_performance[pair]['trades'] * 100
                )
            
            # Monthly performance
            monthly_performance = {}
            for trade in trades:
                month = trade['entry_time'][:7]  # YYYY-MM
                if month not in monthly_performance:
                    monthly_performance[month] = {'trades': 0, 'pnl': 0, 'wins': 0}
                monthly_performance[month]['trades'] += 1
                monthly_performance[month]['pnl'] += trade.get('pnl', 0)
                if trade.get('pnl', 0) > 0:
                    monthly_performance[month]['wins'] += 1
            
            # Calculate win rates per month
            for month in monthly_performance:
                monthly_performance[month]['win_rate'] = (
                    monthly_performance[month]['wins'] / monthly_performance[month]['trades'] * 100
                )
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'total_pnl': total_pnl,
                'win_rate': win_rate,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'pair_performance': pair_performance,
                'monthly_performance': monthly_performance
            }
            
        except Exception as e:
            logger.error(f"Error getting trade statistics: {e}")
            return {'error': str(e)}
    
    def analyze_mistakes(self) -> Dict:
        """
        Analyze common trading mistakes
        
        Returns:
            Analysis of mistakes
        """
        try:
            trades = self.get_trades()
            
            if not trades:
                return {'error': 'No trades to analyze'}
            
            mistakes = {
                'early_exits': [],
                'late_exits': [],
                'poor_entries': [],
                'ignored_stop_loss': [],
                'revenge_trades': []
            }
            
            for i, trade in enumerate(trades):
                if trade.get('pnl', 0) < 0:  # Only analyze losing trades
                    # Check for early exits (closed before reaching take profit)
                    if (trade.get('take_profit') and trade.get('exit_price') and 
                        trade['exit_price'] < trade['take_profit']):
                        mistakes['early_exits'].append(trade)
                    
                    # Check for poor entries (immediate negative movement)
                    if (i > 0 and trades[i-1].get('pnl', 0) < 0 and 
                        trade.get('entry_time', '')[:10] == trades[i-1].get('entry_time', '')[:10]):
                        mistakes['revenge_trades'].append(trade)
            
            return mistakes
            
        except Exception as e:
            logger.error(f"Error analyzing mistakes: {e}")
            return {'error': str(e)}
    
    def generate_journal_report(self, filepath: str = None) -> str:
        """
        Generate comprehensive journal report
        
        Args:
            filepath: Optional file path to save report
            
        Returns:
            Report text
        """
        try:
            stats = self.get_trade_statistics()
            mistakes = self.analyze_mistakes()
            
            report = f"""
📊 TRADE JOURNAL REPORT
{'='*60}

📈 OVERALL PERFORMANCE
• Total Trades: {stats.get('total_trades', 0)}
• Win Rate: {stats.get('win_rate', 0):.1f}%
• Total P&L: ${stats.get('total_pnl', 0):.2f}
• Average Win: ${stats.get('avg_win', 0):.2f}
• Average Loss: ${stats.get('avg_loss', 0):.2f}
• Best Trade: ${stats.get('best_trade', 0):.2f}
• Worst Trade: ${stats.get('worst_trade', 0):.2f}

📊 PAIR PERFORMANCE
"""
            
            for pair, perf in stats.get('pair_performance', {}).items():
                report += f"• {pair}: {perf['trades']} trades, {perf['win_rate']:.1f}% win rate, ${perf['pnl']:.2f} P&L\n"
            
            report += f"\n📅 MONTHLY PERFORMANCE\n"
            for month, perf in stats.get('monthly_performance', {}).items():
                report += f"• {month}: {perf['trades']} trades, {perf['win_rate']:.1f}% win rate, ${perf['pnl']:.2f} P&L\n"
            
            report += f"\n⚠️ MISTAKE ANALYSIS\n"
            if 'error' not in mistakes:
                report += f"• Early Exits: {len(mistakes.get('early_exits', []))} trades\n"
                report += f"• Revenge Trades: {len(mistakes.get('revenge_trades', []))} trades\n"
            
            report += f"\n📝 RECOMMENDATIONS\n"
            if stats.get('win_rate', 0) < 40:
                report += "• Consider reviewing entry criteria\n"
            if stats.get('avg_loss', 0) > stats.get('avg_win', 0):
                report += "• Risk management needs improvement\n"
            if len(mistakes.get('early_exits', [])) > 5:
                report += "• Practice patience with winning trades\n"
            
            if filepath:
                with open(filepath, 'w') as f:
                    f.write(report)
                logger.info(f"Journal report saved to {filepath}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating journal report: {e}")
            return f"Error generating report: {str(e)}"
