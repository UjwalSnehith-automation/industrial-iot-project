import json
from gateway.commands import parse_command

TOPIC = "reckoning/plant_kronach/process_lab/process_line_2/cnc_2/command"

def raises_value_error(fn, *args):
    try:
        fn(*args)
    except ValueError:
        return True
    return False

def test_valid_command():
    parts, action = parse_command(TOPIC, json.dumps({"action": "reset"}))
    assert action == "reset"
    assert parts == ["reckoning", "plant_kronach", "process_lab", "process_line_2", "cnc_2", "command"]

def test_unknown_action_is_rejected():
    assert raises_value_error(parse_command, TOPIC, json.dumps({"action": "shutdown"}))

def test_bad_payload_is_rejected():
    assert raises_value_error(parse_command, TOPIC, "not json")
    assert raises_value_error(parse_command, TOPIC, json.dumps({"no_action": 1}))

def test_wrong_topic_is_rejected():
    assert raises_value_error(parse_command, "reckoning/plant_kronach/temperature", json.dumps({"action": "reset"}))