"""
quantum_style_tick_test.py

Tick-level test of the strategy family seen in the "Quantum EA" video:
  * a BUY STOP above and a SELL STOP below the current price (a straddle),
    re-placed every few seconds so they follow price
  * very small take-profit (cents to ~1 dollar), positions live seconds
  * several positions stacked per side during a run
  * optional basket exit: close everything when the net floating profit
    reaches a target, or when it falls to a hard basket stop

The point of this file is NOT to promise profit. It answers three questions
with your own broker's ticks before any real or demo order is sent:

  1. Does the logic make money on REAL ticks after the REAL spread?
  2. How fast does the result die as spread / latency get worse?
     (Your MetaQuotes demo spread is 0.30-0.59 USD; the video account
      showed 0.07 USD.)
  3. Is the profit real structure, or just what any random price path
     would give?  (--baseline shuffles the tick moves and re-runs.)

Usage (from the project folder, MT5 terminal open and logged in):

  # 1) collect your own ticks for a while (leave it running 1-2 hours)
  python backtesting/quantum_style_tick_test.py --record 7200 --csv ticks.csv

  # 2) test on them, with sweeps and the shuffled baseline
  python backtesting/quantum_style_tick_test.py --source csv --csv ticks.csv --sweep --baseline

  # or pull whatever tick history the terminal already has
  python backtesting/quantum_style_tick_test.py --source mt5 --hours 24 --sweep --baseline

  # wiring check only (random prices, proves nothing about profit)
  python backtesting/quantum_style_tick_test.py --source synthetic --sweep
"""

import argparse
import math
import sys
import time
from dataclasses import dataclass, replace

import numpy as np

CONTRACT = 100.0  # ounces per 1.00 lot of XAUUSD


@dataclass
class Params:
    lot: float = 0.01
    offset: float = 0.40        # distance of each stop order from price (USD)
    tp: float = 0.80            # take-profit distance (USD)
    reanchor_s: float = 5.0     # cancel/replace pending orders this often
    max_per_side: int = 3       # max stacked positions per direction
    latency_ms: float = 50.0    # delay from trigger to fill
    basket_target: float = 0.0  # close all at this net floating profit (USD); 0 = off
    basket_stop: float = 0.0    # close all at this net floating loss (USD); 0 = off
    max_hold_s: float = 60.0    # close a position at market after this long
    max_spread: float = 0.0     # no new orders above this spread (USD); 0 = off
    spread_mult: float = 1.0    # scale the recorded spread (what-if a worse broker)
    daily_loss: float = 0.0     # halt for the day at this loss (USD); 0 = off


# ----------------------------------------------------------------------------
# Data sources
# ----------------------------------------------------------------------------
def load_mt5(symbol, hours):
    import MetaTrader5 as mt5
    from datetime import datetime, timedelta, timezone
    if not mt5.initialize():
        raise SystemExit("MT5 initialize failed: %s" % (mt5.last_error(),))
    mt5.symbol_select(symbol, True)
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=hours)
    ticks = mt5.copy_ticks_range(symbol, start, end, mt5.COPY_TICKS_ALL)
    mt5.shutdown()
    if ticks is None or len(ticks) < 1000:
        raise SystemExit(
            "Not enough tick history from the terminal (%s ticks). Use --record "
            "to collect ticks first, then --source csv." % (0 if ticks is None else len(ticks)))
    t = ticks["time_msc"].astype(np.float64) / 1000.0
    bid = ticks["bid"].astype(np.float64)
    ask = ticks["ask"].astype(np.float64)
    return clean(t, bid, ask)


def load_csv(path):
    data = np.genfromtxt(path, delimiter=",", names=True, dtype=np.float64)
    t = data["time_msc"] / 1000.0
    return clean(t, data["bid"], data["ask"])


def clean(t, bid, ask):
    ok = (bid > 0) & (ask > 0) & (ask >= bid)
    t, bid, ask = t[ok], bid[ok], ask[ok]
    order = np.argsort(t, kind="stable")
    return t[order], bid[order], ask[order]


