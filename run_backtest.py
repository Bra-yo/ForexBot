#!/usr/bin/env python3
"""
Manual Backtesting Script with REAL MT5 Data
Run this to test your AI trading system with real market data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auto_trading_manager import AutoTradingManager
from mt5_data import connect_mt5, get_data, add_indicators, get_trend_strength, get_trend_direction, shutdown_mt5
import MetaTrader5 as mt5
import pandas as pd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_real_data():
    """Get real market data from MT5"""
    try:
        # Connect to MT5
        connect_mt5()
        
        # Get real data
        df = get_data(symbol="EURUSD", timeframe=mt5.TIMEFRAME_M15, bars=1500)
        
        # Add indicators
        df = add_indicators(df)
        
        # Rename columns to match expected format
        df = df.rename(columns={
            'time': 'timestamp',
            'open': 'open',
            'high': 'high', 
            'low': 'low',
            'close': 'close',
            'tick_volume': 'volume'
        })
        
        return df
        
    except Exception as e:
        logger.error(f"Error getting real data: {e}")
        return None
    
    finally:
        # Always shutdown MT5
        shutdown_mt5()

def run_backtest():
    """Run complete backtesting process with real data"""
    logger.info("Starting Backtesting Process with REAL MT5 Data")
    
    # Get real market data
    df = get_real_data()
    if df is None:
        logger.error("Failed to get real data, exiting")
        return
    
    logger.info(f"Data loaded: {len(df)} candles")
    logger.info(f"Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    
    # Initialize trading manager (for backtesting, no MT5 connection needed)
    manager = AutoTradingManager(None, None)
    
    # Prepare ML data
    logger.info("Preparing ML data...")
    ml_df = manager.prepare_ml_data(df)
    
    # Train ML model
    logger.info("Training ML model...")
    model = manager.train_model(ml_df)
    
    if model is None:
        logger.error("Failed to train model")
        return
    
    # Run backtest with real data
    logger.info("Running backtest with real market data...")
    results = manager.backtest_strategy(ml_df, model)
    
    # Display results
    if results:
        logger.info("BACKTEST RESULTS:")
        logger.info(f"   Final Balance: ${results['final_balance']:,.2f}")
        logger.info(f"   Total Return: {results['total_return']:.1%}")
        logger.info(f"   Win Rate: {results['win_rate']:.1%}")
        logger.info(f"   Total Trades: {results['total_trades']}")
        logger.info(f"   Skipped Trades: {results['skipped_trades']}")
        logger.info(f"   Avg Profit: ${results['avg_profit']:.2f}")
    else:
        logger.error("Backtest failed")

if __name__ == "__main__":
    run_backtest()
