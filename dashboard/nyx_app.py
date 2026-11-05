"""
NYX AI - Dashboard (landing -> login -> control console)

Flow:
  1. Landing page
  2. MT5 login (verified against the terminal)
  3. On successful login the trading backend is started automatically
     (no need to type NYX-START) and the live console opens.

The backend runs as its own detached process, so closing the browser tab
does not stop trading. Use the Stop button in the console to stop it.

Run with:  python start_nyx.py
"""

import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st

try:
    import MetaTrader5 as mt5
except ImportError:  # dashboard still renders without MT5
    mt5 = None

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
PID_FILE = LOG_DIR / "nyx_bot.pid"
BOT_LOG = LOG_DIR / "nyx_bot_live.log"
BACKEND = ROOT / "start_multi_pair_trading_fixed.py"

st.set_page_config(page_title="NYX AI", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
<style>
.block-container {padding-top: 2rem; max-width: 1200px;}
.nyx-hero {text-align:center; padding: 56px 0 24px 0;}
.nyx-hero h1 {font-size: 4rem; letter-spacing: 0.25rem; margin-bottom: 0;}
.nyx-hero p {font-size: 1.2rem; opacity: 0.75;}
.nyx-card {border: 1px solid rgba(128,128,128,0.35); border-radius: 14px; padding: 18px 20px; height: 100%;}
.nyx-card h4 {margin: 0 0 6px 0;}
.nyx-pill {display:inline-block; padding: 4px 14px; border-radius: 999px; font-weight: 600;}
.nyx-on {background: rgba(46,160,67,0.2); color: #3fb950;}
.nyx-off {background: rgba(248,81,73,0.2); color: #f85149;}
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------- process control

def read_pid():
    try:
        return int(PID_FILE.read_text().strip())
    except Exception:
        return None


def pid_alive(pid):
    if not pid:
        return False
    try:
        if os.name == "nt":
            out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"],
                                 capture_output=True, text=True).stdout
            return str(pid) in out
        os.kill(pid, 0)
        return True
    except Exception:
        return False


def bot_running():
    return pid_alive(read_pid())


def start_bot():
    if bot_running():
        return True, "Backend already running."
    env = os.environ.copy()
    env["NYX_AUTO_ARM"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    log = open(BOT_LOG, "a", encoding="utf-8")
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
    try:
        proc = subprocess.Popen([sys.executable, str(BACKEND)], cwd=str(ROOT), env=env,
                                stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, **kwargs)
        PID_FILE.write_text(str(proc.pid))
        return True, f"Backend started (pid {proc.pid})."
    except Exception as e:
        return False, f"Could not start backend: {e}"


def stop_bot():
    pid = read_pid()
    if not pid_alive(pid):
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        else:
            os.kill(pid, 15)
    except Exception:
        pass
    try:
        PID_FILE.unlink()
    except Exception:
        pass


# ---------------------------------------------------------------- MT5 helpers

def mt5_login(login, password, server):
    """Verify credentials against the terminal. Returns (ok, info_or_error)."""
    if mt5 is None:
        return False, "MetaTrader5 package is not installed."
    try:
        kwargs = {}
        if login:
            kwargs = {"login": int(login), "password": password, "server": server}
        if not mt5.initialize(**kwargs):
            return False, f"MT5 initialize failed: {mt5.last_error()}"
        info = mt5.account_info()
        if info is None:
            return False, "Connected to terminal but no account is logged in."
        return True, info
    except Exception as e:
        return False, str(e)
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


def snapshot():
    """Account + positions + recent deals straight from MT5."""
    if mt5 is None or not mt5.initialize():
        return None
    try:
        acc = mt5.account_info()
        pos = mt5.positions_get() or []
        deals = mt5.history_deals_get(datetime.now() - timedelta(days=7), datetime.now() + timedelta(days=1)) or []
        return acc, list(pos), list(deals)
    finally:
        mt5.shutdown()


# ---------------------------------------------------------------- pages

if "page" not in st.session_state:
    # If a backend is already running from an earlier session, go straight to the console.
    st.session_state.page = "console" if bot_running() else "landing"


def goto(page):
    st.session_state.page = page
    st.rerun()


def page_landing():
    st.markdown(
        """
<div class="nyx-hero">
  <h1>NYX AI</h1>
  <p>Automated gold (XAUUSD) trading with live risk control</p>
</div>
""",
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="nyx-card"><h4>Signal engine</h4>Multi-factor analysis with trend, volume profile and VWAP context on M15 and M5.</div>', unsafe_allow_html=True)
    c2.markdown('<div class="nyx-card"><h4>Risk first</h4>Broker-side stop loss and take profit, drawdown, spread and volatility filters.</div>', unsafe_allow_html=True)
    c3.markdown('<div class="nyx-card"><h4>Always visible</h4>Open positions, equity and the live bot log in one console.</div>', unsafe_allow_html=True)
    st.write("")
    _, mid, _ = st.columns([1, 1, 1])
    if mid.button("Enter", type="primary", use_container_width=True):
        goto("login")


def page_login():
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.markdown("## Connect to MetaTrader 5")
        st.caption("Logging in verifies the account and starts the trading backend automatically.")
        with st.form("login"):
            login = st.text_input("MT5 login (account number)", placeholder="leave empty to use the account already open in MT5")
            password = st.text_input("MT5 password", type="password")
            server = st.text_input("Server", value="MetaQuotes-Demo")
            live_ok = st.checkbox("If this is a REAL-money account, I understand the bot will trade it with real funds")
            submitted = st.form_submit_button("Log in and start NYX", type="primary", use_container_width=True)

        if submitted:
            if login and not password:
                st.error("Enter the password, or clear the login field to use the open terminal account.")
                return
            with st.spinner("Verifying account..."):
                ok, info = mt5_login(login, password, server)
            if not ok:
                st.error(info)
                return
            is_demo = info.trade_mode == 0
            if not is_demo and not live_ok:
                st.error(f"Account {info.login} is a REAL-money account. Tick the confirmation box to continue.")
                return
            st.session_state.account = {"login": info.login, "server": info.server, "demo": is_demo}
            good, msg = start_bot()
            if not good:
                st.error(msg)
                return
            st.success(msg)
            time.sleep(1.2)
            goto("console")
        if st.button("Back"):
            goto("landing")


def tail(path, n=60):
    try:
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return "No log yet."


@st.fragment(run_every=5)
def live_panel():
    running = bot_running()
    pill = '<span class="nyx-pill nyx-on">BOT RUNNING</span>' if running else '<span class="nyx-pill nyx-off">BOT STOPPED</span>'
    st.markdown(pill, unsafe_allow_html=True)

    snap = snapshot()
    if snap is None:
        st.warning("Cannot reach MT5 right now.")
    else:
        acc, pos, deals = snap
        floating = sum(p.profit for p in pos)
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Balance", f"${acc.balance:,.2f}")
        m2.metric("Equity", f"${acc.equity:,.2f}", f"{acc.equity - acc.balance:+,.2f}")
        m3.metric("Open positions", len(pos))
        m4.metric("Floating P/L", f"${floating:,.2f}")

        st.subheader("Open positions")
        if pos:
            st.dataframe(pd.DataFrame([{
                "Ticket": p.ticket, "Symbol": p.symbol,
                "Type": "BUY" if p.type == 0 else "SELL", "Lots": p.volume,
                "Open": p.price_open, "SL": p.sl, "TP": p.tp,
                "Price": p.price_current, "Profit": p.profit,
            } for p in pos]), use_container_width=True, hide_index=True)
        else:
            st.info("No open positions.")

        closed = [d for d in deals if d.entry == 1 and d.profit != 0]
        st.subheader("Last 7 days (closed)")
        if closed:
            wins = sum(1 for d in closed if d.profit > 0)
            total = sum(d.profit for d in closed)
            a, b, c = st.columns(3)
            a.metric("Closed trades", len(closed))
            b.metric("Win rate", f"{wins / len(closed) * 100:.0f}%")
            c.metric("Net P/L", f"${total:,.2f}")
        else:
            st.caption("No closed trades in the last 7 days.")

    st.subheader("Live bot log")
    st.code(tail(BOT_LOG), language="text")


def page_console():
    top_l, top_r = st.columns([4, 1])
    with top_l:
        st.markdown("## NYX AI Console")
        acc = st.session_state.get("account")
        if acc:
            st.caption(f"Account {acc['login']} on {acc['server']} ({'DEMO' if acc['demo'] else 'REAL'})")
    with top_r:
        if bot_running():
            if st.button("Stop bot", type="secondary", use_container_width=True):
                stop_bot()
                st.rerun()
        else:
            if st.button("Start bot", type="primary", use_container_width=True):
                ok, msg = start_bot()
                (st.success if ok else st.error)(msg)
                time.sleep(1)
                st.rerun()
        if st.button("Log out", use_container_width=True):
            goto("login")
    live_panel()


page = st.session_state.page
if page == "landing":
    page_landing()
elif page == "login":
    page_login()
else:
    page_console()