def synth(hours=4.0, seed=1, ticks_per_sec=3.0, atr_m5=3.0, spread=0.20):
    """Zero-edge random walk. Only proves the harness runs."""
    rng = np.random.default_rng(seed)
    n = int(hours * 3600 * ticks_per_sec)
    t = np.cumsum(rng.exponential(1.0 / ticks_per_sec, n))
    sigma = atr_m5 / (1.6 * math.sqrt(300.0 * ticks_per_sec))
    mid = np.round(4000.0 + np.cumsum(rng.normal(0.0, sigma, n)), 2)
    return t, mid - spread / 2.0, mid + spread / 2.0


def record_ticks(symbol, seconds, path):
    import MetaTrader5 as mt5
    if not mt5.initialize():
        raise SystemExit("MT5 initialize failed: %s" % (mt5.last_error(),))
    mt5.symbol_select(symbol, True)
    last = 0
    rows = 0
    end = time.time() + seconds
    print("Recording %s ticks to %s for %d seconds. Ctrl+C to stop early." % (symbol, path, seconds))
    with open(path, "w") as f:
        f.write("time_msc,bid,ask\n")
        try:
            while time.time() < end:
                tk = mt5.symbol_info_tick(symbol)
                if tk is not None and tk.time_msc != last and tk.bid > 0 and tk.ask >= tk.bid:
                    last = tk.time_msc
                    f.write("%d,%.5f,%.5f\n" % (tk.time_msc, tk.bid, tk.ask))
                    rows += 1
                    if rows % 5000 == 0:
                        f.flush()
                time.sleep(0.002)
        except KeyboardInterrupt:
            pass
    mt5.shutdown()
    print("Saved %d ticks." % rows)


