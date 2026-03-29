#!/usr/bin/env python3
"""
SIMPLE RULE TEST - Step 5: Very Simple Trading Rule
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_trading_manager import AutoTradingManager
import pandas as pd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def create_sample_data():
    """Create sample price data for backtesting"""
    import numpy as np
    
    # Generate 1000 candles of sample data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=1000, freq='h')
    
    # Simulate price movement
    price = 1.1000
    prices = []
    
    for i in range(1000):
        change = np.random.normal(0, 0.001)  # 0.1% standard deviation
        price *= (1 + change)
        prices.append(price)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * 1.002 for p in prices],  # 0.2% high
        'low': [p * 0.998 for p in prices],   # 0.2% low
        'close': prices,
        'volume': [1000000] * 1000
    })
    
    return df

def simple_rule_backtest():
    """Very simple rule: confidence >= 80%"""
    print("🔧 SIMPLE RULE TEST - CONFIDENCE >= 80%")
    print("="*50)
    
    # Initialize trading manager
    manager = AutoTradingManager(None, None)
    
    # Create sample data
    print("📊 Creating sample data...")
    df = create_sample_data()
    
    # Prepare ML data
    print("🧠 Preparing ML data...")
    ml_df = manager.prepare_ml_data(df)
    
    # Train model
    print("🎯 Training ML model...")
    model = manager.train_model(ml_df)
    
    if model is None:
        print("❌ Failed to train model")
        return
    
    print("\n" + "="*50)
    print("🔧 SIMPLE RULE: confidence >= 80%")
    print("No cooldown, no max trades, no filters")
    print("="*50)
    
    balance = 1000
    trades = []
    trade_count = 0
    
    for i in range(50, len(ml_df)-1):
        if trade_count >= 20:  # Reasonable limit
            break
            
        row = ml_df.iloc[i]
        
        # Get ML prediction
        signal, prob = manager.predict_signal(row)
        
        if signal is None:
            print(f"🚫 Skip: prediction failed")
            continue
        
        # SIMPLE RULE ONLY
        if prob >= 0.80:  # 80% confidence
            trade_count += 1
            
            prediction = 1 if signal == "BUY" else 0
            entry = ml_df.iloc[i]['close']
            exit_price = ml_df.iloc[i+1]['close']
            
            # Calculate profit
            if prediction == 1:  # BUY
                profit = (exit_price - entry) / entry
            else:  # SELL
                profit = (entry - exit_price) / entry
            
            profit_pct = profit * 100
            balance += profit_pct
            trades.append(profit_pct)
            
            print(f"✅ TRADE #{trade_count}: {signal} ({prob:.1%}) → {profit_pct:+.3f}%")
        else:
            print(f"🚫 Skip: confidence too low ({prob:.1%} < 80%)")
    
    # Results
    win_rate = sum(1 for t in trades if t > 0) / len(trades) if trades else 0
    total_return = (balance - 1000) / 1000
    
    print(f"\n📊 SIMPLE RULE RESULTS:")
    print(f"   Total Trades: {len(trades)}")
    print(f"   Win Rate: {win_rate:.1%}")
    print(f"   Total Return: {total_return:.1%}")
    print(f"   Final Balance: ${balance:,.2f}")
    
    if len(trades) > 0:
        print("✅ SIMPLE RULE WORKS - trades executed!")
    else:
        print("❌ SIMPLE RULE FAILED - no trades!")

if __name__ == "__main__":
    simple_rule_backtest()
