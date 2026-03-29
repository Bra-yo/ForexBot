#!/usr/bin/env python3
"""
DEBUG Backtesting Script - Step-by-Step Debugging
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

def run_debug_backtest():
    """Run debugging backtest step-by-step"""
    print("🔧 DEBUG BACKTEST - STEP BY STEP")
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
    print("🔧 STEP 1: REGULAR BACKTEST (WITH DEBUG PRINTING)")
    print("="*50)
    
    # Run regular backtest with debug printing
    results1 = manager.backtest_strategy(ml_df, model)
    
    print("\n" + "="*50)
    print("🔧 STEP 2: DEBUG BACKTEST (FORCE ALL TRADES)")
    print("="*50)
    
    # Run debug backtest (force all trades)
    results2 = manager.backtest_strategy_debug(ml_df, model)
    
    print("\n" + "="*50)
    print("📊 COMPARISON RESULTS")
    print("="*50)
    print("REGULAR BACKTEST:")
    print(f"   Trades: {results1['total_trades']}")
    print(f"   Win Rate: {results1['win_rate']:.1%}")
    print(f"   Return: {results1['total_return']:.1%}")
    
    print("\nDEBUG BACKTEST (Forced):")
    print(f"   Trades: {results2['total_trades']}")
    print(f"   Win Rate: {results2['win_rate']:.1%}")
    print(f"   Return: {results2['total_return']:.1%}")
    
    print("\n🔧 ANALYSIS:")
    if results2['total_trades'] > 0:
        print("✅ ML predictions are working")
        if results1['total_trades'] == 0:
            print("❌ Your filters are blocking ALL trades")
        else:
            print("✅ Some trades pass filters")
    else:
        print("❌ ML predictions are NOT working")

if __name__ == "__main__":
    run_debug_backtest()