# ----------------------------------------------------------------------------
# Simulator
# ----------------------------------------------------------------------------
def simulate(t, bid0, ask0, p):
    mid = (bid0 + ask0) / 2.0
    spr = (ask0 - bid0) * p.spread_mult
    bid = mid - spr / 2.0
    ask = mid + spr / 2.0

    n = len(t)
    oz = p.lot * CONTRACT
    lat = p.latency_ms / 1000.0

    pos = []                 # [dir, entry, t_open]
    queue = []               # [fill_time, dir]
    lvl = {1: None, -1: None}
    anchor = {1: -1e18, -1: -1e18}

    realized = 0.0
    peak = 0.0
    max_dd = 0.0
    closed = []              # (pnl, hold_s)
    cycles = []
    cycle_start = None
    cur_day = int(t[0] // 86400)
    day_start = 0.0
    halted = False

    def close_all(ti, b, a):
        nonlocal realized
        for d, ent, to in pos:
            pnl = ((b - ent) if d > 0 else (ent - a)) * oz
            realized += pnl
            closed.append((pnl, ti - to))
        pos.clear()

    for i in range(n):
        ti, b, a = t[i], bid[i], ask[i]

        day = int(ti // 86400)
        if day != cur_day:
            cur_day = day
            day_start = realized
            halted = False

        # 1) fills that have waited out the latency
        if queue and queue[0][0] <= ti:
            rest = []
            for ft, d in queue:
                if ft <= ti:
                    if (not halted) and sum(1 for x in pos if x[0] == d) < p.max_per_side:
                        pos.append([d, a if d > 0 else b, ti])
                else:
                    rest.append([ft, d])
            queue = rest

        # 2) take-profit and max-hold exits
        if pos:
            keep = []
            for e in pos:
                d, ent, to = e
                if d > 0 and b >= ent + p.tp:
                    pnl = p.tp * oz
                elif d < 0 and a <= ent - p.tp:
                    pnl = p.tp * oz
                elif ti - to >= p.max_hold_s:
                    pnl = ((b - ent) if d > 0 else (ent - a)) * oz
                else:
                    keep.append(e)
                    continue
                realized += pnl
                closed.append((pnl, ti - to))
            pos[:] = keep

        # 3) basket logic and daily loss on the remaining positions
        floating = 0.0
        if pos:
            for d, ent, to in pos:
                floating += ((b - ent) if d > 0 else (ent - a)) * oz
            if p.basket_target > 0 and floating >= p.basket_target:
                close_all(ti, b, a)
                floating = 0.0
            elif p.basket_stop > 0 and floating <= -p.basket_stop:
                close_all(ti, b, a)
                floating = 0.0
        if p.daily_loss > 0 and not halted and (realized - day_start + floating) <= -p.daily_loss:
            close_all(ti, b, a)
            floating = 0.0
            halted = True
            lvl[1] = lvl[-1] = None
            queue = []

        # cycle bookkeeping (flat -> positions -> flat)
        if pos and cycle_start is None:
            cycle_start = realized
        elif not pos and cycle_start is not None:
            cycles.append(realized - cycle_start)
            cycle_start = None

        eq = realized + floating
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd

        # 4) pending stop orders: trigger, then place / re-anchor
        spread_now = a - b
        spread_ok = (p.max_spread <= 0) or (spread_now <= p.max_spread)
        for d in (1, -1):
            if lvl[d] is not None:
                if (d > 0 and a >= lvl[d]) or (d < 0 and b <= lvl[d]):
                    queue.append([ti + lat, d])
                    lvl[d] = None
                elif ti - anchor[d] >= p.reanchor_s:
                    lvl[d] = None
            if lvl[d] is None and not halted and spread_ok:
                if sum(1 for x in pos if x[0] == d) + sum(1 for q in queue if q[1] == d) < p.max_per_side:
                    lvl[d] = (a + p.offset) if d > 0 else (b - p.offset)
                    anchor[d] = ti

    close_all(t[-1], bid[-1], ask[-1])
    if cycle_start is not None:
        cycles.append(realized - cycle_start)

    pnls = np.array([c[0] for c in closed]) if closed else np.array([0.0])
    holds = np.array([c[1] for c in closed]) if closed else np.array([0.0])
    wins = pnls[pnls > 0]
    losses = pnls[pnls <= 0]
    hours = max((t[-1] - t[0]) / 3600.0, 1e-9)
    cyc = np.array(cycles) if cycles else np.array([0.0])
    return {
        "positions": len(closed),
        "per_hour": len(closed) / hours,
        "win_rate": 100.0 * len(wins) / max(len(closed), 1),
        "net": float(realized),
        "avg_win": float(wins.mean()) if len(wins) else 0.0,
        "avg_loss": float(losses.mean()) if len(losses) else 0.0,
        "worst_loss": float(pnls.min()),
        "profit_factor": float(wins.sum() / abs(losses.sum())) if len(losses) and losses.sum() != 0 else float("inf"),
        "max_dd": float(max_dd),
        "avg_hold_s": float(holds.mean()),
        "avg_spread": float(np.mean(spr)),
        "cycles": len(cycles),
        "cycle_win_rate": 100.0 * float((cyc > 0).sum()) / max(len(cyc), 1),
        "worst_cycle": float(cyc.min()),
        "hours": hours,
    }


# ----------------------------------------------------------------------------
# Reporting
# ----------------------------------------------------------------------------
def shuffled(t, bid, ask, seed):
    """Same volatility, same spreads, no real structure."""
    rng = np.random.default_rng(seed)
    mid = (bid + ask) / 2.0
    steps = rng.permutation(np.diff(mid))
    new_mid = np.concatenate([[mid[0]], mid[0] + np.cumsum(steps)])
    spr = ask - bid
    return t, new_mid - spr / 2.0, new_mid + spr / 2.0


def line(label, r):
    return ("%-26s pos=%6d  win%%=%5.1f  net=%9.2f  avgW=%6.2f avgL=%7.2f  worstL=%7.2f  PF=%5.2f  maxDD=%8.2f  cyc=%5d worstCyc=%8.2f" % (
        label, r["positions"], r["win_rate"], r["net"], r["avg_win"], r["avg_loss"],
        r["worst_loss"], min(r["profit_factor"], 99.0), r["max_dd"], r["cycles"], r["worst_cycle"]))


def main():
    ap = argparse.ArgumentParser(description="Quantum-style tick scalper test")
    ap.add_argument("--source", choices=["synthetic", "mt5", "csv"], default="synthetic")
    ap.add_argument("--csv", default="ticks.csv")
    ap.add_argument("--symbol", default="XAUUSD")
    ap.add_argument("--hours", type=float, default=24.0)
    ap.add_argument("--record", type=int, default=0, help="record live ticks for N seconds and exit")
    ap.add_argument("--lot", type=float, default=0.01)
    ap.add_argument("--offset", type=float, default=0.40)
    ap.add_argument("--tp", type=float, default=0.80)
    ap.add_argument("--reanchor", type=float, default=5.0)
    ap.add_argument("--max-per-side", type=int, default=3)
    ap.add_argument("--latency-ms", type=float, default=50.0)
    ap.add_argument("--basket-target", type=float, default=0.0)
    ap.add_argument("--basket-stop", type=float, default=0.0)
    ap.add_argument("--max-hold", type=float, default=60.0)
    ap.add_argument("--max-spread", type=float, default=0.0)
    ap.add_argument("--daily-loss", type=float, default=0.0)
    ap.add_argument("--sweep", action="store_true", help="spread and latency sensitivity tables")
    ap.add_argument("--baseline", action="store_true", help="compare against shuffled (no-structure) ticks")
    a = ap.parse_args()

    if a.record:
        record_ticks(a.symbol, a.record, a.csv)
        return

    if a.source == "mt5":
        t, bid, ask = load_mt5(a.symbol, a.hours)
    elif a.source == "csv":
        t, bid, ask = load_csv(a.csv)
    else:
        t, bid, ask = synth(hours=min(a.hours, 6.0))
        print("SYNTHETIC random-walk data: this only checks the code runs.")

    p = Params(lot=a.lot, offset=a.offset, tp=a.tp, reanchor_s=a.reanchor,
               max_per_side=a.max_per_side, latency_ms=a.latency_ms,
               basket_target=a.basket_target, basket_stop=a.basket_stop,
               max_hold_s=a.max_hold, max_spread=a.max_spread, daily_loss=a.daily_loss)

    spr = ask - bid
    print("Ticks: %d over %.2f hours | spread median %.2f  mean %.2f  p95 %.2f USD" % (
        len(t), (t[-1] - t[0]) / 3600.0, np.median(spr), spr.mean(), np.percentile(spr, 95)))
    print("Params: lot=%.2f offset=%.2f tp=%.2f latency=%.0fms max/side=%d basket_target=%.2f basket_stop=%.2f" % (
        p.lot, p.offset, p.tp, p.latency_ms, p.max_per_side, p.basket_target, p.basket_stop))
    print("")

    base = simulate(t, bid, ask, p)
    print(line("REAL ticks, your spread", base))

    if a.baseline:
        res = [simulate(*shuffled(t, bid, ask, s), p) for s in range(5)]
        avg = {k: float(np.mean([r[k] for r in res])) for k in res[0]}
        print(line("SHUFFLED baseline (avg 5)", avg))
        print("  -> If REAL is not clearly better than SHUFFLED, the 'edge' is only the settings, not the market.")

    if a.sweep:
        print("\nSpread sensitivity (multiplies the recorded spread):")
        for m in (0.25, 0.5, 1.0, 2.0, 4.0, 8.0):
            r = simulate(t, bid, ask, replace(p, spread_mult=m))
            print(line("  spread x%.2f (avg %.2f)" % (m, r["avg_spread"]), r))
        print("\nLatency sensitivity:")
        for ms in (0, 25, 50, 100, 200, 400):
            r = simulate(t, bid, ask, replace(p, latency_ms=ms))
            print(line("  latency %dms" % ms, r))

    print("\nHow to read this: a high win% means little by itself. Compare avgW vs avgL, worstL and worstCyc.")
    print("Win% x avgW must beat (100-win%) x |avgL| after the spread, and maxDD must fit your account.")


if __name__ == "__main__":
    sys.exit(main())