import os
import sqlite3
import tempfile
from central.data_processor import RuleEngine
from central.storage import Storage

RULE = {"id": "auto_reset_on_fault", "metric": "status", "equals": 2, "command": "reset"}

LIMITED = {"id": "auto_reset_on_fault", "metric": "status", "equals": 2, "command": "reset",
           "max_resets": 2, "window_seconds": 60}


def reading(metric, value, cell="cnc_2"):
    return {"plant": "plant_kronach", "area": "process_lab", "line": "process_line_2",
            "cell": cell, "metric": metric, "value": value, "timestamp": "2026-12-01T08:00:00+00:00"}


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def fault_and_recover(engine, cell="cnc_2"):
    engine.process(reading("status", 2, cell))
    engine.process(reading("status", 0, cell))


def test_fault_triggers_exactly_one_command():
    sent = []
    engine = RuleEngine([RULE], lambda p, r: sent.append((p["cell"], r["command"])))
    engine.process(reading("status", 2))
    engine.process(reading("status", 2))
    assert sent == [("cnc_2", "reset")]


def test_rule_rearms_after_recovery():
    sent = []
    engine = RuleEngine([RULE], lambda p, r: sent.append(p["cell"]))
    engine.process(reading("status", 2))
    engine.process(reading("status", 0))
    engine.process(reading("status", 2))
    assert len(sent) == 2


def test_other_metrics_and_values_do_nothing():
    sent = []
    engine = RuleEngine([RULE], lambda p, r: sent.append(1))
    engine.process(reading("temperature", 2))
    engine.process(reading("status", 1))
    assert sent == []


def test_machines_are_tracked_separately():
    sent = []
    engine = RuleEngine([RULE], lambda p, r: sent.append(p["cell"]))
    engine.process(reading("status", 2, "cnc_1"))
    engine.process(reading("status", 2, "cnc_2"))
    assert sorted(sent) == ["cnc_1", "cnc_2"]


def test_storage_saves_readings_and_actions():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "t.db")
        s = Storage(path)
        s.save_reading(reading("temperature", 70.5))
        s.save_action(reading("status", 2), "auto_reset_on_fault", "reset")
        s.close()
        db = sqlite3.connect(path)
        assert db.execute("SELECT metric, value FROM readings").fetchall() == [("temperature", 70.5)]
        assert db.execute("SELECT rule, command FROM actions").fetchall() == [("auto_reset_on_fault", "reset")]


def test_breaker_stops_commands_and_alerts_once():
    sent, alerts, clock = [], [], FakeClock()
    engine = RuleEngine([LIMITED], lambda p, r: sent.append(1), lambda p, r: alerts.append(p["cell"]), clock)
    for t in (0, 10, 20, 30):         
        clock.now = t
        fault_and_recover(engine)
    assert len(sent) == 2             
    assert alerts == ["cnc_2"]         


def test_breaker_resets_after_the_window():
    sent, alerts, clock = [], [], FakeClock()
    engine = RuleEngine([LIMITED], lambda p, r: sent.append(1), lambda p, r: alerts.append(1), clock)
    for t in (0, 10, 20):
        clock.now = t
        fault_and_recover(engine)
    assert len(sent) == 2 and len(alerts) == 1
    clock.now = 100                   
    fault_and_recover(engine)
    assert len(sent) == 3              


def test_breaker_counts_machines_separately():
    sent, clock = [], FakeClock()
    engine = RuleEngine([LIMITED], lambda p, r: sent.append(p["cell"]), None, clock)
    for cell in ("cnc_1", "cnc_2"):
        for t in (0, 1):
            clock.now = t
            fault_and_recover(engine, cell)
    assert sorted(sent) == ["cnc_1", "cnc_1", "cnc_2", "cnc_2"]


def test_rule_without_limit_never_blocks():
    sent, clock = [], FakeClock()
    engine = RuleEngine([RULE], lambda p, r: sent.append(1), None, clock)
    for t in range(10):
        clock.now = t
        fault_and_recover(engine)
    assert len(sent) == 10

def test_on_clear_is_called_when_the_fault_ends():
    cleared = []
    engine = RuleEngine([RULE], lambda p, r: None, on_clear=lambda p, r: cleared.append(p["cell"]))
    engine.process(reading("status", 0))             
    engine.process(reading("status", 2))
    engine.process(reading("status", 0))
    engine.process(reading("status", 0))              
    assert cleared == ["cnc_2"]