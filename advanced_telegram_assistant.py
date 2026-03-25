"""
Advanced Telegram Trading Assistant with Interactive Features
Handles chart screenshots, inline keyboards, and callback queries
"""

import requests
import os
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import io
import base64
from telegram_notifier import TelegramNotifier
try:
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, CallbackQuery
    from telegram.ext import CallbackQueryHandler, Dispatcher
except ImportError:
    # Fallback for older versions
    try:
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, CallbackQuery
        from telegram.ext import CallbackQueryHandler, Dispatcher
    except ImportError:
        # If telegram library is not available, create dummy classes
        class InlineKeyboardButton:
            def __init__(self, text, callback_data):
                self.text = text
                self.callback_data = callback_data
        
        class InlineKeyboardMarkup:
            def __init__(self, keyboard):
                self.keyboard = keyboard
        
        class Update:
            pass
        
        class CallbackQuery:
            pass
        
        class CallbackQueryHandler:
            def __init__(self, callback):
                self.callback = callback
        
        class Dispatcher:
            def add_handler(self, handler):
                pass

logger = logging.getLogger(__name__)

# Authorized user ID for security (replace with your actual Telegram user ID)
AUTHORIZED_USER_ID = int(os.getenv('TELEGRAM_USER_ID', '0'))

class AdvancedTelegramAssistant(TelegramNotifier):
    """Advanced Telegram trading assistant with charts and interactive buttons"""
    
    def __init__(self, bot_token: str = None, chat_id: str = None):
        super().__init__(bot_token, chat_id)
        self.pending_trades = {}  # Store pending trade alerts
        
        # Check if interactive features are available
        self.interactive_enabled = self._check_telegram_library()
        
    def _check_telegram_library(self) -> bool:
        """Check if telegram library with interactive features is available"""
        try:
            # Try to import and use telegram classes
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            return True
        except ImportError:
            logger.warning("Telegram interactive features not available - using basic mode")
            return False
        
    def send_trade_alert_with_chart(self, signal_data: Dict, chart_data: Dict = None) -> bool:
        """
        Send comprehensive trade alert with chart and interactive buttons
        
        Args:
            signal_data (Dict): Signal analysis data
            chart_data (Dict): Chart data for visualization
            
        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            return False
        
        # Check if alert conditions are met
        if not self._should_send_alert(signal_data):
            return False
        
        # Create unique signal key for cooldown
        symbol = signal_data.get('symbol', 'UNKNOWN')
        signal = signal_data.get('signal', 'WAIT')
        signal_key = f"{symbol}_{signal}_{datetime.now().strftime('%Y%m%d_%H%M')}"
        
        # Check cooldown
        if not self.check_cooldown(signal_key):
            logger.info(f"Advanced Telegram alert blocked by cooldown for {signal_key}")
            return False
        
        try:
            # Generate chart
            chart_image = self._generate_trade_chart(signal_data, chart_data)
            
            # Send chart with caption and buttons
            message = self._format_advanced_trade_alert(signal_data)
            
            # Send photo with caption and keyboard
            if chart_image:
                if self.interactive_enabled:
                    result = self._send_photo_with_buttons(chart_image, message, signal_key)
                else:
                    # Fallback to basic photo without buttons
                    result = self._send_photo_basic(chart_image, message)
            else:
                # Fallback to text message
                if self.interactive_enabled:
                    result = self._send_message_with_buttons(message, signal_key)
                else:
                    result = self.send_message(message)
            
            if result:
                self.last_alert_time[signal_key] = datetime.now()
                # Store pending trade for callback handling
                self.pending_trades[signal_key] = signal_data
                logger.info(f"Advanced Telegram alert sent for {signal}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error sending advanced Telegram alert: {e}")
            return False
    
    def _send_photo_basic(self, photo_data: bytes, caption: str) -> bool:
        """Send photo without interactive buttons (fallback)"""
        try:
            self.bot.send_photo(
                chat_id=self.chat_id,
                photo=photo_data,
                caption=caption
            )
            return True
        except Exception as e:
            logger.error(f"Error sending basic photo: {e}")
            return False
    
    def _generate_trade_chart(self, signal_data: Dict, chart_data: Dict = None) -> bytes:
        """
        Generate chart image with trade setup visualization
        
        Args:
            signal_data (Dict): Signal data
            chart_data (Dict): Historical price data
            
        Returns:
            bytes: Chart image data
        """
        try:
            # Create figure with professional styling
            plt.style.use('dark_background')
            fig, ax = plt.subplots(figsize=(12, 8), facecolor='#1a1a1a')
            ax.set_facecolor('#2a2a2a')
            
            # Use provided chart data or generate sample data
            if chart_data and 'close' in chart_data:
                prices = chart_data['close'][-50:]  # Last 50 candles
                dates = chart_data.index[-50:] if hasattr(chart_data, 'index') else pd.date_range(end=datetime.now(), periods=50, freq='5min')
            else:
                # Generate sample data around current price
                current_price = signal_data.get('entry_price', 1.1000)
                prices = [current_price + (i * 0.0001 * (1 if i % 2 == 0 else -1)) for i in range(50)]
                dates = pd.date_range(end=datetime.now(), periods=50, freq='5min')
            
            # Plot candlestick-style line chart
            ax.plot(dates, prices, color='#00ff88', linewidth=2, label='Price')
            
            # Add entry point
            entry_price = signal_data.get('entry_price', prices[-1])
            entry_time = dates[-1] if len(dates) > 0 else datetime.now()
            ax.scatter(entry_time, entry_price, color='#00ff00', s=100, marker='^', 
                      label=f'Entry: {entry_price:.5f}', zorder=5)
            
            # Add stop loss
            sl_price = signal_data.get('structure_sl', 0)
            if sl_price > 0:
                ax.axhline(y=sl_price, color='#ff4444', linestyle='--', linewidth=2, 
                           label=f'SL: {sl_price:.5f}', alpha=0.8)
            
            # Add take profit
            tp_price = signal_data.get('structure_tp', 0)
            if tp_price > 0:
                ax.axhline(y=tp_price, color='#44ff44', linestyle='--', linewidth=2, 
                           label=f'TP: {tp_price:.5f}', alpha=0.8)
            
            # Formatting
            ax.set_title(f'{signal_data.get("symbol", "UNKNOWN")} - {signal_data.get("signal", "WAIT")} Signal', 
                        fontsize=16, fontweight='bold', color='white')
            ax.set_xlabel('Time', fontsize=12, color='white')
            ax.set_ylabel('Price', fontsize=12, color='white')
            
            # Style the grid and ticks
            ax.grid(True, alpha=0.3, color='white')
            ax.tick_params(colors='white')
            ax.legend(facecolor='#2a2a2a', edgecolor='white', labelcolor='white')
            
            # Format x-axis
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Save to bytes
            buffer = io.BytesIO()
            plt.savefig(buffer, format='PNG', dpi=150, facecolor='#1a1a1a')
            buffer.seek(0)
            
            plt.close()
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generating chart: {e}")
            return None
    
    def _format_advanced_trade_alert(self, signal_data: Dict) -> str:
        """
        Format trade alert with Markdown/HTML styling
        
        Args:
            signal_data (Dict): Signal data
            
        Returns:
            str: Formatted message
        """
        symbol = signal_data.get('symbol', 'UNKNOWN')
        signal = signal_data.get('signal', 'WAIT')
        confidence = signal_data.get('confidence', 0)
        market_state = signal_data.get('market_state', 'UNKNOWN')
        htf_trend = signal_data.get('htf_trend', 'UNKNOWN')
        timeframe = signal_data.get('timeframe', 'UNKNOWN')
        
        entry_price = signal_data.get('entry_price', 0)
        stop_loss = signal_data.get('structure_sl', 0)
        take_profit = signal_data.get('structure_tp', 0)
        
        risk_reward = signal_data.get('risk_reward', {})
        rr_ratio = risk_reward.get('ratio', 0)
        
        reasons = signal_data.get('reasons', [])
        
        # Determine signal emoji
        signal_emoji = "📈" if signal == "BUY" else "📉" if signal == "SELL" else "⏳"
        
        # Format reasons
        reasons_text = "\n".join([f"• {reason}" for reason in reasons[:3]])
        
        message = f"""🚀 *TRADE ALERT* 🚀

