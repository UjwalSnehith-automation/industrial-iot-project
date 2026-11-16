from datetime import datetime, timedelta, timezone
import pytest
from gateway.normalizer import normalize

UNITS = {"temperature": "degC", "status": "0=idle, 1=running, 2=fault"}
PATH = ["reckoning", "plant_coburg", "decision_lab", "decision_line_1", "robot_arm_1", "temperature"]

def test_topic_is_the_full_path():
    msg = normalize(PATH, 70.5, UNITS)
    assert msg["topic"] == "reckoning/plant_coburg/decision_lab/decision_line_1/robot_arm_1/temperature"

def test_payload_has_all_levels_value_and_unit():
    p = normalize(PATH, 70.5, UNITS)["payload"]
    assert p["plant"] == "plant_coburg" and p["cell"] == "robot_arm_1"
    assert p["value"] == 70.5 and p["unit"] == "degC"

def test_timestamp_is_utc():
    p = normalize(PATH, 1, UNITS, datetime(2026, 12, 1, 8, 0))["payload"]
    assert p["timestamp"] == "2026-12-01T08:00:00+00:00"

def test_source_and_receive_time_are_both_kept():
    machine_time = datetime.now(timezone.utc) - timedelta(seconds=5)
    p = normalize(PATH, 1, UNITS, machine_time)["payload"]
    assert datetime.fromisoformat(p["timestamp"]) == machine_time
    delay = datetime.fromisoformat(p["received_timestamp"]) - datetime.fromisoformat(p["timestamp"])
    assert timedelta(seconds=4) < delay < timedelta(seconds=7)

def test_without_source_time_the_receive_time_is_used():
    p = normalize(PATH, 1, UNITS)["payload"]
    assert p["timestamp"] == p["received_timestamp"]

def test_wrong_path_length_is_rejected():
    with pytest.raises(ValueError):
        normalize(PATH[:4], 1, UNITS)