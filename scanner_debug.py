"""
Scanner Debug Tool - Test and verify integrated scanner functionality
"""

import threading
import time
import logging
from datetime import datetime
from integrated_scanner import get_integrated_scanner, start_integrated_scanner, stop_integrated_scanner

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def show_scanner_status():
    """Display current scanner status in console"""
    scanner = get_integrated_scanner()
    
    if scanner:
        status = scanner.get_scanner_status()
        
        print("\n" + "="*60)
        print("🔍 SCANNER STATUS REPORT")
        print("="*60)
        print(f"📊 Scanner Running: {status['running']}")
        print(f"🧵 Thread Alive: {status['thread_alive']}")
        print(f"💱 Symbols: {status['symbols_count']}")
        print(f"⏱️ Timeframes: {status['timeframes_count']}")
        print(f"📈 Total Combinations: {status['symbols_count'] * status['timeframes_count']}")
        
        print("\n📋 LAST SIGNALS:")
        for symbol in status['last_signals']:
            for timeframe in status['last_signals'][symbol]:
                last_signal = status['last_signals'][symbol][timeframe]
                if last_signal:
                    print(f"   {symbol} {timeframe}: {last_signal}")
                else:
                    print(f"   {symbol} {timeframe}: No signal")
        
        print("\n" + "="*60)
        
        return True
    else:
        print("❌ Scanner not initialized")
        return False

def test_scanner_cycle():
    """Run one test cycle and show results"""
    print("\n🧪 RUNNING TEST SCAN CYCLE...")
    
    scanner = get_integrated_scanner()
    if not scanner:
        print("❌ Scanner not available - starting first...")
        start_integrated_scanner()
        time.sleep(2)  # Wait for startup
        scanner = get_integrated_scanner()
    
    if scanner:
        print("✅ Scanner available - running test cycle...")
        
        # Force one scan cycle
        try:
            scanner._scan_all_pairs()
            print("✅ Test scan cycle completed")
            
            # Show updated status
            time.sleep(1)
            show_scanner_status()
            
        except Exception as e:
            print(f"❌ Test cycle error: {e}")
            import traceback
            traceback.print_exc()

def interactive_menu():
    """Interactive menu for scanner control"""
    while True:
        print("\n" + "="*50)
        print("🔍 SCANNER DEBUG MENU")
        print("="*50)
        print("1. 📊 Show Scanner Status")
        print("2. 🧪 Run Test Scan Cycle") 
        print("3. 🚀 Start Continuous Scanner")
        print("4. 🛑 Stop Scanner")
        print("5. ❌ Exit")
        print("="*50)
        
        try:
            choice = input("\nEnter your choice (1-5): ").strip()
            
            if choice == '1':
                show_scanner_status()
            elif choice == '2':
                test_scanner_cycle()
            elif choice == '3':
                print("🚀 Starting continuous scanner...")
                start_integrated_scanner()
            elif choice == '4':
                print("🛑 Stopping scanner...")
                stop_integrated_scanner()
            elif choice == '5':
                print("👋 Goodbye!")
                break
            else:
                print("❌ Invalid choice - try again")
                
        except KeyboardInterrupt:
            print("\n👋 Exiting debug menu...")
            break
        except Exception as e:
            print(f"❌ Menu error: {e}")

if __name__ == "__main__":
    print("🔍 SCANNER DEBUG TOOL")
    print("This tool helps you verify the integrated scanner is working properly")
    print("You can check status, run test cycles, and control the scanner")
    
    interactive_menu()
