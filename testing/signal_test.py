"""
Test trading signal generation
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

try:
    from technical_analysis import TechnicalAnalysis
    import pandas as pd
    import numpy as np
    
    print('Testing trading signal generation...')
    
    # Create sample market data
    dates = pd.date_range(start='2023-01-01', periods=100, freq='1h')
    np.random.seed(42)
    
    market_data = pd.DataFrame({
        'timestamp': dates,
        'open': 1.1000 + np.random.randn(100) * 0.001,
        'high': 1.1000 + np.random.randn(100) * 0.002,
        'low': 1.1000 + np.random.randn(100) * 0.002,
        'close': 1.1000 + np.random.randn(100) * 0.001,
        'volume': np.random.randint(1000, 10000, 100)
    })
    market_data.set_index('timestamp', inplace=True)
    
    # Calculate indicators
    ta = TechnicalAnalysis()
    rsi = ta.calculate_rsi(market_data['close'], period=14)
    sma_fast, sma_slow = ta.calculate_moving_averages(market_data['close'])
    
    latest_rsi = rsi.iloc[-1]
    latest_sma = sma_fast.iloc[-1]
    latest_ema = sma_slow.iloc[-1]
    latest_price = market_data['close'].iloc[-1]
    
    print(f'Latest RSI: {latest_rsi:.1f}')
    print(f'Latest SMA: {latest_sma:.5f}')
    print(f'Latest EMA: {latest_ema:.5f}')
    print(f'Latest Price: {latest_price:.5f}')
    
    # Generate trading signal
    signal_strength = 0
    reasons = []
    
    if latest_rsi < 30:
        signal_strength += 2
        reasons.append(f'RSI oversold ({latest_rsi:.1f})')
    elif latest_rsi > 70:
        signal_strength -= 2
        reasons.append(f'RSI overbought ({latest_rsi:.1f})')
    
    if latest_ema > latest_sma:
        signal_strength += 1
        reasons.append('EMA above SMA (uptrend)')
    elif latest_ema < latest_sma:
        signal_strength -= 1
        reasons.append('EMA below SMA (downtrend)')
    
    # Final decision
    if signal_strength >= 2:
        decision = 'BUY'
        confidence = min(90, 60 + signal_strength * 10)
    elif signal_strength <= -2:
        decision = 'SELL'
        confidence = min(90, 60 + abs(signal_strength) * 10)
    else:
        decision = 'WAIT'
        confidence = 50
    
    print(f'\nSIGNAL: {decision}')
    print(f'CONFIDENCE: {confidence:.0f}%')
    reasons_str = ' | '.join(reasons) if reasons else 'Neutral conditions'
    print(f'REASONS: {reasons_str}')
    
    # Calculate SL/TP
    stop_loss_pips = 20
    if decision == 'BUY':
        stop_loss_price = latest_price - (stop_loss_pips * 0.0001)
        take_profit_price = latest_price + (stop_loss_pips * 0.00015)
    else:
        stop_loss_price = latest_price + (stop_loss_pips * 0.0001)
        take_profit_price = latest_price - (stop_loss_pips * 0.00015)
    
    print(f'ENTRY: {latest_price:.5f}')
    print(f'STOP LOSS: {stop_loss_price:.5f}')
    print(f'TAKE PROFIT: {take_profit_price:.5f}')
    
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