*Pair:* {symbol}
*Timeframe:* {timeframe}
*Signal:* {signal_emoji} {signal}
*Confidence:* {confidence:.0f}%
*Market State:* {market_state}
*HTF Trend:* {htf_trend}

💰 *Entry:* {entry_price:.5f}
🛑 *Stop Loss:* {stop_loss:.5f}
🎯 *Take Profit:* {take_profit:.5f}
📊 *Risk:Reward:* {rr_ratio:.1f}:1

🧠 *Reason:*
{reasons_text}

*Use buttons below to take action* ⬇️"""
        
        return message
    
    def _send_photo_with_buttons(self, photo_data: bytes, caption: str, signal_key: str) -> bool:
        """
        Send photo with inline keyboard buttons
        
        Args:
            photo_data (bytes): Image data
            caption (str): Photo caption
            signal_key (str): Unique signal identifier
            
        Returns:
            bool: True if successful
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            
            # Create inline keyboard
            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '🚀 Execute Trade', 'callback_data': f'execute_{signal_key}'},
                        {'text': '❌ Ignore Trade', 'callback_data': f'ignore_{signal_key}'}
                    ],
                    [
                        {'text': '📊 View Chart', 'callback_data': f'chart_{signal_key}'}
                    ]
                ]
            }
            
            files = {
                'photo': ('chart.png', photo_data, 'image/png')
            }
            
            data = {
                'chat_id': self.chat_id,
                'caption': caption,
                'parse_mode': 'Markdown',
                'reply_markup': str(keyboard).replace("'", '"')
            }
            
            response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                logger.info("Photo with buttons sent successfully")
                return True
            else:
                logger.error(f"Failed to send photo: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return False
    
    def _send_message_with_buttons(self, message: str, signal_key: str) -> bool:
        """
        Send message with inline keyboard buttons
        
        Args:
            message (str): Message text
            signal_key (str): Unique signal identifier
            
        Returns:
            bool: True if successful
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            # Create inline keyboard
            keyboard = {
                'inline_keyboard': [
                    [
                        {'text': '🚀 Execute Trade', 'callback_data': f'execute_{signal_key}'},
                        {'text': '❌ Ignore Trade', 'callback_data': f'ignore_{signal_key}'}
                    ],
                    [
                        {'text': '📊 View Chart', 'callback_data': f'chart_{signal_key}'}
                    ]
                ]
            }
            
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': 'Markdown',
                'reply_markup': keyboard
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                logger.info("Message with buttons sent successfully")
                return True
            else:
                logger.error(f"Failed to send message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    def handle_callback_query(self, callback_data: str, callback_query_id: str) -> bool:
        """
        Handle button callback queries
        
        Args:
            callback_data (str): Callback data from button
            callback_query_id (str): Telegram callback query ID
            
        Returns:
            bool: True if handled successfully
        """
        try:
            # Parse callback data
            parts = callback_data.split('_', 1)
            action = parts[0]
            signal_key = parts[1] if len(parts) > 1 else ''
            
            # Acknowledge the callback
            self._answer_callback_query(callback_query_id)
            
            # Handle different actions
            if action == 'execute':
                return self._handle_execute_trade(signal_key)
            elif action == 'ignore':
                return self._handle_ignore_trade(signal_key)
            elif action == 'chart':
                return self._handle_view_chart(signal_key)
            else:
                logger.warning(f"Unknown callback action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling callback: {e}")
            return False
    
    def _handle_execute_trade(self, signal_key: str) -> bool:
        """
        Handle trade execution from Telegram button
        
        Args:
            signal_key (str): Signal identifier
            
        Returns:
            bool: True if executed successfully
        """
        try:
            signal_data = self.pending_trades.get(signal_key)
            if not signal_data:
                self._send_message("❌ Trade setup expired or not found")
                return False
            
            # Send execution confirmation
            message = f"""🚀 *EXECUTING TRADE* 🚀

*Pair:* {signal_data.get('symbol')}
*Signal:* {signal_data.get('signal')}
*Entry:* {signal_data.get('entry_price'):.5f}
*SL:* {signal_data.get('structure_sl'):.5f}
*TP:* {signal_data.get('structure_tp'):.5f}

*Trade is being placed...* ⏳"""
            
            self.send_message(message)
            
            # Here you would integrate with your trading system
            # For now, just log the action
            logger.info(f"Trade execution requested for {signal_key}")
            
            # Send confirmation
            self._send_message("✅ Trade execution request received!")
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            self._send_message(f"❌ Error executing trade: {e}")
            return False
    
    def _handle_ignore_trade(self, signal_key: str) -> bool:
        """
        Handle trade ignore from Telegram button
        
        Args:
            signal_key (str): Signal identifier
            
        Returns:
            bool: True if handled successfully
        """
        try:
            signal_data = self.pending_trades.get(signal_key)
            if not signal_data:
                return False
            
            # Remove from pending trades
            del self.pending_trades[signal_key]
            
            # Send confirmation
            message = f"""❌ *TRADE IGNORED* ❌

*Pair:* {signal_data.get('symbol')}
*Signal:* {signal_data.get('signal')}

*Trade setup has been ignored* 📋"""
            
            self.send_message(message)
            logger.info(f"Trade ignored for {signal_key}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error ignoring trade: {e}")
            return False
    
    def _handle_view_chart(self, signal_key: str) -> bool:
        """
        Handle chart view request from Telegram button
        
        Args:
            signal_key (str): Signal identifier
            
        Returns:
            bool: True if handled successfully
        """
        try:
            signal_data = self.pending_trades.get(signal_key)
            if not signal_data:
                return False
            
            # Regenerate and send chart
            chart_image = self._generate_trade_chart(signal_data)
            if chart_image:
                message = f"📊 *Chart for {signal_data.get('symbol')}* {signal_data.get('signal')}"
                self._send_photo_only(chart_image, message)
                return True
            else:
                self._send_message("❌ Could not generate chart")
                return False
                
        except Exception as e:
            logger.error(f"Error viewing chart: {e}")
            return False
    
    def _send_photo_only(self, photo_data: bytes, caption: str) -> bool:
        """
        Send photo without buttons
        
        Args:
            photo_data (bytes): Image data
            caption (str): Photo caption
            
        Returns:
            bool: True if successful
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
            
            files = {
                'photo': ('chart.png', photo_data, 'image/png')
            }
            
            data = {
                'chat_id': self.chat_id,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            
            response = requests.post(url, files=files, data=data, timeout=30)
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            return False
    
    def _answer_callback_query(self, callback_query_id: str, text: str = None) -> bool:
        """
        Answer callback query to remove loading state
        
        Args:
            callback_query_id (str): Callback query ID
            text (str): Optional alert text
            
        Returns:
            bool: True if successful
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/answerCallbackQuery"
            
            data = {
                'callback_query_id': callback_query_id,
                'text': text or "Action processed"
            }
            
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Error answering callback query: {e}")
            return False
    
    def send_trade_feedback(self, trade_data: Dict, feedback_type: str) -> bool:
        """
        Send trade feedback notifications
        
        Args:
            trade_data (Dict): Trade information
            feedback_type (str): Type of feedback (executed, sl_hit, tp_hit, breakeven)
            
        Returns:
            bool: True if sent successfully
        """
        if not self.enabled:
            return False
        
        try:
            symbol = trade_data.get('symbol', 'UNKNOWN')
            
            if feedback_type == 'executed':
                message = f"""✅ *TRADE EXECUTED* ✅

*Pair:* {symbol}
*Type:* {trade_data.get('type')}
*Volume:* {trade_data.get('volume')}
*Entry:* {trade_data.get('entry_price'):.5f}

*Trade placed successfully* 🚀"""
            
            elif feedback_type == 'sl_hit':
                profit = trade_data.get('profit', 0)
                message = f"""🛑 *STOP LOSS HIT* 🛑

*Pair:* {symbol}
*Reason:* Stop Loss Triggered
*Profit:* {profit:.2f} USD

*Trade closed automatically* 📊"""
            
            elif feedback_type == 'tp_hit':
                profit = trade_data.get('profit', 0)
                message = f"""🎯 *TAKE PROFIT HIT* 🎯

*Pair:* {symbol}
*Reason:* Take Profit Reached
*Profit:* {profit:.2f} USD

*Successful trade!* 💰"""
            
            elif feedback_type == 'breakeven':
                message = f"""🔄 *STOP LOSS MOVED* 🔄

*Pair:* {symbol}
*Action:* SL moved to break-even
*Entry:* {trade_data.get('entry_price'):.5f}

*Protecting profits* 🛡️"""
            
            else:
                return False
            
            return self.send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending trade feedback: {e}")
            return False
