"""
Example Usage of the Professional Backtesting System
Shows how to use all components together
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
import matplotlib.pyplot as plt

# Import our professional components
from backtest import BacktestEngine
from analytics.metrics import PerformanceMetrics
from logs.trade_journal import TradeJournal
from optimizer import StrategyOptimizer

def enhanced_rsi_strategy(data: pd.DataFrame, 
                         rsi_period: int = 14,
                         rsi_oversold: float = 30,
                         rsi_overbought: float = 70,
                         ma_period: int = 20,
                         risk_reward: float = 2.0) -> Dict:
    """
    Enhanced RSI strategy with multiple parameters for optimization
    """
    if len(data) < max(rsi_period, ma_period) + 10:
        return {'action': 'WAIT'}
    
    # Calculate RSI
    close = data['close']
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    # Calculate Moving Average
    ma = close.rolling(window=ma_period).mean()
    
    current_rsi = rsi.iloc[-1]
    current_price = close.iloc[-1]
    current_ma = ma.iloc[-1]
    
    # Enhanced signal logic
    signal = {'action': 'WAIT'}
    
    # Buy conditions
    if (current_rsi < rsi_oversold and 
        current_price > current_ma and  # Trend confirmation
        rsi.iloc[-2] >= rsi_oversold):  # RSI crossing oversold
        
        stop_loss = current_price * 0.98  # 2% stop loss
        take_profit = current_price + (current_price - stop_loss) * risk_reward
        
        signal = {
            'action': 'BUY',
            'pair': 'EUR/USD',
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'signal_strength': max(0, (rsi_oversold - current_rsi) / rsi_oversold * 100)
        }
    
    # Sell conditions
    elif (current_rsi > rsi_overbought and 
          current_price < current_ma and  # Trend confirmation
          rsi.iloc[-2] <= rsi_overbought):  # RSI crossing overbought
        
        stop_loss = current_price * 1.02  # 2% stop loss
        take_profit = current_price - (stop_loss - current_price) * risk_reward
        
        signal = {
            'action': 'SELL',
            'pair': 'EUR/USD',
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'signal_strength': max(0, (current_rsi - rsi_overbought) / (100 - rsi_overbought) * 100)
        }
    
    return signal

def get_sample_data(pair: str = 'EURUSD=X', period: str = '2y') -> pd.DataFrame:
    """Get sample forex data for testing"""
    print(f"📊 Downloading {pair} data for {period}...")
    
    try:
        ticker = yf.Ticker(pair)
        data = ticker.history(period=period, interval='1h')
        
        if data.empty:
            print("❌ No data found, creating sample data...")
            # Create sample data for testing
            dates = pd.date_range(start='2022-01-01', end='2024-01-01', freq='1h')
            np.random.seed(42)
            
            price = 1.1000
            prices = [price]
            
            for _ in range(len(dates) - 1):
                change = np.random.normal(0, 0.001)  # 0.1% standard deviation
                price *= (1 + change)
                prices.append(price)
            
            data = pd.DataFrame({
                'open': prices,
                'high': [p * (1 + abs(np.random.normal(0, 0.002))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.002))) for p in prices],
                'close': prices,
                'volume': np.random.randint(1000, 10000, len(prices))
            }, index=dates)
        
        # Clean column names
        data.columns = [col.lower() for col in data.columns]
        print(f"✅ Got {len(data)} data points")
        return data
        
    except Exception as e:
        print(f"❌ Error getting data: {e}")
        return pd.DataFrame()

def run_basic_backtest():
    """Run basic backtest example"""
    print("\n🔥 BASIC BACKTEST EXAMPLE")
    print("=" * 50)
    
    # Get data
    data = get_sample_data()
    if data.empty:
        return
    
    # Create backtest engine
    backtest = BacktestEngine(initial_balance=10000)
    
    # Run backtest
    results = backtest.run_backtest(data, enhanced_rsi_strategy)
    
    # Print results
    backtest.print_summary(results)
    
    # Plot results
    backtest.plot_results(results)
    
    return results

def run_performance_analysis():
    """Run performance analysis example"""
    print("\n📊 PERFORMANCE ANALYSIS EXAMPLE")
    print("=" * 50)
    
    # Get data and run backtest
    data = get_sample_data()
    if data.empty:
        return
    
    backtest = BacktestEngine(initial_balance=10000)
    results = backtest.run_backtest(data, enhanced_rsi_strategy)
    
    # Analyze performance
    metrics = PerformanceMetrics()
    performance_metrics = metrics.calculate_all_metrics(
        results['trades'], 
        results['equity_curve'], 
        results['initial_balance']
    )
    
    # Generate report
    report = metrics.generate_report(performance_metrics)
    print(report)
    
    # Plot dashboard
    metrics.plot_performance_dashboard(
        performance_metrics, 
        results['trades'], 
        results['equity_curve']
    )
    
    return performance_metrics

def run_trade_journaling():
    """Run trade journaling example"""
    print("\n📝 TRADE JOURNALING EXAMPLE")
    print("=" * 50)
    
    # Get data and run backtest
    data = get_sample_data()
    if data.empty:
        return
    
    backtest = BacktestEngine(initial_balance=10000)
    results = backtest.run_backtest(data, enhanced_rsi_strategy)
    
    # Create trade journal
    journal = TradeJournal()
    
    # Record all trades
    for i, trade in enumerate(results['trades']):
        trade_data = {
            'trade_id': f"BT_{i+1}",
            'pair': trade.get('pair', 'EUR/USD'),
            'action': trade.get('action', 'BUY'),
            'entry_price': trade.get('entry_price'),
            'exit_price': trade.get('exit_price'),
            'entry_time': trade.get('entry_time', datetime.now()),
            'exit_time': trade.get('exit_time', datetime.now()),
            'position_size': trade.get('size', 0.01),
            'stop_loss': trade.get('stop_loss', 0),
            'take_profit': trade.get('take_profit', 0),
            'pnl': trade.get('pnl', 0),
            'commission': trade.get('commission', 0),
            'duration_hours': trade.get('duration', 0),
            'strategy': 'Enhanced RSI',
            'signal_strength': 75.0,
            'market_conditions': 'Volatile',
            'notes': f"Backtest trade #{i+1}"
        }
        journal.record_trade(trade_data)
    
    # Get statistics
    stats = journal.get_trade_statistics()
    print(f"📈 Journal Statistics:")
    print(f"• Total Trades: {stats.get('total_trades', 0)}")
    print(f"• Win Rate: {stats.get('win_rate', 0):.1f}%")
    print(f"• Total P&L: ${stats.get('total_pnl', 0):.2f}")
    
    # Generate journal report
    report = journal.generate_journal_report('logs/journal_report.txt')
    print(report)
    
    # Export to CSV
    journal.export_to_csv('logs/trades_export.csv')
    print("📁 Trades exported to CSV")
    
    return journal

def run_strategy_optimization():
    """Run strategy optimization example"""
    print("\n🧠 STRATEGY OPTIMIZATION EXAMPLE")
    print("=" * 50)
    
    # Get data
    data = get_sample_data()
    if data.empty:
        return
    
    # Define parameter grid for optimization
    parameter_grid = {
        'rsi_period': [10, 14, 20],
        'rsi_oversold': [25, 30, 35],
        'rsi_overbought': [65, 70, 75],
        'ma_period': [15, 20, 25],
        'risk_reward': [1.5, 2.0, 2.5]
    }
    
    print(f"🔍 Testing {len(parameter_grid)} parameters...")
    
    # Create optimizer
    optimizer = StrategyOptimizer(data, initial_balance=10000)
    
    # Run grid search optimization
    grid_results = optimizer.grid_search(
        enhanced_rsi_strategy,
        parameter_grid,
        metric='total_return_pct',
        maximize=True,
        parallel=True
    )
    
    print(f"\n🏆 OPTIMIZATION RESULTS:")
    print(f"Best Parameters: {grid_results['best_parameters']}")
    print(f"Best Return: {grid_results['best_metrics']['total_return_pct']:.2f}%")
    print(f"Win Rate: {grid_results['best_metrics']['win_rate']:.1f}%")
    print(f"Profit Factor: {grid_results['best_metrics']['profit_factor']:.2f}")
    
    # Plot optimization results
    optimizer.plot_optimization_results(grid_results)
    
    # Save results
    optimizer.save_optimization_results(grid_results, 'logs/optimization_results.json')
    
    return grid_results

def run_walk_forward_analysis():
    """Run walk-forward analysis example"""
    print("\n🚶 WALK-FORWARD ANALYSIS EXAMPLE")
    print("=" * 50)
    
    # Get more data for walk-forward
    data = get_sample_data(period='3y')
    if data.empty:
        return
    
    # Define smaller parameter grid for walk-forward (faster)
    parameter_grid = {
        'rsi_period': [12, 14, 16],
        'rsi_oversold': [28, 30, 32],
        'rsi_overbought': [68, 70, 72],
        'risk_reward': [1.8, 2.0, 2.2]
    }
    
    # Create optimizer
    optimizer = StrategyOptimizer(data, initial_balance=10000)
    
    # Run walk-forward optimization
    wf_results = optimizer.walk_forward_optimization(
        enhanced_rsi_strategy,
        parameter_grid,
        train_periods=500,  # 500 hours training
        test_periods=100,   # 100 hours testing
        metric='total_return_pct'
    )
    
    print(f"\n📊 WALK-FORWARD RESULTS:")
    print(f"Total Train Return: {wf_results['total_train_return']:.2f}%")
    print(f"Total Test Return: {wf_results['total_test_return']:.2f}%")
    print(f"Overfitting Ratio: {wf_results['overfitting_ratio']:.2f}")
    
    # Plot walk-forward results
    optimizer.plot_optimization_results(wf_results)
    
    return wf_results

def run_genetic_algorithm():
    """Run genetic algorithm optimization example"""
    print("\n🧬 GENETIC ALGORITHM EXAMPLE")
    print("=" * 50)
    
    # Get data
    data = get_sample_data()
    if data.empty:
        return
    
    # Define parameter ranges
    param_ranges = {
        'rsi_period': (10, 25),
        'rsi_oversold': (20, 40),
        'rsi_overbought': (60, 80),
        'ma_period': (10, 30),
        'risk_reward': (1.0, 3.0)
    }
    
    # Create optimizer
    optimizer = StrategyOptimizer(data, initial_balance=10000)
    
    # Run genetic algorithm
    ga_results = optimizer.genetic_algorithm(
        enhanced_rsi_strategy,
        param_ranges,
        population_size=30,
        generations=50,
        mutation_rate=0.1,
        metric='total_return_pct',
        maximize=True
    )
    
    print(f"\n🧬 GENETIC ALGORITHM RESULTS:")
    print(f"Best Parameters: {ga_results['best_parameters']}")
    print(f"Best Return: {ga_results['best_metrics']['total_return_pct']:.2f}%")
    print(f"Win Rate: {ga_results['best_metrics']['win_rate']:.1f}%")
    
    # Plot evolution
    optimizer.plot_optimization_results(ga_results)
    
    return ga_results

def main():
    """Main function to run all examples"""
    print("🚀 PROFESSIONAL BACKTESTING SYSTEM DEMO")
    print("=" * 60)
    
    # Create logs directory
    import os
    os.makedirs('logs', exist_ok=True)
    
    try:
        # 1. Basic Backtest
        print("\n1️⃣ Running Basic Backtest...")
        basic_results = run_basic_backtest()
        
        # 2. Performance Analysis
        print("\n2️⃣ Running Performance Analysis...")
        performance_metrics = run_performance_analysis()
        
        # 3. Trade Journaling
        print("\n3️⃣ Running Trade Journaling...")
        journal = run_trade_journaling()
        
        # 4. Strategy Optimization (Grid Search)
        print("\n4️⃣ Running Strategy Optimization...")
        optimization_results = run_strategy_optimization()
        
        # 5. Walk-Forward Analysis
        print("\n5️⃣ Running Walk-Forward Analysis...")
        wf_results = run_walk_forward_analysis()
        
        # 6. Genetic Algorithm
        print("\n6️⃣ Running Genetic Algorithm...")
        ga_results = run_genetic_algorithm()
        
        print("\n🎉 ALL EXAMPLES COMPLETED SUCCESSFULLY!")
        print("📁 Check the logs/ folder for saved results")
        
    except KeyboardInterrupt:
        print("\n👋 Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Error in demo: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
