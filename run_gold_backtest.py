"""
Backtest the REAL live signal engine (TechnicalAnalysis.advanced_signal_analysis
in technical_analysis.py) against historical XAUUSD data - the exact same
pipeline now wired into MultiPairLiveBot.get_signal() for live trading.

MUST BE RUN ON YOUR WINDOWS MACHINE, WITH THE MT5 TERMINAL OPEN AND LOGGED IN.
(Needs MetaTrader5 + TA-Lib installed, same as the live bot.)

Usage:
    python run_gold_backtest.py                      # last 6 months, M15
    python run_gold_backtest.py --months 12
    python run_gold_backtest.py --start 2025-01-01 --end 2025-12-31
    python run_gold_backtest.py --timeframe M30

Output:
    Prints a full summary (return, win rate, profit factor, Sharpe, drawdown)
    and saves an equity curve chart to gold_backtest_results.png
"""

import argparse
import sys
from datetime import datetime, timedelta
import pandas as pd

sys.path.insert(0, 'backtesting')

# Force a non-interactive backend before matplotlib.pyplot gets imported by
# anything (backtest.py imports it). Belt-and-suspenders alongside the fix
# in backtest.py's plot_results() itself - this script should never block
# waiting for a popup window to be closed, especially when running multiple
# backtests back-to-back unattended (--timeframe all).
import matplotlib
matplotlib.use('Agg')

from brokers.mt5_connector import MT5Connector
from technical_analysis import TechnicalAnalysis
from backtest import BacktestEngine  # backtesting/backtest.py

SYMBOL = "XAUUSD"
HTF_WARMUP_DAYS = 45     # extra H4 history before the backtest start, for EMA200 warmup
TRAILING_WINDOW = 300    # candles of context fed into the analysis engine per decision


class OfflineHTFConnector:
    """
    Drop-in stand-in for MT5Connector, used only for the higher-timeframe
    trend lookups inside advanced_signal_analysis(). Serves data from
    pre-fetched DataFrames instead of hitting MT5 live on every candle, and
    respects `as_of` so it never leaks future bars into a historical
    decision (see technical_analysis.py's as_of parameter).

    IMPORTANT: analyze_higher_timeframe_trend() requests H4 data for
    M1/M5/M15/M30 base signals, but D1 data for H1/H4/D1 base signals - two
    DIFFERENT higher timeframes depending on what's being analyzed. An
    earlier version of this class only ever held H4 data and served it
    regardless of which timeframe was actually requested, meaning every H1
    backtest run so far silently used H4 data mislabeled as "D1" for its
    trend check. This version holds both series and routes correctly.
    """

    def __init__(self, htf_data_by_timeframe: dict):
        self.htf_data_by_timeframe = htf_data_by_timeframe  # {'H4': df, 'D1': df}
        self.connected = True

    def get_historical_data(self, symbol, timeframe, start_date, end_date):
        data = self.htf_data_by_timeframe.get(timeframe)
        if data is None:
            return None
        return data.loc[:end_date]


def fetch_data(connector, symbol, timeframe, start_date, end_date, label):
    print(f"Fetching {label}...")
    data = connector.get_historical_data(symbol=symbol, timeframe=timeframe,
                                          start_date=start_date, end_date=end_date)
    if data is None or data.empty:
        # The MT5 Python connection can go stale after several minutes of
        # this process not touching MT5 at all (e.g. during the previous
        # timeframe's multi-minute backtest loop, which only calls into the
        # offline HTF connector, never real MT5). A single re-initialize
        # covers this without needing to guess the exact cause - this is
        # exactly what broke the M15/M30/H1 comparison run: M15 fetched
        # fine, then M30 came back empty after the long M15 backtest loop.
        print(f"  No data on first attempt - reconnecting to MT5 and retrying...")
        connector.initialize()
        data = connector.get_historical_data(symbol=symbol, timeframe=timeframe,
                                              start_date=start_date, end_date=end_date)

    if data is None or data.empty:
        # Different failure mode from the stale-connection case above: this
        # one fails even on a fresh connection. Most likely cause for the
        # finer timeframes (M1 especially) is that the broker simply doesn't
        # retain that much history at that granularity - 6 months of M1 is
        # ~260,000 candles, versus ~11,000 for M15 over the same window, and
        # demo servers in particular often cap how far back 1-minute data
        # goes. Rather than guess the exact cutoff, back off to
        # progressively shorter windows (holding end_date fixed) until the
        # broker actually has data, and report exactly what was used so the
        # comparison table stays honest about it.
        for days_back in [90, 30, 14, 7]:
            shrunk_start = end_date - timedelta(days=days_back)
            if shrunk_start <= start_date:
                continue  # not actually shorter than what already failed
            print(f"  Still no data - broker likely doesn't retain {timeframe} history "
                  f"that far back. Trying the last {days_back} days instead...")
            data = connector.get_historical_data(symbol=symbol, timeframe=timeframe,
                                                  start_date=shrunk_start, end_date=end_date)
            if data is not None and not data.empty:
                print(f"  NOTE: {timeframe} only covers the last {days_back} days, not the "
                      f"full requested window - keep this in mind when comparing it "
                      f"against other timeframes in the results below.")
                break

    if data is None or data.empty:
        raise RuntimeError(
            f"No data returned for {symbol} {timeframe} at any window length tried. "
            f"Check that this exact symbol name appears in your MT5 Market Watch "
            f"(some brokers use 'XAUUSDm', 'GOLD#', etc. instead of 'XAUUSD')."
        )
    print(f"  {len(data)} candles ({data.index.min()} to {data.index.max()})")
    return data


