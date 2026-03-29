"""
BOT CONTROL MANAGER
Handles lock files, single instance protection, and emergency stops
"""

import os
import sys
import time
import logging

logger = logging.getLogger(__name__)

class BotController:
    """Professional bot control and safety management"""
    
    def __init__(self):
        self.lock_file = "nyx.lock"
        self.stop_file = "stop.txt"
        self.pid_file = "nyx.pid"
        
    def check_single_instance(self):
        """Ensure only one bot instance runs"""
        if os.path.exists(self.lock_file):
            try:
                # Read existing PID
                with open(self.lock_file, 'r') as f:
                    existing_pid = int(f.read().strip())
                
                # Check if process is still running
                if self.is_process_running(existing_pid):
                    logger.error(f"Bot already running (PID: {existing_pid})")
                    print("❌ ERROR: Nyx AI Bot is already running!")
                    print(f"   Existing process ID: {existing_pid}")
                    print("   Please stop the existing bot first")
                    return False
                else:
                    logger.info("Stale lock file found - cleaning up")
                    self.cleanup_lock_files()
                    
            except Exception as e:
                logger.error(f"Error checking lock file: {e}")
                
        # Create new lock file with current PID
        try:
            current_pid = os.getpid()
            with open(self.lock_file, 'w') as f:
                f.write(str(current_pid))
            
            with open(self.pid_file, 'w') as f:
                f.write(str(current_pid))
                
            logger.info(f"Lock file created - PID: {current_pid}")
            print(f"✅ Bot instance started - PID: {current_pid}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create lock file: {e}")
            return False
            
    def is_process_running(self, pid):
        """Check if process with given PID is still running"""
        try:
            # On Unix-like systems
            if os.name == 'posix':
                os.kill(pid, 0)  # Send signal 0 to check if process exists
                return True
            else:
                # On Windows
                import psutil
                return psutil.pid_exists(pid)
        except OSError:
            return False
        except ImportError:
            # If psutil not available, assume process exists
            return True
        except Exception:
            return False
            
    def check_emergency_stop(self):
        """Check for emergency stop file"""
        if os.path.exists(self.stop_file):
            logger.warning("Emergency stop file detected")
            print("🚨 EMERGENCY STOP FILE DETECTED")
            try:
                os.remove(self.stop_file)
                logger.info("Emergency stop file removed")
                return True
            except Exception as e:
                logger.error(f"Failed to remove stop file: {e}")
        return False
        
    def cleanup_lock_files(self):
        """Clean up all control files"""
        try:
            for file in [self.lock_file, self.stop_file, self.pid_file]:
                if os.path.exists(file):
                    os.remove(file)
                    logger.info(f"Removed control file: {file}")
        except Exception as e:
            logger.error(f"Error cleaning up control files: {e}")
            
    def create_stop_file(self):
        """Create emergency stop file"""
        try:
            with open(self.stop_file, 'w') as f:
                f.write("EMERGENCY STOP")
            logger.info("Emergency stop file created")
            return True
        except Exception as e:
            logger.error(f"Failed to create stop file: {e}")
            return False
            
    def get_current_pid(self):
        """Get current process ID"""
        return os.getpid()
        
    def __enter__(self):
        """Context manager entry"""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup"""
        self.cleanup_lock_files()
        logger.info("Bot control files cleaned up")
