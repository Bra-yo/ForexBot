"""
Debug script to test scanner imports
"""

import sys
import os
import traceback

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(project_root, 'brokers'))

print(f"Project root: {project_root}")
print(f"Python path: {sys.path[-1]}")

try:
    from mt5_connector import MT5Connector
    print("✅ MT5Connector import: OK")
except Exception as e:
    print(f"❌ MT5Connector import: {e}")
    traceback.print_exc()

try:
    from technical_analysis import TechnicalAnalysis
    print("✅ TechnicalAnalysis import: OK")
except Exception as e:
    print(f"❌ TechnicalAnalysis import: {e}")
    traceback.print_exc()

try:
    from advanced_telegram_assistant import AdvancedTelegramAssistant
    print("✅ AdvancedTelegramAssistant import: OK")
except Exception as e:
    print(f"❌ AdvancedTelegramAssistant import: {e}")
    traceback.print_exc()

print("\n🚀 All imports tested!")
