#!/usr/bin/env python3
"""
View Backtesting Results
Check your backtesting performance
"""

import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

def view_results():
    """View and analyze backtesting results"""
    
    print("🔍 BACKTESTING RESULTS VIEWER")
    print("="*40)
    
    # Check for results file
    if os.path.exists("backtest_results.txt"):
        print("\n📁 Found backtest_results.txt:")
        print("-" * 30)
        with open("backtest_results.txt", "r") as f:
            print(f.read())
    
    # Check for trades CSV
    if os.path.exists("trades.csv"):
        print("\n📊 Trade History (trades.csv):")
        print("-" * 30)
        df = pd.read_csv("trades.csv")
        
        if not df.empty:
            # Basic statistics
            total_trades = len(df)
            wins = len(df[df['result'] == 'WIN'])
            losses = len(df[df['result'] == 'LOSS'])
            win_rate = wins / total_trades
            
            print(f"Total Trades: {total_trades}")
            print(f"Wins: {wins}")
            print(f"Losses: {losses}")
            print(f"Win Rate: {win_rate:.1%}")
            
            if 'profit' in df.columns:
                total_profit = df['profit'].sum()
                avg_profit = df['profit'].mean()
                print(f"Total Profit: {total_profit:.2f}%")
                print(f"Average Profit: {avg_profit:.2f}%")
                
                # Create equity curve
                df['cumulative_profit'] = df['profit'].cumsum()
                
                plt.figure(figsize=(12, 6))
                plt.plot(df['cumulative_profit'])
                plt.title("Equity Curve")
                plt.xlabel("Trade Number")
                plt.ylabel("Cumulative Profit (%)")
                plt.grid(True)
                plt.savefig("equity_curve.png")
                print("📈 Equity curve saved as equity_curve.png")
    
    # Check for equity curve
    if os.path.exists("equity_curve.png"):
        print("\n📈 Equity curve available: equity_curve.png")
    
    # Check logs for backtest results
    print("\n🔍 Checking logs for backtest results...")
    log_files = []
    for file in os.listdir('.'):
        if file.endswith('.log'):
            log_files.append(file)
    
    for log_file in log_files:
        try:
            with open(log_file, 'r') as f:
                content = f.read()
                if "Backtest Results:" in content:
                    print(f"\n📊 Found in {log_file}:")
                    print("-" * 30)
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if "Backtest Results:" in line:
                            # Print next 5 lines
                            for j in range(1, 6):
                                if i + j < len(lines):
                                    print(lines[i + j])
                            break
        except:
            continue

def run_quick_backtest():
    """Run a quick backtest if no results found"""
    print("\n🚀 No results found. Running quick backtest...")
    os.system("python run_backtest.py")

if __name__ == "__main__":
    view_results()
    
    # If no results found, offer to run backtest
    if not any(os.path.exists(f) for f in ["backtest_results.txt", "trades.csv"]):
        response = input("\nNo backtest results found. Run backtest now? (y/n): ")
        if response.lower() == 'y':
            run_quick_backtest()
            print("\nBacktest completed! Run this script again to view results.")
