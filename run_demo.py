import argparse
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from config.loader import load_config

ROOT = Path(__file__).resolve().parent
LOGS = ROOT / "logs"
PY = sys.executable

def port_in_use(port):
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0

READY_TIMEOUT = 20   

def wait_for_port(port, proc, timeout=None):
    deadline = time.time() + (READY_TIMEOUT if timeout is None else timeout)
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        if port_in_use(port):
            return True
        time.sleep(0.3)
    return False

def broker_command():
    exe = shutil.which("amqtt", path=str(Path(PY).parent)) or shutil.which("amqtt")
    if not exe:
        sys.exit("amqtt not found. Install it with: pip install amqtt")
    return [exe, "-c", "config/amqtt.yaml"]

def build_steps(cfg, dashboard=False):
    steps = [("broker", broker_command(), 0, cfg["broker"]["port"])]
    for number, plant in enumerate(cfg["plants"], start=1):
        steps.append((f"plant_{number}", [PY, "-m", f"simulators.plant_{number}"], 0, plant["opcua_port"]))
    steps.append(("gateway", [PY, "-m", "gateway.main"], 3))
    steps.append(("center", [PY, "-m", "central.mqtt_subscriber"], 1))
    if dashboard:
        steps.append(("dashboard", [PY, "-m", "streamlit", "run", "dashboard/app.py",
                                    "--server.headless", "true"], 0, 8501))
    return steps

def start_all(steps, env, cwd, logdir):
    logdir.mkdir(exist_ok=True)
    procs = []
    for name, command, wait, *rest in steps:
        log = open(logdir / f"{name}.log", "w")
        proc = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT,
                                start_new_session=True)
        procs.append((name, proc))
        print(f"started {name}")
        time.sleep(wait)
        if rest and not wait_for_port(rest[0], proc):    
            return procs, name
        if proc.poll() is not None:
            return procs, name
    return procs, None


def stop_all(procs):
    for name, proc in reversed(procs):
        if proc.poll() is None:
            proc.terminate()
    for name, proc in reversed(procs):
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    print("everything stopped")

def counts(db_path):
    try:
        db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        readings = db.execute("SELECT COUNT(*) FROM readings").fetchone()[0]
        open_alerts = db.execute("SELECT COUNT(*) FROM alerts WHERE state='open'").fetchone()[0]
        resets = db.execute("SELECT COUNT(*) FROM alerts WHERE state='acknowledged'").fetchone()[0]
        last = db.execute("SELECT plant, cell, ack_by FROM alerts WHERE state='acknowledged' "
                          "ORDER BY ack_ts DESC LIMIT 1").fetchone()
        db.close()
        return readings, open_alerts, resets, last
    except Exception:
        return None

def tail(path, lines=8):
    try:
        return "".join(Path(path).read_text().splitlines(keepends=True)[-lines:])
    except OSError:
        return ""

def monitor(procs, db_path, seconds=5):
    while True:
        time.sleep(seconds)
        for name, proc in procs:
            if proc.poll() is not None:
                print(f"\n{name} stopped unexpectedly. Last log lines:\n{tail(LOGS / (name + '.log'))}")
                return
        info = counts(db_path)
        if info:
            readings, open_alerts, resets, last = info
            extra = f" | last: {last[0]}/{last[1]} by {last[2]}" if last else ""
            print(f"readings stored: {readings} | open alerts: {open_alerts} | operator resets: {resets}{extra}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast-faults", action="store_true", help="machines fail often (demo of the automation)")
    parser.add_argument("--no-dashboard", action="store_true", help="do not start the Streamlit dashboard")
    parser.add_argument("--keep-data", action="store_true", help="keep the old data.db")
    args = parser.parse_args()

    dashboard = not args.no_dashboard
    if dashboard and not (ROOT / "dashboard" / "app.py").exists():
        print("dashboard/app.py not found, starting without the dashboard")
        dashboard = False

    cfg = load_config()
    ports = [cfg["broker"]["port"]] + [p["opcua_port"] for p in cfg["plants"]]
    if dashboard:
        ports.append(8501)
    busy = [p for p in ports if port_in_use(p)]
    if busy:
        sys.exit(f"Port(s) {busy} already in use. Is an old demo still running? "
                 "Stop it (Ctrl+C in its terminal) and try again.")

    db_path = ROOT / "data.db"
    if not args.keep_data and db_path.exists():
        db_path.unlink()
        print("deleted old data.db (use --keep-data to keep it)")

    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}  
    if args.fast_faults:
        env["FAULT_CHANCE"] = "0.30"

    procs, failed = start_all(build_steps(cfg, dashboard), env, ROOT, LOGS)
    try:
        if failed:
            print(f"\n{failed} did not start properly. Last log lines:\n{tail(LOGS / (failed + '.log'))}")
        else:
            print("\nDemo is running. Press Ctrl+C to stop.")
            if dashboard:
                print("Dashboard: http://localhost:8501 (give it a minute to fill with data)")
                webbrowser.open("http://localhost:8501")
            print(f"Logs: {LOGS}\n")
            monitor(procs, db_path)
    except KeyboardInterrupt:
        print()
    finally:
        stop_all(procs)


if __name__ == "__main__":
    main()