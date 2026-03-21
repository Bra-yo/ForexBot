"""
📊 Trading Engine Monitor - Real-time Trading Activity
Shows detailed trading engine logs and activity
"""
import json
import time
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

def read_trading_state():
    """Read shared state from trading engine"""
    try:
        with open("trading_state.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # Trading engine hasn't started yet, return default state
        return {
            'timestamp': datetime.now().isoformat(),
            'market_open': False,
            'mt5_connected': False,
            'active_trades': [],
            'daily_loss': 0.0,
            'signals': {},
            'account_info': {}
        }
    except:
        return {
            'timestamp': datetime.now().isoformat(),
            'market_open': False,
            'mt5_connected': False,
            'active_trades': [],
            'daily_loss': 0.0,
            'signals': {},
            'account_info': {}
        }

def clear_screen():
    """Clear console screen"""
    import os
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print header"""
    print("=" * 60)
    print("📊 BrayoForexBot - Trading Engine Monitor")
    print("=" * 60)
    print(f"🕒 Last Update: {datetime.now().strftime('%H:%M:%S')}")
    print()

def print_trading_status(state):
    """Print trading status"""
    print("🎯 TRADING STATUS")
    print("-" * 30)
    
    # Market status
    market_status = "🟢 OPEN" if state['market_open'] else "🔴 CLOSED"
    print(f"Market: {market_status}")
    
    # MT5 connection
    mt5_status = "🟢 Connected" if state['mt5_connected'] else "🔴 Disconnected"
    print(f"MT5: {mt5_status}")
    
    # Active trades count
    active_count = len(state.get('active_trades', []))
    print(f"Active Trades: {active_count}")
    
    # Daily loss
    daily_loss = state.get('daily_loss', 0)
    loss_color = "🔴" if daily_loss > 0 else "🟢"
    print(f"Daily P&L: {loss_color} ${daily_loss:.2f}")
    print()

def print_signals(state):
    """Print current signals"""
    signals = state.get('signals', {})
    if not signals:
        print("📋 No signals available")
        return
    
    print("🎯 CURRENT SIGNALS")
    print("-" * 30)
    
    decision = signals.get('decision', 'HOLD')
    strength = signals.get('strength', 0)
    symbol = signals.get('symbol', 'N/A')
    timeframe = signals.get('timeframe', 'N/A')
    
    # Signal emoji
    signal_emoji = {
        'BUY': '🟢', 'SELL': '🔴', 'HOLD': '🟡'
    }.get(decision, '⚪')
    
    print(f"Signal: {signal_emoji} {decision}")
    print(f"Strength: {strength}/10")
    print(f"Symbol: {symbol}")
    print(f"Timeframe: {timeframe}")
    
    # Technical indicators
    rsi = signals.get('rsi', 0)
    sma = signals.get('sma', 0)
    ema = signals.get('ema', 0)
    
    print(f"RSI(14): {rsi:.1f}")
    print(f"SMA(20): {sma:.5f}")
    print(f"EMA(20): {ema:.5f}")
    
    # Trend
    trend = "📈 Uptrend" if ema > sma else "📉 Downtrend"
    print(f"Trend: {trend}")
    print()

def print_active_trades(state):
    """Print detailed active trades"""
    active_trades = state.get('active_trades', [])
    
    if not active_trades:
        print("📋 No active trades")
        return
    
    print("📊 ACTIVE TRADES")
    print("-" * 30)
    
    for i, trade in enumerate(active_trades, 1):
        print(f"📈 Trade #{i}: {trade.get('symbol', 'N/A')} - {trade.get('type', 'Unknown')}")
        print(f"   Ticket: {trade.get('ticket', 'N/A')}")
        print(f"   Volume: {trade.get('volume', 0):.2f} lots")
        print(f"   Entry: {trade.get('price', 0):.5f}")
        print(f"   SL: {trade.get('sl', 0):.5f}")
        print(f"   TP: {trade.get('tp', 0):.5f}")
        
        # Calculate profit and pips
        profit = trade.get('profit', 0)
        profit_color = "🟢" if profit >= 0 else "🔴"
        print(f"   Profit: {profit_color} ${profit:.2f}")
        
        # Calculate pips
        if trade.get('type') == 'BUY':
            pips = (trade.get('current_price', 0) - trade.get('price', 0)) / 0.00001
        else:
            pips = (trade.get('price', 0) - trade.get('current_price', 0)) / 0.00001
        
        print(f"   Pips: {pips:.1f}")
        print(f"   Current: {trade.get('current_price', 0):.5f}")
        print()

def print_account_info(state):
    """Print account information"""
    account_info = state.get('account_info', {})
    
    if not account_info:
        print("🏦 No account data available")
        return
    
    print("🏦 ACCOUNT INFORMATION")
    print("-" * 30)
    
    balance = account_info.get('balance', 0)
    equity = account_info.get('equity', 0)
    free_margin = account_info.get('free_margin', 0)
    profit = account_info.get('profit', 0)
    
    print(f"Balance: ${balance:.2f}")
    print(f"Equity: ${equity:.2f}")
    print(f"Free Margin: ${free_margin:.2f}")
    
    profit_color = "🟢" if profit >= 0 else "🔴"
    print(f"Profit: {profit_color} ${profit:.2f}")
    print()

def main():
    """Main monitoring loop"""
    print("📊 BrayoForexBot - Trading Engine Monitor")
    print("🔄 Real-time Trading Activity Monitor")
    print("📝 Press CTRL+C to stop monitoring")
    print()
    
    try:
        while True:
            # Clear screen and show header
            clear_screen()
            print_header()
            
            # Read current state
            state = read_trading_state()
            
            # Show all information
            print_trading_status(state)
            print_signals(state)
            print_active_trades(state)
            print_account_info(state)
            
            # Show instructions
            print("🎛️ CONTROLS")
            print("-" * 20)
            print("• Trading Engine: Running independently")
            print("• Dashboard: http://localhost:8502")
            print("• Press CTRL+C here to stop monitoring")
            print("• Press CTRL+C in engine to stop trading")
            print()
            
            # Wait 2 seconds before refresh
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n🛑 Trading Engine Monitor Stopped")
    except Exception as e:
        print(f"\n❌ Monitor Error: {str(e)}")

if __name__ == "__main__":
    main()
