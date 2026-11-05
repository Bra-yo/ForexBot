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
    python run_gold_backtest.py --timeframe M5 --months 3 --variants   # old vs live rules, one pass
    python run_gold_backtest.py --live-stops --min-confidence 45        # a single run with live rules

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
from confidence_config import MIN_CONFIDENCE_PCT
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


MIN_RR_RATIO = 2.0       # matches EliteTradingConfig.MIN_RR_RATIO in live trading
ATR_PERIOD = 14
_ANALYSIS_CACHE = {}     # (timeframe, as_of) -> analysis record; shared by every variant so
                         # the slow per-candle analysis only ever runs once per candle


def _atr(window, period=ATR_PERIOD):
    """Simple ATR of the trailing window (same idea as the live executor's get_atr)."""
    high, low, close = window['high'], window['low'], window['close']
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    val = tr.tail(period).mean()
    return float(val) if pd.notna(val) else 0.0


def make_gold_strategy(ta: TechnicalAnalysis, htf_connector: OfflineHTFConnector, base_timeframe: str,
                       min_conf: float = MIN_CONFIDENCE_PCT, live_stops: bool = False,
                       spread: float = 0.40):
    """
    Wraps TechnicalAnalysis.advanced_signal_analysis() - the exact same
    pipeline used by MultiPairLiveBot.get_signal() in live trading - into the
    strategy_func(data_slice) -> dict interface BacktestEngine expects.

    min_conf    single confidence floor (percent). Defaults to the shared live
                value in confidence_config.py. The old version of this file
                hard-coded 50 and 65, so the 45-65 band that the live bot
                trades was never actually backtested.
    live_stops  apply the live executor's stop/target rules: stop widened to at
                least 1x ATR + spread, and take-profit pushed out to at least
                2x the stop distance.
    spread      USD spread used by the stop floor (gold: ~0.35-0.45 on demo).
    """
    def analyze(window):
        # The expensive part. Cached per candle so that several variants
        # (different confidence floors / stop rules) can share one pass.
        as_of = window.index[-1]
        key = (base_timeframe, as_of)
        if key in _ANALYSIS_CACHE:
            return _ANALYSIS_CACHE[key]
        rec = None
        try:
            enriched = ta.get_all_indicators(window)
            analysis = ta.advanced_signal_analysis(
                htf_connector, enriched, SYMBOL, base_timeframe, as_of=as_of
            )
            latest = enriched.iloc[-1]
            rec = {
                'signal': analysis.get('signal'),
                'confidence': analysis.get('confidence', 0),
                'blocked': analysis.get('trade_blocked', True),
                'sl': analysis.get('structure_sl'),
                'tp': analysis.get('structure_tp'),
                'ma_fast': float(latest['ma_fast']) if pd.notna(latest.get('ma_fast')) else 0.0,
                'ma_slow': float(latest['ma_slow']) if pd.notna(latest.get('ma_slow')) else 0.0,
                'price': float(window['close'].iloc[-1]),
                'atr': _atr(window),
            }
        except Exception:
            rec = None
        _ANALYSIS_CACHE[key] = rec
        return rec

    def strategy(data_slice: pd.DataFrame):
        if len(data_slice) < 60:
            return {'action': 'WAIT'}

        # Cap the window fed into indicators/structure analysis to keep this
        # tractable (BacktestEngine passes a GROWING slice on every candle).
        window = data_slice.tail(TRAILING_WINDOW)
        rec = analyze(window)
        if rec is None:
            return {'action': 'WAIT'}

        signal = rec['signal']
        confidence = rec['confidence']

        # One confidence floor, the same constant the live bot uses.
        if rec['blocked'] or signal not in ('BUY', 'SELL') or confidence < min_conf:
            return {'action': 'WAIT'}

        # "TREND IS KING" gate (SignalQualityEngine.check_trend_alignment):
        # fast/slow MA direction must agree with the signal.
        ema_fast, ema_slow = rec['ma_fast'], rec['ma_slow']
        if ema_fast and ema_slow:
            if signal == 'BUY' and ema_fast < ema_slow:
                return {'action': 'WAIT'}
            if signal == 'SELL' and ema_fast > ema_slow:
                return {'action': 'WAIT'}

        sl = rec['sl']
        tp = rec['tp']
        current_price = rec['price']
        # Guard against degenerate structure levels (missing, or equal to entry).
        if not sl or not tp or abs(current_price - sl) < 1e-6:
            return {'action': 'WAIT'}

        # Signal-time R/R filter (EliteTradingConfig.MIN_RR_RATIO = 2.0).
        risk = abs(current_price - sl)
        reward = abs(tp - current_price)
        if risk <= 0 or (reward / risk) < MIN_RR_RATIO:
            return {'action': 'WAIT'}

        # Live executor adjustments, applied AFTER the signal-time check
        # exactly as in live_trading_executor.execute_live_trade().
        if live_stops and rec['atr'] > 0:
            floor_dist = rec['atr'] + spread
            sl_dist = abs(current_price - sl)
            if sl_dist < floor_dist:
                sl_dist = floor_dist
                sl = current_price - sl_dist if signal == 'BUY' else current_price + sl_dist
            min_tp_dist = sl_dist * MIN_RR_RATIO
            if abs(tp - current_price) < min_tp_dist:
                tp = current_price + min_tp_dist if signal == 'BUY' else current_price - min_tp_dist

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
                         balance, max_duration_minutes, htf_data_cache=None,
                         min_conf=MIN_CONFIDENCE_PCT, live_stops=False, spread=0.40,
                         base_data=None, quiet=False):
    """
    Run one backtest for one timeframe. Returns (engine, results, htf_data_cache).
    htf_data_cache is a dict {'H4': df, 'D1': df} - fetched once and reused
    across timeframes in --timeframe all, since the H4/D1 series don't
    depend on which base timeframe is being tested.
    """
    if base_data is None:
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
    strategy = make_gold_strategy(ta, htf_connector, timeframe, min_conf=min_conf,
                                  live_stops=live_stops, spread=spread)

    if not quiet:
        print(f"\nRunning backtest over {len(base_data)} candles ({timeframe}) "
              f"(this uses the real analysis engine per candle, so it will take a while)...\n")

    engine = BacktestEngine(initial_balance=balance)
    max_duration = max_duration_minutes if max_duration_minutes and max_duration_minutes > 0 else None
    results = engine.run_backtest(base_data, strategy, max_duration_minutes=max_duration)
    return engine, results, htf_data_cache, base_data