def make_gold_strategy(ta: TechnicalAnalysis, htf_connector: OfflineHTFConnector, base_timeframe: str):
    """
    Wraps TechnicalAnalysis.advanced_signal_analysis() - the exact same
    pipeline used by MultiPairLiveBot.get_signal() in live trading - into the
    strategy_func(data_slice) -> dict interface BacktestEngine expects.
    """
    def strategy(data_slice: pd.DataFrame):
        if len(data_slice) < 60:
            return {'action': 'WAIT'}

        # Cap the window fed into indicators/structure analysis to keep this
        # tractable: BacktestEngine passes a GROWING slice (data.iloc[:i+1])
        # on every candle. Every indicator here (RSI-14, MACD-26, BB-20,
        # 20-candle structure lookback) only needs a few hundred candles of
        # context - without this cap the structure-level swing-detection
        # loop (pure Python) would make the whole backtest O(n^2), turning a
        # few minutes into hours on a real multi-month dataset.
        window = data_slice.tail(TRAILING_WINDOW)
        as_of = window.index[-1]

        try:
            enriched = ta.get_all_indicators(window)
            analysis = ta.advanced_signal_analysis(
                htf_connector, enriched, SYMBOL, base_timeframe, as_of=as_of
            )
        except Exception:
            return {'action': 'WAIT'}

        signal = analysis.get('signal')
        confidence = analysis.get('confidence', 0)
        # Match MultiPairLiveBot.run_analysis_cycle()'s exact gate - it only
        # ever considers a signal candidate when confidence > 50. Without
        # this, the backtest took every non-blocked BUY/SELL regardless of
        # confidence, trading far more often (and more recklessly) than the
        # live bot ever would.
        if analysis.get('trade_blocked', True) or signal not in ('BUY', 'SELL') or confidence <= 50:
            return {'action': 'WAIT'}

        # SEPARATE, STRICTER gate: live_trading_executor.py's
        # EliteTradingConfig.MIN_CONFIDENCE = 0.65 (65%) is a second,
        # harder confidence floor applied inside execute_live_trade() -
        # distinct from the >50 "candidate" filter above. A signal can
        # clear 50% and still get silently blocked here in live trading.
        # This was invisible even in the live logs (logged at a level
        # that doesn't show by default) until that was fixed separately -
        # replicating the actual gate here, not just the visible symptom.
        if confidence < 65:
            return {'action': 'WAIT'}

        # Match live_trading_executor.py's SEPARATE "TREND IS KING" gate
        # (SignalQualityEngine.check_trend_alignment) - this is a DIFFERENT,
        # additional check from whatever advanced_signal_analysis() does
        # internally, using the M15-scale fast/slow MAs, not the HTF trend.
        # This is the exact gate that correctly rejected your live SELL
        # signal twice ("SELL signal against uptrend").
        #
        # NOTE ON A BUG IN THE PREVIOUS VERSION OF THIS FILE: this used to
        # read ema_fast/ema_slow from analysis.get('market_data', {}) - but
        # advanced_signal_analysis() never sets that key; it's only ever
        # populated by MultiPairLiveBot.get_signal() in the live bot, which
        # this script doesn't call. So market_data was always {}, ema_fast/
        # ema_slow were always 0, the "if ema_fast and ema_slow" guard was
        # always false, and this entire check silently never ran - even
        # though the code was genuinely present. Pulling the values directly
        # from the enriched dataframe instead, the same place get_signal()
        # actually gets them from.
        latest = enriched.iloc[-1]
        ema_fast = float(latest['ma_fast']) if pd.notna(latest.get('ma_fast')) else 0.0
        ema_slow = float(latest['ma_slow']) if pd.notna(latest.get('ma_slow')) else 0.0
        if ema_fast and ema_slow:
            if signal == 'BUY' and ema_fast < ema_slow:
                return {'action': 'WAIT'}
            if signal == 'SELL' and ema_fast > ema_slow:
                return {'action': 'WAIT'}

        sl = analysis.get('structure_sl')
        tp = analysis.get('structure_tp')
        current_price = window['close'].iloc[-1]
        # Guard against degenerate structure levels (missing, or equal to
        # entry price - would divide by zero in BacktestEngine's position
        # sizing) rather than letting a bad level crash a long backtest run.
        if not sl or not tp or abs(current_price - sl) < 1e-6:
            return {'action': 'WAIT'}

        # Match live_trading_executor.py's R/R filter (EliteTradingConfig.
        # MIN_RR_RATIO = 2.0). This is the exact gate that blocked a real
        # M30 trade live (R/R 1.43 < 2.0) while this backtest, before this
        # fix, had no R/R floor at all and would have taken it anyway.
        risk = abs(current_price - sl)
        reward = abs(tp - current_price)
        if risk <= 0 or (reward / risk) < 2.0:
            return {'action': 'WAIT'}

        return {
            'action': signal,
            'pair': SYMBOL,
            'stop_loss': sl,
            'take_profit': tp,
        }

    return strategy


