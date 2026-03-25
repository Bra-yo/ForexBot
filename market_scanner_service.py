"""
Market Scanner Service - Independent Multi-Pair Multi-Timeframe Scanner
Runs completely separate from dashboard for continuous market monitoring
"""

import logging
import time
import signal
import sys
import os
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from brokers.mt5_connector import MT5Connector
from advanced_telegram_assistant import AdvancedTelegramAssistant
from market_scanner import MarketScanner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('market_scanner.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

class MarketScannerService:
    """Main service for running the market scanner"""
    
    def __init__(self):
        self.scanner = None
        self.running = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("MarketScannerService initialized")
    
    def start(self):
        """Start the market scanner service"""
        try:
            logger.info("Starting Market Scanner Service...")
            
            # Initialize MT5 connector
            logger.info("Connecting to MetaTrader 5...")
            mt5_connector = MT5Connector()
            
            # Test connection
            account_info = mt5_connector.get_account_info()
            if 'error' in account_info:
                logger.error(f"MT5 connection failed: {account_info['error']}")
                return False
            
            logger.info(f"MT5 connected - Account: {account_info['login']}")
            
            # Initialize Telegram assistant
            logger.info("Initializing Telegram assistant...")
            telegram_assistant = AdvancedTelegramAssistant()
            
            if not telegram_assistant.enabled:
                logger.warning("Telegram not configured - alerts disabled")
            else:
                logger.info("Telegram assistant ready")
            
            # Initialize market scanner
            logger.info("Initializing market scanner...")
            self.scanner = MarketScanner(mt5_connector, telegram_assistant)
            
            # Configure scanner settings
            self.scanner.set_scan_delay(3)  # 3 seconds between scans
            self.scanner.set_cooldown_minutes(15)  # 15 minutes cooldown per pair/tf
            
            logger.info("Scanner configuration:")
            logger.info(f"  - Pairs: 15 total (majors, crosses, metals)")
            logger.info(f"  - Timeframes: 7 total (M5, M15, M30, H1, H4)")
            logger.info(f"  - Scan delay: 3 seconds")
            logger.info(f"  - Cooldown: 15 minutes")
            logger.info(f"  - Max workers: 5 concurrent scans")
            
            # Test Telegram connection
            if telegram_assistant.enabled:
                logger.info("Testing Telegram connection...")
                if telegram_assistant.test_connection():
                    logger.info("Telegram test successful")
                else:
                    logger.warning("Telegram test failed")
            
            # Start scanning
            self.running = True
            logger.info("Starting continuous market scanning...")
            self.scanner.start_scanning()
            
            # Main service loop
            self._service_loop()
            
        except Exception as e:
            logger.error(f"Error starting service: {e}")
            return False
    
    def _service_loop(self):
        """Main service loop for monitoring and stats"""
        stats_counter = 0
        
        while self.running:
            try:
                time.sleep(60)  # Check every minute
                
                if self.scanner and self.scanner.scanning:
                    stats_counter += 1
                    
                    # Log stats every 10 minutes
                    if stats_counter % 10 == 0:
                        stats = self.scanner.get_stats()
                        logger.info(f"""
📊 Scanner Status (Last 10 min):
- Total Scans: {stats['total_scans']}
- Signals Found: {stats['signals_found']}
- Signals Sent: {stats['signals_sent']}
- Avg Duration: {stats['scan_duration_avg']:.2f}s
- Last Scan: {stats['last_scan_time'].strftime('%H:%M:%S') if stats['last_scan_time'] else 'N/A'}
                        """)
                
            except Exception as e:
                logger.error(f"Error in service loop: {e}")
    
    def stop(self):
        """Stop the market scanner service"""
        logger.info("Stopping Market Scanner Service...")
        self.running = False
        
        if self.scanner:
            self.scanner.stop_scanning()
            
            # Log final stats
            stats = self.scanner.get_stats()
            logger.info(f"""
Final Scanner Statistics:
- Total Scans: {stats['total_scans']}
- Signals Found: {stats['signals_found']}
- Signals Sent: {stats['signals_sent']}
- Avg Scan Duration: {stats['scan_duration_avg']:.2f}s
            """)
        
        logger.info("Market Scanner Service stopped")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum} - shutting down...")
        self.stop()
        sys.exit(0)

def main():
    """Main entry point"""
    print("""
MARKET SCANNER SERVICE
================================
Multi-Pair Multi-Timeframe Scanner
Independent from Dashboard

Features:
- 15 Currency Pairs + Gold
- 7 Timeframes (M5-H4)
- Continuous Scanning
- Telegram Alerts
- Anti-Spam Protection
- Performance Optimized

Starting service...
    """)
    
    service = MarketScannerService()
    
    try:
        success = service.start()
        if not success:
            logger.error("Failed to start service")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        service.stop()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        service.stop()
        sys.exit(1)

if __name__ == "__main__":
    main()