VARIANTS = [
    # (label, confidence floor, live stop rules?)
    ("OLD gates: conf>=65, structure stops", 65.0, False),
    ("LIVE gate: conf>=%.0f, structure stops" % MIN_CONFIDENCE_PCT, MIN_CONFIDENCE_PCT, False),
    ("LIVE gate: conf>=%.0f, LIVE stops" % MIN_CONFIDENCE_PCT, MIN_CONFIDENCE_PCT, True),
    ("conf>=55, LIVE stops", 55.0, True),
    ("conf>=65, LIVE stops", 65.0, True),
]


def run_variants(connector, ta, tf, start_date, end_date, args):
    rows = []
    htf_cache = None
    base_data = None
    for idx, (label, conf, live) in enumerate(VARIANTS):
        print(f"\n--- Variant {idx + 1}/{len(VARIANTS)}: {label} ---")
        engine, results, htf_cache, base_data = run_single_backtest(
            connector, ta, SYMBOL, tf, start_date, end_date, args.balance,
            args.max_duration_minutes, htf_data_cache=htf_cache, min_conf=conf,
            live_stops=live, spread=args.spread, base_data=base_data, quiet=(idx > 0)
        )
        trades = results.get('trades', [])
        pnls = pd.Series([t['pnl'] for t in trades], dtype=float)
        m = results.get('metrics', {})
        if len(pnls) > 1 and pnls.std() > 0:
            t_stat = pnls.mean() / (pnls.std() / (len(pnls) ** 0.5))
        else:
            t_stat = 0.0
        rows.append({
            'label': label,
            'trades': len(trades),
            'win_rate': m.get('win_rate', 0),
            'return_pct': 100 * (results['final_balance'] - results['initial_balance']) / results['initial_balance'],
            'pf': m.get('profit_factor', 0),
            'dd': m.get('max_drawdown_pct', 0),
            't': t_stat,
        })
        if idx == 2:
            print_monthly_breakdown(results, label=label)

    print(f"\n{'=' * 100}")
    print(f"VARIANT COMPARISON - {SYMBOL} {tf}, {start_date.date()} to {end_date.date()}")
    print(f"{'=' * 100}")
    print(f"{'Variant':<42}{'Trades':>7}{'Win%':>7}{'Return%':>9}{'PF':>7}{'MaxDD%':>8}{'t-stat':>8}")
    for r in rows:
        print(f"{r['label']:<42}{r['trades']:>7}{r['win_rate']:>7.1f}{r['return_pct']:>9.2f}"
              f"{r['pf']:>7.2f}{r['dd']:>8.2f}{r['t']:>8.2f}")
    print(f"{'=' * 100}")
    print("t-stat = mean trade P&L / its standard error. Below about 2.0 you cannot rule out luck;")
    print("with only a few dozen trades it will usually be below 2 even for a real edge.")


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
    parser.add_argument('--min-confidence', type=float, default=MIN_CONFIDENCE_PCT,
                         help="Confidence floor in percent (default: the shared live value in "
                              "confidence_config.py, currently %.0f)." % MIN_CONFIDENCE_PCT)
    parser.add_argument('--live-stops', action='store_true',
                         help="Apply the live executor's stop/target rules: stop widened to at least "
                              "1x ATR + spread, take-profit pushed out to at least 2x the stop distance.")
    parser.add_argument('--spread', type=float, default=0.40,
                         help="Spread in USD used by the stop floor with --live-stops (default 0.40).")
    parser.add_argument('--variants', action='store_true',
                         help="Run the old gates, the live gate and the live stop rules side by side on "
                              "ONE timeframe and print a comparison. The slow per-candle analysis runs "
                              "once and is reused, so only the first variant is slow.")
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

    if args.variants:
        if len(timeframes) != 1:
            print("--variants works on one timeframe at a time (not --timeframe all).")
            connector.disconnect()
            sys.exit(1)
        try:
            run_variants(connector, ta, timeframes[0], start_date, end_date, args)
        finally:
            connector.disconnect()
        return

    try:
        for tf in timeframes:
            engine, results, htf_data_cache, _ = run_single_backtest(
                connector, ta, SYMBOL, tf, start_date, end_date,
                args.balance, args.max_duration_minutes, htf_data_cache=htf_data_cache,
                min_conf=args.min_confidence, live_stops=args.live_stops, spread=args.spread
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