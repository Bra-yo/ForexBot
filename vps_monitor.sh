#!/bin/bash
# VPS MONITORING SCRIPT FOR NYX AI
echo "📊 Nyx AI Bot Monitor"
echo "========================"

# Check if bot is running
if pgrep -f "python3.*start_multi_pair_trading" > /dev/null; then
    echo "✅ Bot is running"
    
    # Check recent trades
    echo "📈 Recent activity:"
    python3 -c "
import MetaTrader5 as mt5
if mt5.initialize():
    positions = mt5.positions_get()
    if positions:
        for pos in positions[-5:]:  # Last 5 positions
            print(f'  {pos.symbol}: {pos.type} {pos.volume} lots @ {pos.price_open:.5f}')
    else:
        print('  No open positions')
    mt5.shutdown()
"
else
    echo "❌ Bot is NOT running"
    echo "🔄 Restarting..."
    # Start bot
    cd /path/to/your/project  # 🔧 UPDATE THIS PATH
    nohup python3 start_multi_pair_trading_fixed.py > bot.log 2>&1 &
    echo "✅ Bot restarted"
fi

echo ""
echo "📊 System status:"
echo "  Memory: $(free -h | awk '/^Mem:/ {print $3"/"$2}')"
echo "  Disk: $(df -h . | awk 'NR==2{print $4}')"
echo "  Uptime: $(uptime -p | cut -d',' -f1 | xargs)"
echo "========================"
echo "Checked at: $(date)"