def print_monthly_breakdown(results, label=""):
    """
    Group closed trades by calendar month and print win rate / P&L per
    month. A single aggregate profit factor can hide a result that's really
    just "one good stretch carrying a flat-to-losing rest of the period" -
    this makes that visible instead of leaving it to eyeballing the equity
    curve shape.
    """
    trades = results.get('trades', [])
    if not trades:
        print(f"\n(No trades to break down{' for ' + label if label else ''})")
        return

    df = pd.DataFrame(trades)
    df['month'] = pd.to_datetime(df['entry_time']).dt.to_period('M')

    print(f"\n{'='*60}")
    print(f"MONTHLY BREAKDOWN{' - ' + label if label else ''}")
    print(f"{'='*60}")
    print(f"{'Month':<10}{'Trades':>8}{'Win Rate':>10}{'Net P&L':>12}")
    for month, g in df.groupby('month'):
        wins = (g['pnl'] > 0).sum()
        win_rate = 100 * wins / len(g)
        net_pnl = g['pnl'].sum()
        flag = "  <- carrying the result" if net_pnl > 0 and net_pnl > df['pnl'].sum() * 0.5 else ""
        print(f"{str(month):<10}{len(g):>8}{win_rate:>9.1f}%{net_pnl:>11.2f}{flag}")
    print(f"{'='*60}")


def run_single_backtest(connector, ta, symbol, timeframe, start_date, end_date,
                         balance, max_duration_minutes, htf_data_cache=None):
    """
    Run one backtest for one timeframe. Returns (engine, results, htf_data_cache).
    htf_data_cache is a dict {'H4': df, 'D1': df} - fetched once and reused
    across timeframes in --timeframe all, since the H4/D1 series don't
    depend on which base timeframe is being tested.
    """
    base_data = fetch_data(connector, symbol, timeframe, start_date, end_date,
                            f"base timeframe data ({timeframe})")

    if htf_data_cache is None:
        htf_data_cache = {}
    for htf_tf in ('H4', 'D1'):
        if htf_tf not in htf_data_cache:
            htf_data_cache[htf_tf] = fetch_data(
                connector, symbol, htf_tf, start_date - timedelta(days=HTF_WARMUP_DAYS), end_date,
                f"higher-timeframe data ({htf_tf}, for trend confirmation)"
            )

    htf_connector = OfflineHTFConnector(htf_data_cache)
    strategy = make_gold_strategy(ta, htf_connector, timeframe)

    print(f"\nRunning backtest over {len(base_data)} candles ({timeframe}) "
          f"(this uses the real analysis engine per candle, so it will take a while)...\n")

    engine = BacktestEngine(initial_balance=balance)
    max_duration = max_duration_minutes if max_duration_minutes and max_duration_minutes > 0 else None
    results = engine.run_backtest(base_data, strategy, max_duration_minutes=max_duration)
    return engine, results, htf_data_cache


