"""
LEVEL 7: TELEGRAM COMMAND CONTROL SYSTEM
Remote control commands for Nyx AI Level 7
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class TelegramCommandHandler:
    """Handle Telegram commands for remote bot control"""
    
    def __init__(self, live_executor, telegram_bot):
        self.live_executor = live_executor
        self.telegram = telegram_bot
        self.commands = {
            '/start': self.cmd_start,
            '/stop': self.cmd_stop,
            '/status': self.cmd_status,
            '/closeall': self.cmd_close_all,
            '/help': self.cmd_help
        }
    
    def handle_command(self, message_text, chat_id):
        """Parse and execute Telegram commands"""
        try:
            # Extract command from message
            command = message_text.strip().lower()
            
            if command in self.commands:
                response = self.commands[command]()
                self.telegram.send_message(response)
                logger.info(f"Telegram command executed: {command} by chat {chat_id}")
            else:
                # Unknown command
                help_response = self.cmd_help()
                self.telegram.send_message(help_response)
                logger.warning(f"Unknown Telegram command: {command}")
                
        except Exception as e:
            logger.error(f"Error handling Telegram command: {e}")
            self.telegram.send_message(f"❌ Error executing command: {e}")
    
    def cmd_start(self):
        """Start trading command"""
        try:
            if not self.live_executor.running:
                self.live_executor.running = True
                self.live_executor.is_running = True
                return """🚀 TRADING STARTED

Status: ACTIVE
Mode: Normal Trading
Bot: Nyx AI Level 7
Time: {}
""".format(datetime.now().strftime('%H:%M:%S'))
            else:
                return """✅ Trading already running

Status: Already ACTIVE
Bot: Nyx AI Level 7
"""
        except Exception as e:
            return f"❌ Error starting trading: {e}"
    
    def cmd_stop(self):
        """Stop trading command"""
        try:
            if self.live_executor.running:
                self.live_executor.stop()
                return """🛑 TRADING STOPPED

Status: STOPPED
Action: All positions will be managed normally
Bot: Nyx AI Level 7
Time: {}
""".format(datetime.now().strftime('%H:%M:%S'))
            else:
                return """⚠️ Trading already stopped

Status: Already STOPPED
Bot: Nyx AI Level 7
"""
        except Exception as e:
            return f"❌ Error stopping trading: {e}"
    
    def cmd_status(self):
        """Status command - show current bot status"""
        try:
            # Get account info
            import MetaTrader5 as mt5
            account = mt5.account_info()
            
            if not account:
                return "❌ Unable to get account status"
            
            # Get open positions
            positions = mt5.positions_get()
            open_trades = len(positions) if positions else 0
            
            # Get daily profit
            daily_profit = getattr(self.live_executor, '_daily_profit', 0.0)
            
            return """📊 NYX AI STATUS REPORT

🤖 Bot Status: {}
💰 Account Balance: ${:,.2f}
💎 Account Equity: ${:,.2f}
📈 Daily P&L: ${:+.2f}
🔄 Open Trades: {}

⏰ Time: {}
🏷️ Level: 7 Quantum Intelligence

Commands: /start, /stop, /status, /closeall, /help
""".format(
                "🟢 ACTIVE" if self.live_executor.running else "🔴 STOPPED",
                account.balance,
                account.equity,
                daily_profit,
                open_trades,
                datetime.now().strftime('%H:%M:%S')
            )
            
        except Exception as e:
            return f"❌ Error getting status: {e}"
    
    def cmd_close_all(self):
        """Close all positions command"""
        try:
            import MetaTrader5 as mt5
            positions = mt5.positions_get()
            
            if not positions:
                return "ℹ️ No open positions to close"
            
            closed_count = 0
            for pos in positions:
                result = self.live_executor.close_trade_by_ticket(pos.ticket)
                if result:
                    closed_count += 1
            
            return """🔒 ALL POSITIONS CLOSED

Closed: {} positions
Remaining: {} positions
Time: {}
Bot: Nyx AI Level 7
""".format(
                closed_count,
                len(positions) - closed_count,
                datetime.now().strftime('%H:%M:%S')
            )
            
        except Exception as e:
            return f"❌ Error closing all positions: {e}"
    
    def cmd_help(self):
        """Help command - show available commands"""
        return """🤖 NYX AI LEVEL 7 - COMMAND HELP

Available Commands:
/start - Start trading bot
/stop - Stop trading bot
/status - Show bot status and performance
/closeall - Close all open positions
/help - Show this help message

Example: /status

Bot: Nyx AI Level 7 Quantum Intelligence
Time: {}
""".format(datetime.now().strftime('%H:%M:%S'))
