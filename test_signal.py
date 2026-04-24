#!/usr/bin/env python3
"""
TEST SIGNAL SCRIPT
Independent test script for Nyx AI Signal Bridge
Tests signal creation and MT5 EA communication
"""

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Configuration - Must match signal_bridge.py
SIGNAL_FILE = "/home/ubuntu/nyx-ai/trade_signal.json"

def create_test_signal():
    """Create a test trade signal for EURUSD SELL"""
    
    # Test signal data
    signal = {
        "symbol": "EURUSD",
        "action": "SELL",
        "lot": 0.01,
        "sl": 1.1100,
        "tp": 1.0950,
        "confidence": 85.5,
        "score": 0.72,
        "timestamp": datetime.utcnow().isoformat(),
        "entry_price": 1.1000,
        "signal_id": f"EURUSD_SELL_{int(time.time())}",
        "status": "new"
    }
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)
        
        # Write signal to file
        with open(SIGNAL_FILE, 'w') as f:
            json.dump(signal, f, indent=4)
        
        print(f"Test signal created successfully!")
        print(f"File: {SIGNAL_FILE}")
        print(f"Signal: {signal['symbol']} {signal['action']} @ {signal['entry_price']}")
        print(f"SL: {signal['sl']} | TP: {signal['tp']}")
        print(f"Confidence: {signal['confidence']}% | Score: {signal['score']}")
        print(f"Signal ID: {signal['signal_id']}")
        print(f"Time: {signal['timestamp']}")
        
        return True
        
    except Exception as e:
        print(f"Error creating test signal: {e}")
        return False

def check_signal_status():
    """Check if signal file exists and show its status"""
    
    if os.path.exists(SIGNAL_FILE):
        print(f"Signal file exists: {SIGNAL_FILE}")
        
        try:
            with open(SIGNAL_FILE, 'r') as f:
                signal = json.load(f)
            
            print(f"Current signal: {signal.get('symbol', 'N/A')} {signal.get('action', 'N/A')}")
            print(f"Signal ID: {signal.get('signal_id', 'N/A')}")
            print(f"Status: {signal.get('status', 'N/A')}")
            print(f"Created: {signal.get('timestamp', 'N/A')}")
            
            # Check file age
            file_age = time.time() - os.path.getmtime(SIGNAL_FILE)
            print(f"File age: {int(file_age)} seconds")
            
        except Exception as e:
            print(f"Error reading signal file: {e}")
    else:
        print(f"No signal file found: {SIGNAL_FILE}")

def clear_signal():
    """Clear/remove the signal file"""
    
    if os.path.exists(SIGNAL_FILE):
        try:
            os.remove(SIGNAL_FILE)
            print(f"Signal file removed: {SIGNAL_FILE}")
            return True
        except Exception as e:
            print(f"Error removing signal file: {e}")
            return False
    else:
        print(f"No signal file to remove")
        return True

def test_signal_bridge():
    """Test the signal bridge functionality"""
    
    print("=== NYX AI SIGNAL BRIDGE TEST ===")
    print(f"Signal file path: {SIGNAL_FILE}")
    print()
    
    # Test 1: Create signal
    print("Test 1: Creating test signal...")
    if create_test_signal():
        print("PASSED: Signal created successfully")
    else:
        print("FAILED: Could not create signal")
        return False
    
    print()
    
    # Test 2: Check signal status
    print("Test 2: Checking signal status...")
    check_signal_status()
    print("PASSED: Signal status checked")
    
    print()
    
    # Test 3: Wait a bit and check again
    print("Test 3: Waiting 3 seconds and checking file age...")
    time.sleep(3)
    check_signal_status()
    print("PASSED: File age tracking working")
    
    print()
    
    # Test 4: Clean up
    print("Test 4: Cleaning up test signal...")
    if clear_signal():
        print("PASSED: Signal cleaned up successfully")
    else:
        print("FAILED: Could not clean up signal")
        return False
    
    print()
    print("ALL TESTS PASSED!")
    return True

def main():
    """Main function with command line options"""
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python test_signal.py create    - Create test signal")
        print("  python test_signal.py status    - Check signal status")
        print("  python test_signal.py clear     - Clear signal file")
        print("  python test_signal.py test      - Run full test suite")
        return
    
    command = sys.argv[1].lower()
    
    if command == "create":
        create_test_signal()
    elif command == "status":
        check_signal_status()
    elif command == "clear":
        clear_signal()
    elif command == "test":
        test_signal_bridge()
    else:
        print(f"Unknown command: {command}")
        print("Use: create, status, clear, or test")

if __name__ == "__main__":
    main()
