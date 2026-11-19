import json
import os
import sqlite3
import pandas as pd
from sklearn.ensemble import IsolationForest

FEATURES = ["temperature", "power", "status"]
CELL_COLS = ["plant", "area", "line", "cell"]


def _read(db_path, query, columns):
    if not os.path.exists(db_path):
        return pd.DataFrame(columns=columns)
    try:
        db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        df = pd.read_sql_query(query, db)
        db.close()
    except Exception:
        return pd.DataFrame(columns=columns)
    df["ts"] = pd.to_datetime(df["ts"], utc=True, format="ISO8601")
    return df.sort_values("ts").reset_index(drop=True)


def load_readings(db_path="data.db", limit=50000):
    query = f"SELECT * FROM readings ORDER BY ts DESC LIMIT {int(limit)}"
    return _read(db_path, query, ["ts", *CELL_COLS, "metric", "value"])


def load_actions(db_path="data.db", limit=200):
    query = f"SELECT * FROM actions ORDER BY ts DESC LIMIT {int(limit)}"
    df = _read(db_path, query, ["ts", *CELL_COLS, "rule", "command"])
    return df.sort_values("ts", ascending=False).reset_index(drop=True)


def load_alerts(db_path="data.db", limit=500):
    columns = ["id", "ts", *CELL_COLS, "rule", "command", "state", "ack_ts", "ack_by"]
    query = f"SELECT * FROM alerts ORDER BY id DESC LIMIT {int(limit)}"
    df = _read(db_path, query, columns)
    if df.empty:
        return pd.DataFrame(columns=columns)
    df["ack_ts"] = pd.to_datetime(df["ack_ts"], utc=True, format="ISO8601", errors="coerce")
    return df.sort_values("id", ascending=False).reset_index(drop=True)


def ack_message(enterprise, alert, operator):
    topic = "/".join([enterprise, alert["plant"], alert["area"], alert["line"], alert["cell"], "ack"])
    return topic, json.dumps({"operator": operator, "rule": alert["rule"]})


def cell_frame(df, plant, area, line, cell):
    sel = df[(df.plant == plant) & (df.area == area) & (df.line == line) & (df.cell == cell)]
    if sel.empty:
        return pd.DataFrame(columns=FEATURES)
    wide = sel.pivot_table(index="ts", columns="metric", values="value", aggfunc="last")
    return wide.resample("1s").last().ffill().dropna()


def detect_anomalies(frame, contamination=0.02, min_rows=50):
    out = frame.copy()
    out["anomaly"] = False
    out["score"] = 0.0
    if any(c not in out.columns for c in FEATURES) or len(out) < min_rows:
        return out
    model = IsolationForest(contamination=contamination, random_state=42)
    model.fit(out[FEATURES])
    out["anomaly"] = model.predict(out[FEATURES]) == -1
    out["score"] = model.score_samples(out[FEATURES])
    return out


def latest_values(df):
    if df.empty:
        return pd.DataFrame()
    last = df.groupby([*CELL_COLS, "metric"]).tail(1)
    table = last.pivot_table(index=CELL_COLS, columns="metric", values="value", aggfunc="last")
    return table.reset_index()