def main():
    parser = argparse.ArgumentParser(description="Backtest the real Gold signal engine")
    parser.add_argument('--months', type=int, default=6, help="Lookback period in months (default 6)")
    parser.add_argument('--start', type=str, default=None, help="Start date YYYY-MM-DD (overrides --months)")
    parser.add_argument('--end', type=str, default=None, help="End date YYYY-MM-DD (default: now)")
    parser.add_argument('--timeframe', type=str, default='M15',
                         choices=['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1', 'all'],
                         help="Base timeframe to backtest (default M15). 'all' runs M1, M5, M15, "
                              "M30, H1, H4, and D1 as SEPARATE independent backtests and prints a "
                              "comparison - this tells you which timeframe(s) carry the edge, but "
                              "does NOT simulate them running simultaneously with shared equity/risk "
                              "the way the live bot now does. Heads up: M1 will be by far the slowest "
                              "of the seven (many more candles per month than any other timeframe).")
    parser.add_argument('--balance', type=float, default=10000, help="Starting balance (default 10000)")
    parser.add_argument('--max-duration-minutes', type=float, default=0,
                         help="Force-close trades still open after this long. Default 0 (disabled) now "
                              "matches the live bot, which no longer force-closes on a timer either - "
                              "backtesting showed the old 10-minute cap was actively harmful (cut trades "
                              "off before they could reach take_profit). Pass a number to re-test with a cap.")
    args = parser.parse_args()

    end_date = datetime.strptime(args.end, '%Y-%m-%d') if args.end else datetime.now()
    start_date = (datetime.strptime(args.start, '%Y-%m-%d') if args.start
                  else end_date - timedelta(days=30 * args.months))

    connector = MT5Connector()
    if not connector.initialize():
        print("Could not initialize MT5. Is the terminal running and logged in?")
        sys.exit(1)

    ta = TechnicalAnalysis()
    timeframes = ['M1', 'M5', 'M15', 'M30', 'H1', 'H4', 'D1'] if args.timeframe == 'all' else [args.timeframe]

    print(f"Backtesting {SYMBOL} {'/'.join(timeframes)} from {start_date.date()} to {end_date.date()}\n")

    htf_data_cache = None  # {'H4': df, 'D1': df} - shared across timeframes in --timeframe all
    comparison = []

    try:
        for tf in timeframes:
            engine, results, htf_data_cache = run_single_backtest(
                connector, ta, SYMBOL, tf, start_date, end_date,
                args.balance, args.max_duration_minutes, htf_data_cache=htf_data_cache
            )
            engine.print_summary(results)
            print_monthly_breakdown(results, label=tf)

            try:
                engine.plot_results(results, save_path=f'gold_backtest_results_{tf}.png')
                print(f"\nEquity curve saved to gold_backtest_results_{tf}.png")
            except Exception as e:
                print(f"\n(Could not save plot: {e})")

            comparison.append({
                'timeframe': tf,
                'trades': len(results['trades']),
                'return_pct': 100 * (results['final_balance'] - results['initial_balance']) / results['initial_balance'],
                'win_rate': results['metrics'].get('win_rate', 0) if 'metrics' in results else 0,
                'profit_factor': results['metrics'].get('profit_factor', 0) if 'metrics' in results else 0,
            })
    finally:
        connector.disconnect()

    if len(timeframes) > 1:
        print(f"\n{'='*60}")
        print("TIMEFRAME COMPARISON (independent single-timeframe backtests -")
        print("not a simulation of all three running simultaneously)")
        print(f"{'='*60}")
        print(f"{'Timeframe':<10}{'Trades':>8}{'Return':>10}{'Profit Factor':>15}")
        for c in comparison:
            print(f"{c['timeframe']:<10}{c['trades']:>8}{c['return_pct']:>9.2f}%{c['profit_factor']:>15.2f}")
        print(f"{'='*60}")


if __name__ == "__main__":
    main()