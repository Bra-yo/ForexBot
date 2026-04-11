"""
Advanced Telegram Alerts System
LEVEL 10.3: Comprehensive alert management for critical events
"""

import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any, Optional
import json
import os

logger = logging.getLogger(__name__)

class AdvancedTelegramAlerts:
    """
    Advanced Telegram Alerts System
    Manages all critical event notifications
    """
    
    def __init__(self, telegram_assistant=None, alert_config_file: str = "telegram_alerts_config.json"):
        self.telegram = telegram_assistant
        self.alert_config_file = alert_config_file
        self.alert_history = []
        self.rate_limits = {}  # Prevent spam
        self.last_daily_summary = None
        
        # Alert settings
        self.alert_settings = {
            'mt5_restart': True,
            'mt5_recovery_success': True,
            'mt5_recovery_failed': True,
            'elite_trade_override': True,
            'daily_performance': True,
            'critical_errors': True,
            'milestone_alerts': True
        }
        
        # Rate limiting (minutes)
        self.rate_limits_config = {
            'mt5_restart': 15,      # Max once per 15 minutes
            'elite_override': 30,     # Max once per 30 minutes
            'daily_summary': 1440,    # Max once per day
            'critical_error': 5         # Max once per 5 minutes
        }
        
        self.load_config()
        logger.info("Advanced Telegram Alerts initialized")
    
    def load_config(self):
        """Load alert configuration"""
        try:
            if os.path.exists(self.alert_config_file):
                with open(self.alert_config_file, 'r') as f:
                    config = json.load(f)
                    
                # Update settings
                if 'alert_settings' in config:
                    self.alert_settings.update(config['alert_settings'])
                
                if 'rate_limits' in config:
                    self.rate_limits_config.update(config['rate_limits'])
                
                logger.info("Alert configuration loaded")
            else:
                logger.info("No alert config file found, using defaults")
                
        except Exception as e:
            logger.error(f"Error loading alert config: {e}")
    
    def save_config(self):
        """Save alert configuration"""
        try:
            config = {
                'alert_settings': self.alert_settings,
                'rate_limits': self.rate_limits_config,
                'last_updated': datetime.now().isoformat()
            }
            
            with open(self.alert_config_file, 'w') as f:
                json.dump(config, f, indent=2)
                
            logger.debug("Alert configuration saved")
            
        except Exception as e:
            logger.error(f"Error saving alert config: {e}")
    
    def check_rate_limit(self, alert_type: str) -> bool:
        """Check if alert type is rate limited"""
        try:
            if alert_type not in self.rate_limits_config:
                return True  # Unknown alert type, allow
            
            # Check last sent time
            if alert_type in self.rate_limits:
                last_sent = self.rate_limits[alert_type]
                time_since = datetime.now() - last_sent
                
                # Convert minutes to timedelta
                limit_minutes = self.rate_limits_config[alert_type]
                limit_delta = timedelta(minutes=limit_minutes)
                
                if time_since < limit_delta:
                    logger.debug(f"Alert {alert_type} rate limited (sent {time_since.total_seconds():.0f}s ago)")
                    return False  # Rate limited
            
            return True  # Not rate limited
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # Allow on error
    
    def update_rate_limit(self, alert_type: str):
        """Update rate limit for alert type"""
        try:
            self.rate_limits[alert_type] = datetime.now()
            logger.debug(f"Rate limit updated for {alert_type}")
            
        except Exception as e:
            logger.error(f"Error updating rate limit: {e}")
    
    def send_alert(self, alert_type: str, message: str, priority: str = "NORMAL") -> bool:
        """Send alert with rate limiting and logging"""
        try:
            # Check if alert type is enabled
            if not self.alert_settings.get(alert_type, False):
                logger.debug(f"Alert type {alert_type} is disabled")
                return False
            
            # Check rate limiting
            if not self.check_rate_limit(alert_type):
                logger.debug(f"Alert {alert_type} rate limited")
                return False
            
            # Check if Telegram is available
            if not self.telegram:
                logger.warning("Telegram assistant not available for alerts")
                return False
            
            # Format message based on priority
            formatted_message = self.format_message(alert_type, message, priority)
            
            # Send alert
            success = self.telegram.send_message(formatted_message)
            
            if success:
                # Update rate limit
                self.update_rate_limit(alert_type)
                
                # Log alert
                alert_record = {
                    'type': alert_type,
                    'message': message,
                    'priority': priority,
                    'timestamp': datetime.now().isoformat(),
                    'sent': True
                }
                
                self.alert_history.append(alert_record)
                
                # Keep only last 100 alerts
                if len(self.alert_history) > 100:
                    self.alert_history = self.alert_history[-100:]
                
                logger.info(f"Alert sent: {alert_type} - {message}")
                return True
            else:
                logger.error(f"Failed to send alert: {alert_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending alert: {e}")
            return False
    
    def format_message(self, alert_type: str, message: str, priority: str) -> str:
        """Format alert message based on type and priority"""
        try:
            # Priority indicators
            priority_emoji = {
                'CRITICAL': '🚨',
                'HIGH': '⚠️',
                'NORMAL': 'ℹ️',
                'INFO': '📊'
            }
            
            emoji = priority_emoji.get(priority, 'ℹ️')
            
            # Alert type formatting
            type_prefixes = {
                'mt5_restart': 'VPS Watchdog',
                'mt5_recovery_success': 'VPS Watchdog',
                'mt5_recovery_failed': 'VPS Watchdog',
                'elite_trade_override': 'Elite Trade Override',
                'daily_performance': 'Daily Performance',
                'critical_errors': 'Critical Error',
                'milestone_alerts': 'Milestone'
            }
            
            prefix = type_prefixes.get(alert_type, 'Nyx AI')
            
            # Format based on priority
            if priority == 'CRITICAL':
                return f"{emoji} {prefix}: {message}"
            elif priority == 'HIGH':
                return f"{emoji} {prefix}: {message}"
            else:
                return f"{emoji} {prefix}: {message}"
                
        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            return f"ℹ️ {message}"
    
    def mt5_restart_alert(self, reason: str = "Connection lost") -> bool:
        """Send MT5 restart alert"""
        message = f"MT5 connection lost - attempting restart. Reason: {reason}"
        return self.send_alert('mt5_restart', message, 'HIGH')
    
    def mt5_recovery_success_alert(self) -> bool:
        """Send MT5 recovery success alert"""
        message = "MT5 recovery successful - connection restored"
        return self.send_alert('mt5_recovery_success', message, 'NORMAL')
    
    def mt5_recovery_failed_alert(self, attempts: int) -> bool:
        """Send MT5 recovery failed alert"""
        message = f"MT5 is down and could not restart automatically after {attempts} attempts. Manual intervention required!"
        return self.send_alert('mt5_recovery_failed', message, 'CRITICAL')
    
    def elite_trade_override_alert(self, trade_info: Dict[str, Any]) -> bool:
        """Send elite trade override alert"""
        symbol = trade_info.get('symbol', 'UNKNOWN')
        confidence = trade_info.get('confidence', 0)
        score = trade_info.get('score', 0)
        
        message = f"Elite trade override activated - executing beyond daily limit. Symbol: {symbol}, Confidence: {confidence}%, Score: {score}"
        return self.send_alert('elite_trade_override', message, 'HIGH')
    
    def daily_performance_alert(self, performance_data: Dict[str, Any]) -> bool:
        """Send daily performance summary"""
        try:
            # Check if we already sent today's summary
            today = date.today()
            
            if self.last_daily_summary == today:
                logger.debug("Daily summary already sent today")
                return False
            
            trades = performance_data.get('trades', 0)
            wins = performance_data.get('wins', 0)
            losses = performance_data.get('losses', 0)
            win_rate = performance_data.get('win_rate', 0)
            profit = performance_data.get('profit', 0)
            
            # Format performance summary
            if profit >= 0:
                profit_emoji = '📈'
                profit_status = f"+${profit:.2f}"
            else:
                profit_emoji = '📉'
                profit_status = f"-${abs(profit):.2f}"
            
            message = f"""Daily Performance Summary:
📊 Trades: {trades} (Wins: {wins}, Losses: {losses})
📈 Win Rate: {win_rate:.1f}%
💰 P&L: {profit_emoji} {profit_status}
⏰ Date: {today.strftime('%Y-%m-%d')}"""
            
            success = self.send_alert('daily_performance', message, 'INFO')
            
            if success:
                self.last_daily_summary = today
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending daily performance alert: {e}")
            return False
    
    def critical_error_alert(self, error_message: str, error_type: str = "System") -> bool:
        """Send critical error alert"""
        message = f"Critical Error ({error_type}): {error_message}"
        return self.send_alert('critical_errors', message, 'CRITICAL')
    
    def milestone_alert(self, milestone: str, details: str = "") -> bool:
        """Send milestone achievement alert"""
        message = f"Milestone Achieved: {milestone}"
        if details:
            message += f" - {details}"
        
        return self.send_alert('milestone_alerts', message, 'INFO')
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        try:
            # Count alerts by type
            alert_counts = {}
            recent_alerts = []
            
            # Count last 24 hours
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            for alert in self.alert_history:
                alert_time = datetime.fromisoformat(alert['timestamp'])
                
                if alert_time >= cutoff_time:
                    recent_alerts.append(alert)
                    
                    alert_type = alert['type']
                    alert_counts[alert_type] = alert_counts.get(alert_type, 0) + 1
            
            return {
                'total_alerts': len(self.alert_history),
                'recent_alerts_24h': len(recent_alerts),
                'alert_counts_by_type': alert_counts,
                'rate_limits_active': list(self.rate_limits.keys()),
                'enabled_alert_types': [k for k, v in self.alert_settings.items() if v],
                'last_daily_summary': self.last_daily_summary
            }
            
        except Exception as e:
            logger.error(f"Error getting alert statistics: {e}")
            return {}
    
    def get_status_report(self) -> str:
        """Get detailed alert system status"""
        stats = self.get_alert_statistics()
        
        report = f"""
ADVANCED TELEGRAM ALERTS STATUS
Alert Settings Enabled: {len([k for k, v in self.alert_settings.items() if v])}/{len(self.alert_settings)}
Rate Limits Active: {len(self.rate_limits)}

Alert Statistics (Last 24h):
- Total Alerts: {stats.get('recent_alerts_24h', 0)}
- By Type: {stats.get('alert_counts_by_type', {})}

Last Daily Summary: {self.last_daily_summary.strftime('%Y-%m-%d') if self.last_daily_summary else 'Never'}

Enabled Alert Types:
{chr(10).join([f"  ✅ {k}" if v else f"  ❌ {k}" for k, v in self.alert_settings.items()])}

Rate Limits (minutes):
{chr(10).join([f"  {k}: {v}min" for k, v in self.rate_limits_config.items()])}
        """.strip()
        
        return report
    
    def enable_alert_type(self, alert_type: str) -> bool:
        """Enable specific alert type"""
        try:
            self.alert_settings[alert_type] = True
            self.save_config()
            logger.info(f"Alert type enabled: {alert_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error enabling alert type: {e}")
            return False
    
    def disable_alert_type(self, alert_type: str) -> bool:
        """Disable specific alert type"""
        try:
            self.alert_settings[alert_type] = False
            self.save_config()
            logger.info(f"Alert type disabled: {alert_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error disabling alert type: {e}")
            return False
    
    def test_alert_system(self) -> bool:
        """Test alert system functionality"""
        try:
            test_message = "Alert system test - all systems operational"
            return self.send_alert('critical_errors', test_message, 'INFO')
            
        except Exception as e:
            logger.error(f"Error testing alert system: {e}")
            return False
