import json
import os
import tempfile
from central.alerts import AlertService, parse_ack
from central.data_processor import RuleEngine
from central.storage import Storage

RULE = {"id": "fault_reset", "metric": "status", "equals": 2, "command": "reset", "requires_ack": True}
TOPIC = "reckoning/plant_kronach/process_lab/process_line_2/cnc_2/ack"


def reading(value, cell="cnc_2"):
    return {"plant": "plant_kronach", "area": "process_lab", "line": "process_line_2", "cell": cell,
            "metric": "status", "value": value, "timestamp": "2026-12-01T08:00:00+00:00"}


def setup(tmp):
    storage = Storage(os.path.join(tmp, "t.db"))
    commands = []
    service = AlertService(storage, lambda loc, rule: commands.append((loc["cell"], rule["command"])))
    engine = RuleEngine([RULE], lambda p, r: service.open(p, r), on_clear=lambda p, r: service.clear(p, r))
    return storage, service, engine, commands


def ack(service, operator="Operator A", cell="cnc_2", rule="fault_reset"):
    return service.acknowledge("plant_kronach", "process_lab", "process_line_2", cell, rule, operator)


def test_fault_creates_an_alert_but_sends_no_command():
    with tempfile.TemporaryDirectory() as d:
        storage, service, engine, commands = setup(d)
        engine.process(reading(2))
        assert commands == []                          # nothing is reset automatically
        assert [a["state"] for a in storage.alerts()] == ["open"]


def test_only_one_open_alert_per_fault():
    with tempfile.TemporaryDirectory() as d:
        storage, service, engine, commands = setup(d)
        engine.process(reading(2))
        engine.process(reading(2))
        assert len(storage.alerts()) == 1


def test_operator_acknowledgement_sends_the_command_once():
    with tempfile.TemporaryDirectory() as d:
        storage, service, engine, commands = setup(d)
        engine.process(reading(2))
        assert ack(service) is True
        assert commands == [("cnc_2", "reset")]
        alert = storage.alerts()[0]
        assert alert["state"] == "acknowledged" and alert["ack_by"] == "Operator A"
        assert ack(service) is False                   
        assert commands == [("cnc_2", "reset")]


def test_acknowledgement_without_an_open_alert_is_ignored():
    with tempfile.TemporaryDirectory() as d:
        storage, service, engine, commands = setup(d)
        assert ack(service) is False                   
        engine.process(reading(2, "cnc_1"))
        assert ack(service, cell="cnc_2") is False     
        assert ack(service, cell="cnc_1", rule="other_rule") is False
        assert commands == []


def test_alert_clears_when_the_machine_recovers_by_itself():
    with tempfile.TemporaryDirectory() as d:
        storage, service, engine, commands = setup(d)
        engine.process(reading(2))
        engine.process(reading(0))
        assert [a["state"] for a in storage.alerts()] == ["cleared"]
        assert ack(service) is False                   
        assert commands == []


def test_a_new_fault_after_a_reset_creates_a_new_alert():
    with tempfile.TemporaryDirectory() as d:
        storage, service, engine, commands = setup(d)
        engine.process(reading(2))
        ack(service)
        engine.process(reading(0))                     
        engine.process(reading(2))                     
        assert [a["state"] for a in storage.alerts()] == ["acknowledged", "open"]


def test_parse_ack():
    parts = parse_ack(TOPIC, json.dumps({"operator": " Operator A ", "rule": "fault_reset"}))
    assert parts == ("plant_kronach", "process_lab", "process_line_2", "cnc_2", "fault_reset", "Operator A")


def test_parse_ack_rejects_bad_input():
    good = json.dumps({"operator": "A", "rule": "r"})
    bad = [
        (TOPIC, "not json"),
        (TOPIC, json.dumps({"rule": "r"})),
        (TOPIC, json.dumps({"operator": "", "rule": "r"})),
        (TOPIC, json.dumps({"operator": "x" * 51, "rule": "r"})),
        (TOPIC, json.dumps({"operator": 5, "rule": "r"})),
        ("reckoning/plant_kronach/cnc_2/ack", good),
        ("reckoning/plant_kronach/process_lab/process_line_2/cnc_2/command", good),
    ]
    for topic, payload in bad:
        try:
            parse_ack(topic, payload)
        except ValueError:
            continue
        raise AssertionError(f"should have been rejected: {topic} {payload}")