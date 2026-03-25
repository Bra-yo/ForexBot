"""
Telegram Notifications Module for BrayoForexBot
Handles sending trade alerts and notifications via Telegram Bot API
"""

import requests
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
import json

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Class for sending Telegram notifications"""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        """
        Initialize Telegram notifier
        
        Args:
            bot_token (str): Telegram bot token
            chat_id (str): Telegram chat ID
        """
        self.bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = chat_id or os.getenv('TELEGRAM_CHAT_ID')
        
        # Cooldown tracking to prevent spam
        self.last_alert_time = {}
        self.cooldown_minutes = 10  # 10 minutes cooldown between same setup alerts
        self.last_execution_time = {}
        
        # Validate setup
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram credentials not provided. Notifications disabled.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Telegram notifications enabled")
    
    def send_message(self, message: str) -> bool:
        """
        Send message to Telegram
        
        Args:
            message (str): Message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.enabled:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, data=data, timeout=10)
            
            if response.status_code == 200:
                logger.info("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    def check_cooldown(self, signal_key: str) -> bool:
        """
        Check if enough time has passed since last alert
        
        Args:
            signal_key (str): Unique key for the signal setup
            
        Returns:
            bool: True if cooldown period has passed
        """
        if signal_key not in self.last_alert_time:
            return True
            
        time_since_last = datetime.now() - self.last_alert_time[signal_key]
        return time_since_last >= timedelta(minutes=self.cooldown_minutes)
    
    def send_trade_alert(self, signal_data: Dict) -> bool:
        """
        Send trade alert for valid setup
        
        Args:
            signal_data (Dict): Signal analysis data
            
        Returns:
            bool: True if alert sent, False if blocked by cooldown
        """
        # Check if alert conditions are met
        if not self._should_send_alert(signal_data):
            return False
        
        # Create unique signal key for cooldown
        symbol = signal_data.get('symbol', 'UNKNOWN')
        signal = signal_data.get('signal', 'WAIT')
        signal_key = f"{symbol}_{signal}"
        
        # Check cooldown
        if not self.check_cooldown(signal_key):
            logger.info(f"Telegram alert blocked by cooldown for {signal_key}")
            return False
        
        # Format message
        message = self._format_trade_alert(signal_data)
        
        # Send message
        if self.send_message(message):
            self.last_alert_time[signal_key] = datetime.now()
            return True
        
        return False
    
    def send_market_state_change(self, symbol: str, old_state: str, new_state: str) -> bool:
        """
        Send notification when market state changes
        
        Args:
            symbol (str): Currency pair
            old_state (str): Previous market state
            new_state (str): New market state
            
        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            return False
        
        # Only notify for significant changes
        if new_state == old_state:
            return False
        
        message = f"""📊 MARKET STATE CHANGE 📊

<b>Pair:</b> {symbol}
<b>Previous:</b> {old_state}
<b>Current:</b> {new_state}
<b>Time:</b> {datetime.now().strftime('%H:%M:%S')}

<i>Market conditions have changed - check for new opportunities</i>"""
        
        return self.send_message(message)
    
    def send_trade_execution(self, trade_data: Dict) -> bool:
        """
        Send notification when trade is executed
        
        Args:
            trade_data (Dict): Trade execution details
            
        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            return False
        
        symbol = trade_data.get('symbol', 'UNKNOWN')
        signal = trade_data.get('type', 'UNKNOWN')
        entry = trade_data.get('entry_price', 0)
        sl = trade_data.get('stop_loss', 0)
        tp = trade_data.get('take_profit', 0)
        volume = trade_data.get('volume', 0)
        
        message = f"""✅ TRADE EXECUTED ✅

<b>Pair:</b> {symbol}
<b>Signal:</b> {signal}
<b>Volume:</b> {volume}

<b>Entry:</b> {entry:.5f}
<b>Stop Loss:</b> {sl:.5f}
<b>Take Profit:</b> {tp:.5f}

<i>Trade has been placed successfully</i>"""
        
        return self.send_message(message)
    
    def send_trade_closure(self, trade_data: Dict) -> bool:
        """
        Send notification when trade is closed
        
        Args:
            trade_data (Dict): Trade closure details
            
        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            return False
        
        symbol = trade_data.get('symbol', 'UNKNOWN')
        reason = trade_data.get('reason', 'UNKNOWN')
        profit = trade_data.get('profit', 0)
        
        # Determine emoji based on profit
        emoji = "💰" if profit > 0 else "📉"
        
        message = f"""{emoji} TRADE CLOSED {emoji}

<b>Pair:</b> {symbol}
<b>Reason:</b> {reason}
<b>Profit:</b> {profit:.2f} USD

<i>Trade has been closed</i>"""
        
        return self.send_message(message)
    
    def _should_send_alert(self, signal_data: Dict) -> bool:
        """
        Check if alert conditions are met
        
        Args:
            signal_data (Dict): Signal analysis data
            
        Returns:
            bool: True if conditions are met
        """
        # Check all required conditions
        conditions = {
            'market_state': signal_data.get('market_state') in ['TRENDING', 'ACTIVE'],  # Allow ACTIVE too
            'trade_blocked': not signal_data.get('trade_blocked', True),
            'entry_confirmed': signal_data.get('entry_confirmed', False),
            'risk_reward_valid': signal_data.get('risk_reward', {}).get('valid', False),
            'valid_signal': signal_data.get('signal') in ['BUY', 'SELL']
        }
        
        # Special override for STRONG signals
        signal_confidence = signal_data.get('confidence', 0)
        if signal_confidence >= 80:  # STRONG signals override some conditions
            conditions['market_state'] = True  # Override market state requirement
            conditions['risk_reward_valid'] = True  # Override risk:reward requirement
        
        # Log condition checks for debugging
        logger.info(f"Telegram alert conditions: {conditions}")
        logger.info(f"Signal confidence: {signal_confidence}% - {'STRONG override' if signal_confidence >= 80 else 'Normal check'}")
        
        return all(conditions.values())
    
    def _format_trade_alert(self, signal_data: Dict) -> str:
        """
        Format trade alert message
        
        Args:
            signal_data (Dict): Signal analysis data
            
        Returns:
            str: Formatted message
        """
        symbol = signal_data.get('symbol', 'UNKNOWN')
        signal = signal_data.get('signal', 'WAIT')
        confidence = signal_data.get('confidence', 0)
        market_state = signal_data.get('market_state', 'UNKNOWN')
        htf_trend = signal_data.get('htf_trend', 'UNKNOWN')
        
        entry_price = signal_data.get('entry_price', 0)
        stop_loss = signal_data.get('structure_sl', 0)
        take_profit = signal_data.get('structure_tp', 0)
        
        risk_reward = signal_data.get('risk_reward', {})
        rr_ratio = risk_reward.get('ratio', 0)
        
        reasons = signal_data.get('reasons', [])
        
        # Determine signal emoji
        signal_emoji = "📈" if signal == "BUY" else "📉" if signal == "SELL" else "⏳"
        
        # Format reasons
        reasons_text = "\n".join([f"• {reason}" for reason in reasons[:3]])  # Limit to top 3
        
        message = f"""🚀 TRADE ALERT 🚀

<b>Pair:</b> {symbol}
<b>Signal:</b> {signal_emoji} {signal}
<b>Confidence:</b> {confidence:.0f}%
<b>Market State:</b> {market_state}
<b>HTF Trend:</b> {htf_trend}

<b>Entry:</b> {entry_price:.5f}
<b>Stop Loss:</b> {stop_loss:.5f}
<b>Take Profit:</b> {take_profit:.5f}
<b>Risk:Reward:</b> {rr_ratio:.1f}:1

<b>Reason:</b>
{reasons_text}

<i>High-quality setup detected - consider trading</i>"""
        
        return message
    
    def test_connection(self) -> bool:
        """
        Test Telegram bot connection
        
        Returns:
            bool: True if connection successful
        """
        if not self.enabled:
            return False
        
        message = f"""🤖 BOT TEST 🤖

<b>Status:</b> ✅ Online
<b>Time:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

<i>BrayoForexBot is ready to send alerts</i>"""
        
        return self.send_message(message)
