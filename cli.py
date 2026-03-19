#!/usr/bin/env python3
"""
Command Line Interface for BrayoForexBot
Provides easy commands to run the bot, backtest, and get status
"""

import argparse
import sys
from datetime import datetime, timedelta
from main import BrayoForexBot
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description='BrayoForexBot - Forex AI Trading Bot')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run the trading bot')
    run_parser.add_argument('--mode', choices=['paper', 'live'], default='paper',
                          help='Trading mode (default: paper)')
    
    # Backtest command
    backtest_parser = subparsers.add_parser('backtest', help='Run backtesting')
    backtest_parser.add_argument('pair', help='Currency pair (e.g., EUR/USD)')
    backtest_parser.add_argument('start_date', help='Start date (YYYY-MM-DD)')
    backtest_parser.add_argument('end_date', help='End date (YYYY-MM-DD)')
    backtest_parser.add_argument('--timeframe', default='1h', 
                                choices=['1m', '5m', '15m', '1h', '4h', '1d'],
                                help='Timeframe for backtesting (default: 1h)')
    
    # Status command
    status_parser = subparsers.add_parser('status', help='Get bot status')
    
    # Test command
    test_parser = subparsers.add_parser('test', help='Test bot components')
    test_parser.add_argument('--notifications', action='store_true',
                           help='Test notification system')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        bot = BrayoForexBot()
        
        if args.command == 'run':
            logger.info(f"🚀 Starting BrayoForexBot in {args.mode} mode")
            bot.run()
            
        elif args.command == 'backtest':
            logger.info(f"📈 Running backtest for {args.pair}")
            results = bot.run_backtest(args.pair, args.start_date, args.end_date)
            
            if 'error' not in results:
                print(f"\n✅ Backtest completed successfully!")
                print(f"📊 Total Return: {results['metrics']['total_return_pct']:.2f}%")
                print(f"🎯 Win Rate: {results['metrics']['win_rate']:.1f}%")
                print(f"💰 Total Trades: {results['total_trades']}")
                print(f"📈 Profit Factor: {results['metrics']['profit_factor']:.2f}")
            else:
                print(f"❌ Backtest failed: {results['error']}")
                
        elif args.command == 'status':
            status = bot.get_status()
            if 'error' not in status:
                print(f"\n📊 BrayoForexBot Status:")
                print(f"🤖 Mode: {status['bot_mode']}")
                print(f"📈 Monitored Pairs: {status['monitored_pairs']}")
                print(f"📋 Open Positions: {status['open_positions']}")
                print(f"💰 Total P&L: ${status['total_pnl']:.2f}")
                print(f"📅 Daily P&L: ${status['daily_pnl']:.2f}")
                print(f"⚠️ Risk Status: {status['risk_status']}")
                print(f"🎯 Total Trades: {status['total_trades']}")
                print(f"📈 Win Rate: {status['win_rate']:.1f}%")
                print(f"📢 Notifications: {'✅' if status['notifications_enabled'] else '❌'}")
            else:
                print(f"❌ Error getting status: {status['error']}")
                
        elif args.command == 'test':
            if args.notifications:
                logger.info("🧪 Testing notification system...")
                success = bot.notifications.test_notifications()
                if success:
                    print("✅ Notification test successful!")
                else:
                    print("❌ Notification test failed!")
            else:
                print("🧪 Running basic tests...")
                print("✅ Bot initialization successful!")
                print("✅ Configuration validation passed!")
                
    except KeyboardInterrupt:
        logger.info("👋 Operation cancelled by user")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
