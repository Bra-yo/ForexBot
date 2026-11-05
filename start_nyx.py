"""
NYX AI - one-command launcher for the WHOLE system.

    python start_nyx.py

Starts:
Default: opens the NYX dashboard (landing page -> MT5 login). Logging in
starts the trading backend automatically; no NYX-START typing needed.
The backend keeps running if you close the browser tab; use Stop in the
console to stop it. Press Ctrl+C here to close the dashboard server.

Options:
    python start_nyx.py --direct          old behaviour: dashboard in the background
                                          and the backend in this console (type NYX-START)
    python start_nyx.py --no-browser      do not open the dashboard tab
    python start_nyx.py --port 8600       use a different dashboard port
"""

import argparse
import importlib.util
import os
import socket
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DASHBOARD = ROOT / "dashboard" / "nyx_app.py"
BACKEND = ROOT / "start_multi_pair_trading_fixed.py"


def port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def ensure_streamlit():
    if importlib.util.find_spec("streamlit") is None:
        print("[NYX] Streamlit not found - installing it (one time)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "streamlit"])


def start_dashboard(port: int, open_browser: bool):
    if not DASHBOARD.exists():
        print(f"[NYX] Dashboard file not found: {DASHBOARD}")
        return None
    if port_open(port):
        print(f"[NYX] Dashboard already running on port {port} - reusing it.")
        if open_browser:
            webbrowser.open(f"http://localhost:{port}")
        return None

    ensure_streamlit()
    cmd = [
        sys.executable, "-m", "streamlit", "run", str(DASHBOARD),
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
    ]
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = open(log_dir / "dashboard.log", "a", encoding="utf-8")
    proc = subprocess.Popen(cmd, cwd=str(ROOT), stdout=log_file, stderr=subprocess.STDOUT)

    for _ in range(40):
        if proc.poll() is not None:
            print("[NYX] Dashboard exited early - see logs/dashboard.log")
            return None
        if port_open(port):
            break
        time.sleep(0.5)

    url = f"http://localhost:{port}"
    print(f"[NYX] Dashboard running at {url}")
    if open_browser:
        webbrowser.open(url)
    return proc


def stop_dashboard(proc):
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("[NYX] Dashboard stopped.")


def main():
    parser = argparse.ArgumentParser(description="Start the NYX AI backend and dashboard together")
    parser.add_argument("--port", type=int, default=8505)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--direct", action="store_true",
                        help="run the backend in this console instead of starting it from the dashboard login")
    parser.add_argument("--dashboard", default=None,
                        help="path to a different Streamlit dashboard file (default: dashboard/nyx_app.py)")
    parser.add_argument("--auto-arm", action="store_true",
                        help="answer the NYX-START prompt automatically (DEMO accounts only)")
    args = parser.parse_args()

    os.chdir(ROOT)
    global DASHBOARD
    if args.dashboard:
        DASHBOARD = Path(args.dashboard).resolve()
    dash = start_dashboard(args.port, not args.no_browser)

    if not args.direct:
        if dash is None:
            return
        print("[NYX] Log in on the dashboard to start trading. Press Ctrl+C here to close the dashboard server.")
        try:
            dash.wait()
        except KeyboardInterrupt:
            pass
        finally:
            stop_dashboard(dash)
        return

    try:
        print("[NYX] Starting trading backend...\n")
        if args.auto_arm:
            backend = subprocess.Popen([sys.executable, str(BACKEND)], cwd=str(ROOT),
                                       stdin=subprocess.PIPE, text=True)
            backend.stdin.write("NYX-START\n")
            backend.stdin.flush()
            backend.stdin.close()
            backend.wait()
        else:
            subprocess.call([sys.executable, str(BACKEND)], cwd=str(ROOT))
    except KeyboardInterrupt:
        print("\n[NYX] Interrupted.")
    finally:
        stop_dashboard(dash)


if __name__ == "__main__":
    main()