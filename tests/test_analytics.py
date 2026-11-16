import os
import tempfile
from datetime import datetime, timedelta, timezone
from central.storage import Storage
from dashboard import analytics

def make_db(path, n=200, spike_at=100):
    s = Storage(path)
    t0 = datetime(2026, 12, 1, 8, 0, tzinfo=timezone.utc)
    base = {"plant": "plant_kronach", "area": "process_lab", "line": "process_line_1", "cell": "printer_1"}
    for i in range(n):
        ts = (t0 + timedelta(seconds=i)).isoformat()
        temp = 140.0 if i == spike_at else 70.0 + (i % 5) * 0.2
        for metric, value in [("temperature", temp), ("power", 12.0), ("status", 1), ("part_count", i)]:
            s.save_reading({**base, "timestamp": ts, "metric": metric, "value": value})
    s.save_action({**base, "timestamp": t0.isoformat()}, "auto_reset_on_fault", "reset")
    s.close()

def test_pipeline_flags_the_spike():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "t.db")
        make_db(db)
        df = analytics.load_readings(db)
        frame = analytics.cell_frame(df, "plant_kronach", "process_lab", "process_line_1", "printer_1")
        assert len(frame) == 200 and set(analytics.FEATURES) <= set(frame.columns)
        flagged = analytics.detect_anomalies(frame, contamination=0.01)
        assert 140.0 in flagged[flagged["anomaly"]]["temperature"].values
        latest = analytics.latest_values(df)
        assert len(latest) == 1 and latest.iloc[0]["cell"] == "printer_1"
        assert len(analytics.load_actions(db)) == 1

def test_missing_database_and_short_history():
    assert analytics.load_readings("does_not_exist.db").empty
    assert not os.path.exists("does_not_exist.db")
    import pandas as pd
    short = pd.DataFrame({"temperature": [1.0], "power": [1.0], "status": [1.0]})
    assert not analytics.detect_anomalies(short)["anomaly"].any()