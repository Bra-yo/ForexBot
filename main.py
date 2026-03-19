#!/usr/bin/env python3
"""
BrayoForexBot - A Forex AI Trading Bot
Created by: [Your Name]
Purpose: Automated forex trading with technical analysis and risk management
"""

import os
import time
import logging
import schedule
from datetime import datetime
from dotenv import load_dotenv

# Import bot modules
from config import Config
from market_data import MarketDataReader
from technical_analysis import TechnicalAnalysis
from trading_engine import TradingEngine
from risk_management import RiskManager
from notifications import NotificationManager
from backtesting import Backtester

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('forex_bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class BrayoForexBot:
    """Main Forex Bot Class"""
    
    def __init__(self):
        # Validate configuration
        config_errors = Config.validate_config()
        if config_errors:
            logger.error("Configuration errors found:")
            for error in config_errors:
                logger.error(f"  - {error}")
            raise ValueError("Invalid configuration")
        
        # Initialize components
        self.market_data = MarketDataReader()
        self.technical_analysis = TechnicalAnalysis()
        self.risk_manager = RiskManager()
        self.trading_engine = TradingEngine(self.risk_manager)
        self.notifications = NotificationManager()
        self.backtester = Backtester()
        
        # Bot settings
        self.trading_mode = Config.TRADING_MODE
        self.currency_pairs = Config.CURRENCY_PAIRS
        self.timeframe = '1h'
        
        logger.info(f"🚀 BrayoForexBot initialized in {self.trading_mode} mode")
        logger.info(f"📊 Monitoring {len(self.currency_pairs)} currency pairs")
        
        # Test notifications on startup
        if self.notifications.enabled:
            self.notifications.send_trade_alert({
                'action': 'START',
                'pair': 'BOT',
                'entry_price': 0,
                'position_size': 0,
                'confidence': 100,
                'reasons': ['Bot started successfully']
            })
        
    def run(self):
        """Main bot execution loop"""
        logger.info("🚀 Starting BrayoForexBot...")
        
        # Schedule daily summary
        schedule.every().day.at("23:59").do(self.send_daily_summary)
        
        try:
            while True:
                # Check if we should stop trading
                should_stop, reason = self.risk_manager.should_stop_trading()
                if should_stop:
                    logger.error(f"🛑 Trading stopped: {reason}")
                    self.notifications.send_risk_alert({
                        'risk_status': 'STOPPED',
                        'daily_pnl': self.risk_manager.daily_pnl,
                        'daily_loss_used': 100
                    })
                    break
                
                # Main trading logic
                self.main_trading_loop()
                
                # Run scheduled tasks
                schedule.run_pending()
                
                # Wait before next iteration
                time.sleep(60)  # Check every minute
                
        except KeyboardInterrupt:
            logger.info("👋 Bot stopped by user")
            self.send_shutdown_message()
        except Exception as e:
            logger.error(f"❌ Bot encountered error: {e}")
            self.notifications.send_error_alert({
                'type': 'CRITICAL',
                'message': str(e)
            })
            raise
    
    def main_trading_loop(self):
        """Main trading logic"""
        try:
            # Get market data for all pairs
            market_data = self.market_data.get_multiple_pairs(
                self.currency_pairs, self.timeframe, '7d'
            )
            
            if not market_data:
                logger.warning("No market data available")
                return
            
            # Analyze each pair
            for pair, data in market_data.items():
                try:
                    # Skip if no data
                    if data.empty:
                        continue
                    
                    # Calculate indicators
                    data_with_indicators = self.technical_analysis.get_all_indicators(data)
                    
                    # Analyze signals
                    signals = self.technical_analysis.analyze_signals(data_with_indicators)
                    
                    # Check for trading opportunity
                    decision = self.trading_engine.analyze_trading_opportunity(
                        pair, data_with_indicators, signals
                    )
                    
                    # Execute trade if signal is strong
                    if decision['action'] in ['BUY', 'SELL']:
                        execution_result = self.trading_engine.execute_trade(decision)
                        
                        if execution_result['success']:
                            # Send notification
                            self.notifications.send_trade_alert(decision)
                            
                            # Update risk manager
                            if decision['action'] == 'BUY':
                                exposure = decision['position_size'] * decision['entry_price']
                            else:
                                exposure = decision['position_size'] * decision['entry_price']
                            
                            self.risk_manager.update_pair_exposure(pair, exposure)
                    
                    # Log analysis results
                    logger.info(f"{pair}: {signals['signal']} ({signals['strength']:.1f}%)")
                    
                except Exception as e:
                    logger.error(f"Error analyzing {pair}: {e}")
                    continue
            
            # Manage existing positions
            self.trading_engine.manage_positions(market_data)
            
            # Update risk metrics
            self.update_risk_metrics()
            
        except Exception as e:
            logger.error(f"Error in main trading loop: {e}")
    
    def update_risk_metrics(self):
        """Update risk management metrics"""
        try:
            # Get position summary
            position_summary = self.trading_engine.get_position_summary()
            
            # Update risk manager with current P&L
            if 'total_realized_pnl' in position_summary:
                self.risk_manager.daily_pnl = position_summary['total_realized_pnl']
            
            # Check for risk alerts
            risk_metrics = self.risk_manager.get_risk_metrics()
            if risk_metrics.get('risk_status') != 'HEALTHY':
                self.notifications.send_risk_alert(risk_metrics)
                
        except Exception as e:
            logger.error(f"Error updating risk metrics: {e}")
    
    def send_daily_summary(self):
        """Send daily trading summary"""
        try:
            # Get trading statistics
            stats = self.trading_engine.get_trading_statistics()
            risk_metrics = self.risk_manager.get_risk_metrics()
            
            summary = {
                'total_trades': stats.get('total_trades', 0),
                'winning_trades': stats.get('winning_trades', 0),
                'total_pnl': stats.get('total_pnl', 0),
                'win_rate': stats.get('win_rate', 0)
            }
            
            self.notifications.send_daily_summary(summary)
            logger.info("📊 Daily summary sent")
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
    
    def send_shutdown_message(self):
        """Send shutdown notification"""
        try:
            stats = self.trading_engine.get_trading_statistics()
            
            message = {
                'action': 'STOP',
                'pair': 'BOT',
                'entry_price': 0,
                'position_size': 0,
                'confidence': 100,
                'reasons': [f"Bot shutdown. Total trades: {stats.get('total_trades', 0)}"]
            }
            
            self.notifications.send_trade_alert(message)
            
        except Exception as e:
            logger.error(f"Error sending shutdown message: {e}")
    
    def run_backtest(self, pair, start_date, end_date):
        """Run backtest for a specific pair and period"""
        try:
            logger.info(f"📈 Running backtest for {pair} from {start_date} to {end_date}")
            
            results = self.backtester.run_backtest(pair, start_date, end_date, self.timeframe)
            
            if 'error' in results:
                logger.error(f"Backtest failed: {results['error']}")
                return results
            
            # Generate report
            report = self.backtester.generate_backtest_report(results)
            logger.info(f"Backtest completed for {pair}")
            
            # Save report
            report_file = f"backtest_{pair}_{start_date}_{end_date}.txt"
            with open(report_file, 'w') as f:
                f.write(report)
            
            logger.info(f"Backtest report saved to {report_file}")
            return results
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return {'error': str(e)}
    
    def get_status(self):
        """Get current bot status"""
        try:
            position_summary = self.trading_engine.get_position_summary()
            risk_metrics = self.risk_manager.get_risk_metrics()
            stats = self.trading_engine.get_trading_statistics()
            
            status = {
                'bot_mode': self.trading_mode,
                'monitored_pairs': len(self.currency_pairs),
                'open_positions': position_summary.get('total_positions', 0),
                'total_pnl': position_summary.get('total_realized_pnl', 0),
                'daily_pnl': risk_metrics.get('daily_pnl', 0),
                'risk_status': risk_metrics.get('risk_status', 'UNKNOWN'),
                'total_trades': stats.get('total_trades', 0),
                'win_rate': stats.get('win_rate', 0),
                'notifications_enabled': self.notifications.enabled
            }
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {'error': str(e)}

if __name__ == "__main__":
    bot = BrayoForexBot()
    bot.run()
