#!/bin/bash
# VPS STARTUP SCRIPT FOR NYX AI
echo "🚀 Starting Nyx AI Trading Bot..."
echo "📊 Date: $(date)"
echo "🌐 Server: $(hostname)"
echo ""

# Check Python
if ! command -v python3 &> /dev/null
then
    echo "❌ Python3 not found"
    exit 1
fi

# Navigate to project directory
cd /path/to/your/project  # 🔧 UPDATE THIS PATH

# Check MT5 connection
echo "🔍 Checking MT5 connection..."
python3 -c "
import MetaTrader5 as mt5
if mt5.initialize():
    print('✅ MT5 Connected')
    account = mt5.account_info()
    print(f'💰 Account: {account.login}')
    print(f'💎 Balance: ${account.balance:.2f}')
    mt5.shutdown()
else:
    print('❌ MT5 Connection failed')
    exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🚀 Starting trading bot..."
    echo "⏰ Started at: $(date)"
    echo ""
    
    # Start the bot
    python3 start_multi_pair_trading_fixed.py
else
    echo "❌ MT5 connection failed - aborting"
    exit 1
fi
