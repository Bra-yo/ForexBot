"""
VPS Watchdog System - MT5 Auto-Recovery
LEVEL 10.3: Advanced MT5 connection monitoring and recovery
"""

import logging
import time
import subprocess
import psutil
import os
from typing import Tuple, Optional
import MetaTrader5 as mt5

logger = logging.getLogger(__name__)

class VPSWatchdog:
    """
    VPS Watchdog System for MT5 Auto-Recovery
    Monitors MT5 connection and performs automatic recovery
    """
    
    def __init__(self, telegram_assistant=None):
        self.telegram = telegram_assistant
        self.restart_attempts = 0
        self.max_restart_attempts = 2
        self.last_check_time = 0
        self.check_interval = 30  # Check every 30 seconds
        self.mt5_process_name = "terminal64.exe"
        
        logger.info("VPS Watchdog initialized")
        logger.info(f"Max restart attempts: {self.max_restart_attempts}")
        logger.info(f"Check interval: {self.check_interval}s")
    
    def check_mt5_connection(self) -> bool:
        """Check if MT5 is properly connected.
        
        IMPORTANT: this must NOT call mt5.shutdown(). MetaTrader5's Python
        API uses one shared, process-wide connection - it is not a fresh
        connection per call. This function runs inside the live trading
        process (via watchdog_check(), called from execute_live_trade()),
        sharing that connection with every other part of the bot. The
        previous version called mt5.shutdown() even on its SUCCESS path,
        which tore down the only MT5 connection the whole bot depends on
        the very first time a real trade signal triggered this check -
        after which every subsequent get_historical_data() call returned
        empty (0 candles) for the rest of the run, since nothing else ever
        called mt5.initialize() again.
        """
        try:
            # Test MT5 connection
            if not mt5.initialize():
                logger.error("MT5 initialization failed")
                return False
            
            # Test account info
            account_info = mt5.account_info()
            if not account_info:
                logger.error("Cannot get account info")
                return False
            
            # Test terminal info
            terminal_info = mt5.terminal_info()
            if not terminal_info:
                logger.error("Cannot get terminal info")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"MT5 connection check error: {e}")
            return False
    
    def kill_mt5_process(self) -> bool:
        """Kill MT5 process safely"""
        try:
            killed = False
            
            # Find and kill MT5 processes
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'] == self.mt5_process_name:
                        logger.info(f"Killing MT5 process: PID {proc.info['pid']}")
                        proc.kill()
                        proc.wait(timeout=5)
                        killed = True
                except (psutil.NoSuchProcess, psutil.TimeoutExpired, psutil.AccessDenied):
                    continue
            
            if killed:
                logger.info("MT5 process killed successfully")
                return True
            else:
                logger.warning("No MT5 process found to kill")
                return True  # No process to kill is okay
                
        except Exception as e:
            logger.error(f"Error killing MT5 process: {e}")
            return False
    
    def restart_mt5(self) -> bool:
        """Restart MT5 application"""
        try:
            logger.info("Attempting to restart MT5...")
            
            # Common MT5 installation paths
            mt5_paths = [
                r"C:\Program Files\MetaTrader 5\terminal64.exe",
                r"C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
                r"C:\Users\{}\AppData\Roaming\MetaQuotes\Terminal\terminal64.exe".format(os.getenv('USERNAME')),
            ]
            
            mt5_exe = None
            for path in mt5_paths:
                if os.path.exists(path):
                    mt5_exe = path
                    break
            
            if not mt5_exe:
                logger.error("MT5 executable not found")
                return False
            
            # Start MT5
            subprocess.Popen([mt5_exe], shell=False)
            logger.info(f"MT5 restarted from: {mt5_exe}")
            
            # Wait for MT5 to start
            time.sleep(10)
            
            # Test connection
            if self.check_mt5_connection():
                logger.info("MT5 restart successful")
                return True
            else:
                logger.error("MT5 restart failed - connection still down")
                return False
                
        except Exception as e:
            logger.error(f"Error restarting MT5: {e}")
            return False
    
    def perform_recovery(self) -> bool:
        """Perform complete MT5 recovery sequence"""
        try:
            self.restart_attempts += 1
            logger.info(f"MT5 recovery attempt {self.restart_attempts}/{self.max_restart_attempts}")
            
            # Step 1: Kill MT5 process
            if not self.kill_mt5_process():
                logger.error("Failed to kill MT5 process")
                return False
            
            # Step 2: Wait 5 seconds
            logger.info("Waiting 5 seconds before restart...")
            time.sleep(5)
            
            # Step 3: Restart MT5
            if not self.restart_mt5():
                logger.error("Failed to restart MT5")
                return False
            
            # Step 4: Reinitialize MT5
            if not self.check_mt5_connection():
                logger.error("MT5 connection still failed after restart")
                return False
            
            logger.info("MT5 recovery completed successfully")
            self.restart_attempts = 0  # Reset counter on success
            return True
            
        except Exception as e:
            logger.error(f"MT5 recovery error: {e}")
            return False
    
    def send_alert(self, message: str):
        """Send Telegram alert"""
        try:
            if self.telegram:
                self.telegram.send_message(f"VPS Watchdog: {message}")
            logger.info(f"Alert sent: {message}")
        except Exception as e:
            logger.error(f"Failed to send alert: {e}")
    
    def watchdog_check(self) -> bool:
        """Main watchdog check function"""
        current_time = time.time()
        
        # Check if enough time has passed since last check
        if current_time - self.last_check_time < self.check_interval:
            return True  # Skip check, not time yet
        
        self.last_check_time = current_time
        
        # Check MT5 connection
        if not self.check_mt5_connection():
            logger.warning("MT5 connection lost - attempting restart")
            self.send_alert("MT5 connection lost - attempting restart")
            
            # Attempt recovery
            if self.perform_recovery():
                logger.info("MT5 recovery successful")
                self.send_alert("MT5 recovery successful")
                return True
            else:
                # Check if we've exceeded max attempts
                if self.restart_attempts >= self.max_restart_attempts:
                    logger.error("MT5 recovery failed - max attempts reached")
                    self.send_alert("MT5 is down and could not restart automatically")
                    return False
                else:
                    logger.warning(f"MT5 recovery failed, will retry... (attempt {self.restart_attempts})")
                    return False
        
        # Connection is good
        return True
    
    def reset_attempts(self):
        """Reset restart attempts counter"""
        self.restart_attempts = 0
        logger.info("Watchdog restart attempts reset")
    
    def get_status(self) -> dict:
        """Get current watchdog status"""
        return {
            'last_check': self.last_check_time,
            'restart_attempts': self.restart_attempts,
            'max_attempts': self.max_restart_attempts,
            'check_interval': self.check_interval,
            'mt5_connected': self.check_mt5_connection()
        }