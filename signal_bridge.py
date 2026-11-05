"""
SIGNAL BRIDGE SYSTEM
Replaces MT5 Python dependency with JSON file-based communication
for Linux compatibility with Wine + MT5 architecture.

Architecture:
AI Bot (Python) -> JSON Signal File -> MT5 EA (Wine) -> Trade Execution
"""

import json
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

# Configuration - file NAMES only. The directory is resolved at runtime
# (see _resolve_signal_dir) so this works on Windows, Linux and Wine.
SIGNAL_FILE = "trade_signal.json"
SIGNAL_LOCK_FILE = "signal.lock"
SIGNAL_CONSUMED_FILE = "signal_consumed.json"
SIGNAL_TIMEOUT = 300  # 5 minutes timeout for signal consumption
MAX_SIGNAL_AGE = 60   # 1 minute max age for new signals

# Setup logging
logger = logging.getLogger(__name__)

def _resolve_signal_dir(signal_dir=None) -> Path:
    """
    Pick the folder the EA reads from. Order:
      1. explicit argument
      2. NYX_SIGNAL_DIR environment variable
      3. MT5 terminal's MQL5/Files folder (where the EA can read it)
      4. ./signals next to the bot
    """
    if signal_dir:
        return Path(signal_dir)
    env_dir = os.environ.get("NYX_SIGNAL_DIR")
    if env_dir:
        return Path(env_dir)
    try:
        import MetaTrader5 as mt5
        info = mt5.terminal_info()
        if info is not None and getattr(info, "data_path", None):
            return Path(info.data_path) / "MQL5" / "Files"
    except Exception:
        pass
    return Path(__file__).resolve().parent / "signals"


