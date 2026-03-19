"""
Notification System Module for BrayoForexBot
Handles alerts and notifications via Telegram and other channels
"""

import os
import requests
import json
from datetime import datetime
from config import Config
import logging

logger = logging.getLogger(__name__)

class NotificationManager:
    """Manages trading notifications and alerts"""
    
    def __init__(self):
        self.telegram_token = Config.TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = Config.TELEGRAM_CHAT_ID
        self.enabled = bool(self.telegram_token and self.telegram_chat_id)
        self.message_queue = []
        self.last_notification = {}
        self.cooldown_period = 300  # 5 minutes cooldown between similar notifications
        
    def send_trade_alert(self, trade_info):
        """
        Send trade execution alert
        
        Args:
            trade_info (dict): Trade information
        """
        try:
            message = self._format_trade_message(trade_info)
            self._send_notification("TRADE", message)
            
        except Exception as e:
            logger.error(f"Error sending trade alert: {e}")
    
    def send_position_update(self, position_info):
        """
        Send position update alert
        
        Args:
            position_info (dict): Position information
        """
        try:
            message = self._format_position_message(position_info)
            self._send_notification("POSITION", message)
            
        except Exception as e:
            logger.error(f"Error sending position update: {e}")
    
    def send_risk_alert(self, risk_info):
        """
        Send risk management alert
        
        Args:
            risk_info (dict): Risk information
        """
        try:
            message = self._format_risk_message(risk_info)
            self._send_notification("RISK", message)
            
        except Exception as e:
            logger.error(f"Error sending risk alert: {e}")
    
    def send_market_alert(self, market_info):
        """
        Send market condition alert
        
        Args:
            market_info (dict): Market information
        """
        try:
            message = self._format_market_message(market_info)
            self._send_notification("MARKET", message)
            
        except Exception as e:
            logger.error(f"Error sending market alert: {e}")
    
    def send_daily_summary(self, summary_info):
        """
        Send daily trading summary
        
        Args:
            summary_info (dict): Daily summary information
        """
        try:
            message = self._format_daily_summary(summary_info)
            self._send_notification("DAILY", message)
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
    
    def send_error_alert(self, error_info):
        """
        Send error alert
        
        Args:
            error_info (dict): Error information
        """
        try:
            message = self._format_error_message(error_info)
            self._send_notification("ERROR", message)
            
        except Exception as e:
            logger.error(f"Error sending error alert: {e}")
    
    def _send_notification(self, notification_type, message):
        """
        Send notification through available channels
        
        Args:
            notification_type (str): Type of notification
            message (str): Message content
        """
        try:
            # Check cooldown to avoid spam
            if self._is_in_cooldown(notification_type, message):
                logger.debug(f"Notification {notification_type} in cooldown, skipping")
                return
            
            # Send via Telegram if enabled
            if self.enabled:
                success = self._send_telegram_message(message)
                if success:
                    self._update_last_notification(notification_type, message)
                    logger.info(f"Telegram notification sent: {notification_type}")
                else:
                    logger.warning("Failed to send Telegram notification")
            else:
                # Log to console if Telegram not configured
                logger.info(f"NOTIFICATION [{notification_type}]: {message}")
            
            # Add to message queue for backup
            self.message_queue.append({
                'type': notification_type,
                'message': message,
                'timestamp': datetime.now(),
                'sent': self.enabled
            })
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def _send_telegram_message(self, message):
        """Send message via Telegram"""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            
            payload = {
                'chat_id': self.telegram_chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=10)
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def _format_trade_message(self, trade_info):
        """Format trade execution message"""
        try:
            action = trade_info.get('action', 'UNKNOWN')
            pair = trade_info.get('pair', 'UNKNOWN')
            price = trade_info.get('entry_price', 0)
            size = trade_info.get('position_size', 0)
            confidence = trade_info.get('confidence', 0)
            
            emoji = "🟢" if action == "BUY" else "🔴" if action == "SELL" else "⏸️"
            
            message = f"""
{emoji} **TRADE EXECUTED**

**Action:** {action}
**Pair:** {pair}
**Price:** {price:.5f}
**Size:** {size} lots
**Confidence:** {confidence:.1f}%
**Time:** {datetime.now().strftime('%H:%M:%S')}

*BrayoForexBot*
"""
            return message.strip()
            
        except Exception as e:
            return f"Error formatting trade message: {str(e)}"
    
    def _format_position_message(self, position_info):
        """Format position update message"""
        try:
            pair = position_info.get('pair', 'UNKNOWN')
            action = position_info.get('action', 'UNKNOWN')
            pnl = position_info.get('unrealized_pnl', 0)
            status = position_info.get('status', 'UNKNOWN')
            
            if status == 'CLOSED':
                emoji = "✅" if pnl > 0 else "❌"
                pnl_text = f"PnL: ${pnl:.2f}"
            else:
                emoji = "📊"
                pnl_text = f"Unrealized PnL: ${pnl:.2f}"
            
            message = f"""
{emoji} **POSITION UPDATE**

**Pair:** {pair}
**Action:** {action}
**Status:** {status}
{pnl_text}
**Time:** {datetime.now().strftime('%H:%M:%S')}

*BrayoForexBot*
"""
            return message.strip()
            
        except Exception as e:
            return f"Error formatting position message: {str(e)}"
    
    def _format_risk_message(self, risk_info):
        """Format risk alert message"""
        try:
            risk_status = risk_info.get('risk_status', 'UNKNOWN')
            daily_pnl = risk_info.get('daily_pnl', 0)
            loss_used = risk_info.get('daily_loss_used', 0)
            
            if risk_status == 'HIGH_RISK':
                emoji = "⚠️"
            elif risk_status == 'MEDIUM_RISK':
                emoji = "⚡"
            else:
                emoji = "✅"
            
            message = f"""
{emoji} **RISK ALERT**

**Status:** {risk_status}
**Daily P&L:** ${daily_pnl:.2f}
**Loss Limit Used:** {loss_used:.1f}%
**Time:** {datetime.now().strftime('%H:%M:%S')}

*BrayoForexBot*
"""
            return message.strip()
            
        except Exception as e:
            return f"Error formatting risk message: {str(e)}"
    
    def _format_market_message(self, market_info):
        """Format market condition message"""
        try:
            message = f"""
📈 **MARKET ALERT**

{market_info}

**Time:** {datetime.now().strftime('%H:%M:%S')}

*BrayoForexBot*
"""
            return message.strip()
            
        except Exception as e:
            return f"Error formatting market message: {str(e)}"
    
    def _format_daily_summary(self, summary_info):
        """Format daily summary message"""
        try:
            total_trades = summary_info.get('total_trades', 0)
            winning_trades = summary_info.get('winning_trades', 0)
            total_pnl = summary_info.get('total_pnl', 0)
            win_rate = summary_info.get('win_rate', 0)
            
            emoji = "📊" if total_pnl >= 0 else "📉"
            
            message = f"""
{emoji} **DAILY SUMMARY**

**Total Trades:** {total_trades}
**Winning Trades:** {winning_trades}
**Win Rate:** {win_rate:.1f}%
**Daily P&L:** ${total_pnl:.2f}
**Date:** {datetime.now().strftime('%Y-%m-%d')}

*BrayoForexBot*
"""
            return message.strip()
            
        except Exception as e:
            return f"Error formatting daily summary: {str(e)}"
    
    def _format_error_message(self, error_info):
        """Format error alert message"""
        try:
            error_type = error_info.get('type', 'UNKNOWN')
            error_message = error_info.get('message', 'Unknown error')
            
            message = f"""
🚨 **ERROR ALERT**

**Type:** {error_type}
**Message:** {error_message}
**Time:** {datetime.now().strftime('%H:%M:%S')}

*BrayoForexBot*
"""
            return message.strip()
            
        except Exception as e:
            return f"Error formatting error message: {str(e)}"
    
    def _is_in_cooldown(self, notification_type, message):
        """Check if notification type is in cooldown period"""
        try:
            if notification_type not in self.last_notification:
                return False
            
            last_time = self.last_notification[notification_type].get('timestamp')
            if not last_time:
                return False
            
            time_diff = (datetime.now() - last_time).total_seconds()
            return time_diff < self.cooldown_period
            
        except Exception as e:
            logger.error(f"Error checking cooldown: {e}")
            return False
    
    def _update_last_notification(self, notification_type, message):
        """Update last notification timestamp"""
        try:
            self.last_notification[notification_type] = {
                'message': message,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error updating last notification: {e}")
    
    def test_notifications(self):
        """Test notification system"""
        try:
            test_message = """
🧪 **TEST NOTIFICATION**

This is a test message from BrayoForexBot.

If you receive this, notifications are working correctly! ✅

**Time:** {time}

*BrayoForexBot*
""".format(time=datetime.now().strftime('%H:%M:%S'))

            if self.enabled:
                success = self._send_telegram_message(test_message)
                logger.info(f"Test notification {'sent successfully' if success else 'failed'}")
                return success
            else:
                logger.info("Notifications not enabled - test message logged")
                return True
                
        except Exception as e:
            logger.error(f"Error testing notifications: {e}")
            return False
    
    def get_notification_stats(self):
        """Get notification statistics"""
        try:
            stats = {
                'enabled': self.enabled,
                'total_sent': len([m for m in self.message_queue if m['sent']]),
                'total_queued': len(self.message_queue),
                'last_notifications': {}
            }
            
            for notification_type, last_notif in self.last_notification.items():
                stats['last_notifications'][notification_type] = {
                    'message': last_notif['message'][:100] + '...' if len(last_notif['message']) > 100 else last_notif['message'],
                    'timestamp': last_notif['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting notification stats: {e}")
            return {'error': str(e)}
    
    def clear_queue(self):
        """Clear message queue"""
        try:
            self.message_queue.clear()
            logger.info("Notification queue cleared")
            
        except Exception as e:
            logger.error(f"Error clearing queue: {e}")
