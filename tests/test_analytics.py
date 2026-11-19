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


def test_load_alerts_and_the_ack_message_fit_the_center():
    from central.alerts import parse_ack
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "t.db")
        s = Storage(db)
        p = {"plant": "plant_kronach", "area": "process_lab", "line": "process_line_1",
             "cell": "printer_1", "timestamp": "2026-12-01T08:00:00+00:00"}
        s.open_alert(p, "fault_reset", "reset")
        s.open_alert({**p, "cell": "printer_2"}, "fault_reset", "reset")
        s.acknowledge_alert("plant_kronach", "process_lab", "process_line_1", "printer_2",
                            "fault_reset", "Operator A", "2026-12-01T08:01:00+00:00")
        s.close()
        alerts = analytics.load_alerts(db)
        assert list(alerts["state"]) == ["acknowledged", "open"]         
        assert alerts.iloc[0]["ack_by"] == "Operator A"
        open_alert = alerts[alerts.state == "open"].iloc[0].to_dict()
        topic, payload = analytics.ack_message("reckoning", open_alert, "Operator B")
        # what the dashboard sends must be accepted by the center's parser
        assert parse_ack(topic, payload) == (
            "plant_kronach", "process_lab", "process_line_1", "printer_1", "fault_reset", "Operator B")


def test_load_alerts_without_a_table_is_empty():
    with tempfile.TemporaryDirectory() as d:
        db = os.path.join(d, "old.db")
        import sqlite3
        sqlite3.connect(db).execute("CREATE TABLE readings (ts TEXT)").connection.commit()
        assert analytics.load_alerts(db).empty