class SignalBridge:
    """Manages JSON-based signal communication between AI bot and MT5 EA"""
    
    def __init__(self, signal_dir: Optional[str] = None):
        self.signal_dir = _resolve_signal_dir(signal_dir)
        self.signal_file = self.signal_dir / SIGNAL_FILE
        self.lock_file = self.signal_dir / SIGNAL_LOCK_FILE
        self.consumed_file = self.signal_dir / SIGNAL_CONSUMED_FILE
        
        # Ensure signal directory exists
        self.signal_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean up old locks on startup
        self._cleanup_old_locks()
        
        logger.info(f"Signal Bridge writing to: {self.signal_dir}")
    
    def _cleanup_old_locks(self):
        """Clean up old lock files from crashed sessions"""
        try:
            if self.lock_file.exists():
                lock_age = time.time() - self.lock_file.stat().st_mtime
                if lock_age > SIGNAL_TIMEOUT:
                    self.lock_file.unlink()
                    logger.warning("Cleaned up old signal lock")
        except Exception as e:
            logger.error(f"Error cleaning up locks: {e}")
    
    def _is_signal_pending(self) -> bool:
        """Check if there's a pending signal that hasn't been consumed"""
        try:
            if not self.signal_file.exists():
                return False
            
            # Check file age
            file_age = time.time() - self.signal_file.stat().st_mtime
            if file_age > SIGNAL_TIMEOUT:
                # Signal is too old, remove it
                self.signal_file.unlink()
                logger.warning("Removed expired signal file")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking signal status: {e}")
            return False
    
    def _create_lock(self) -> bool:
        """Create a lock file to prevent duplicate signals"""
        try:
            if self.lock_file.exists():
                return False
            
            with open(self.lock_file, 'w') as f:
                f.write(f"locked_{time.time()}")
            
            return True
        except Exception as e:
            logger.error(f"Error creating lock: {e}")
            return False
    
    def _release_lock(self):
        """Release the lock file"""
        try:
            if self.lock_file.exists():
                self.lock_file.unlink()
        except Exception as e:
            logger.error(f"Error releasing lock: {e}")
    
    def send_signal(self, symbol: str, action: str, lot: float, sl: float, 
                   tp: float, confidence: float, score: float, 
                   entry_price: Optional[float] = None) -> bool:
        """
        Send a trade signal to MT5 via JSON file
        
        Args:
            symbol: Trading symbol (e.g., 'EURUSD')
            action: 'BUY' or 'SELL'
            lot: Lot size
            sl: Stop loss price
            tp: Take profit price
            confidence: Signal confidence (0-100)
            score: Signal score (0-1)
            entry_price: Optional entry price
        
        Returns:
            bool: True if signal sent successfully, False otherwise
        """
        try:
            # Check if there's already a pending signal
            if self._is_signal_pending():
                logger.warning("Previous signal not yet consumed - skipping new signal")
                return False
            
            # Create lock to prevent race conditions
            if not self._create_lock():
                logger.warning("Could not create signal lock - another process may be sending")
                return False
            
            # Prepare signal data
            signal = {
                "symbol": symbol,
                "action": action.upper(),
                "lot": lot,
                "sl": sl,
                "tp": tp,
                "confidence": confidence,
                "score": score,
                "timestamp": datetime.utcnow().isoformat(),
                "entry_price": entry_price,
                "signal_id": f"{symbol}_{action}_{int(time.time())}",
                "status": "new"  # Signal lock improvement - track processing status
            }
            
            # Write signal to file
            with open(self.signal_file, 'w') as f:
                json.dump(signal, f, indent=4)
            
            logger.info(f"Signal exported: {symbol} {action} | Score: {score:.3f} | Lot: {lot}")
            
            # Release lock
            self._release_lock()
            
            return True
            
        except Exception as e:
            logger.error(f"Signal export failed: {e}")
            self._release_lock()
            return False
    
    def get_signal_status(self) -> Dict[str, Any]:
        """Get the status of the current signal"""
        try:
            if not self.signal_file.exists():
                return {"status": "no_signal", "message": "No signal file"}
            
            with open(self.signal_file, 'r') as f:
                signal = json.load(f)
            
            file_age = time.time() - self.signal_file.stat().st_mtime
            
            status = {
                "status": "pending",
                "signal": signal,
                "age_seconds": int(file_age),
                "message": f"Signal pending for {int(file_age)}s"
            }
            
            # Check if signal is too old
            if file_age > SIGNAL_TIMEOUT:
                status["status"] = "expired"
                status["message"] = f"Signal expired ({int(file_age)}s old)"
            
            return status
            
        except Exception as e:
            logger.error(f"Error getting signal status: {e}")
            return {"status": "error", "message": str(e)}
    
    def mark_signal_consumed(self, execution_result: Dict[str, Any]):
        """Mark a signal as consumed by MT5 EA"""
        try:
            if not self.signal_file.exists():
                logger.warning("No signal file to mark as consumed")
                return
            
            # Read the signal
            with open(self.signal_file, 'r') as f:
                signal = json.load(f)
            
            # Create consumed record
            consumed_record = {
                "original_signal": signal,
                "execution_result": execution_result,
                "consumed_timestamp": datetime.utcnow().isoformat()
            }
            
            # Save to consumed file
            with open(self.consumed_file, 'w') as f:
                json.dump(consumed_record, f, indent=4)
            
            # Remove the signal file
            self.signal_file.unlink()
            
            logger.info(f"Signal marked as consumed: {signal.get('symbol')} {signal.get('action')}")
            
        except Exception as e:
            logger.error(f"Error marking signal consumed: {e}")
    
    def clear_signal(self):
        """Clear any pending signal (emergency use)"""
        try:
            if self.signal_file.exists():
                self.signal_file.unlink()
                logger.info("Signal file cleared")
            
            self._release_lock()
            
        except Exception as e:
            logger.error(f"Error clearing signal: {e}")

# Global signal bridge instance
signal_bridge = SignalBridge()

# Convenience functions for backward compatibility
def send_signal(symbol: str, action: str, lot: float, sl: float, 
                tp: float, confidence: float, score: float,
                entry_price: Optional[float] = None) -> bool:
    """Convenience function to send a signal"""
    return signal_bridge.send_signal(symbol, action, lot, sl, tp, confidence, score, entry_price)

def get_signal_status() -> Dict[str, Any]:
    """Convenience function to get signal status"""
    return signal_bridge.get_signal_status()

def clear_signal():
    """Convenience function to clear signal"""
    signal_bridge.clear_signal()

if __name__ == "__main__":
    # Test the signal bridge
    logging.basicConfig(level=logging.INFO)
    
    print("Testing Signal Bridge...")
    
    # Test sending a signal
    result = send_signal("EURUSD", "BUY", 0.01, 1.1000, 1.1100, 85.5, 0.72)
    print(f"Signal sent: {result}")
    
    # Check status
    status = get_signal_status()
    print(f"Signal status: {status}")
    
    # Mark as consumed
    signal_bridge.mark_signal_consumed({"success": True, "ticket": 12345})
    
    # Check status again
    status = get_signal_status()
    print(f"Signal status after consumption: {status}")