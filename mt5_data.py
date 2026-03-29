import MetaTrader5 as mt5
import pandas as pd


def connect_mt5():
    """Connect to MetaTrader 5 terminal"""
    if not mt5.initialize():
        raise Exception("MT5 initialization failed")
    
    print("Connected to MT5")
    
    # Get account info
    account_info = mt5.account_info()
    if account_info:
        print(f"Account: {account_info.login}")
        print(f"Balance: ${account_info.balance:,.2f}")
        print(f"Server: {account_info.server}")
    
    return True


def get_data(symbol="EURUSD", timeframe=mt5.TIMEFRAME_M15, bars=1000):
    """Get real market data from MT5"""
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, bars)
    
    if rates is None:
        raise Exception(f"Failed to get data for {symbol}")
    
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    print(f"Retrieved {len(df)} candles for {symbol}")
    print(f"Date range: {df['time'].min()} to {df['time'].max()}")
    print(f"Price range: {df['low'].min():.5f} - {df['high'].max():.5f}")
    
    return df


def get_symbols():
    """Get available symbols from MT5"""
    symbols = mt5.symbols_get()
    if symbols:
        print(f"Available symbols: {len(symbols)}")
        forex_symbols = [s.name for s in symbols if "USD" in s.name and len(s.name) == 6]
        print(f"Forex pairs: {len(forex_symbols)}")
        return forex_symbols[:10]  # Return first 10
    return []


def shutdown_mt5():
    """Shutdown MT5 connection"""
    mt5.shutdown()
    print("MT5 connection closed")


def add_indicators(df):
    """Add technical indicators to dataframe"""
    # EMAs for trend detection
    df['ema_fast'] = df['close'].ewm(span=20).mean()
    df['ema_slow'] = df['close'].ewm(span=50).mean()
    
    # EMA difference and percentage
    df['ema_diff'] = df['ema_fast'] - df['ema_slow']
    df['ema_diff_pct'] = df['ema_diff'] / df['close']
    
    # Additional indicators
    df['rsi'] = calculate_rsi(df['close'])
    df['atr'] = calculate_atr(df)
    df['volatility'] = df['high'].rolling(20).std() / df['close']
    
    return df


def calculate_rsi(prices, period=14):
    """Calculate RSI indicator"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_atr(df, period=14):
    """Calculate Average True Range"""
    high_low = df['high'] - df['low']
    high_close = abs(df['high'] - df['close'].shift())
    low_close = abs(df['low'] - df['close'].shift())
    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = true_range.rolling(period).mean()
    return atr


def get_trend_strength(row):
    """Get trend strength based on EMA difference"""
    diff = row['ema_diff_pct']
    
    if abs(diff) < 0.0002:
        return "no_trade"   # dead market
    elif abs(diff) < 0.0005:
        return "weak"
    elif abs(diff) < 0.0015:
        return "moderate"
    else:
        return "strong"


def get_trend_direction(row):
    """Get trend direction based on EMA alignment"""
    if row['ema_fast'] > row['ema_slow']:
        return "up"
    else:
        return "down"
