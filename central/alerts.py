import json
from datetime import datetime, timezone


def parse_ack(topic, payload):
    parts = topic.split("/")
    if len(parts) != 6 or parts[-1] != "ack":
        raise ValueError(f"not an acknowledgement topic: {topic}")
    try:
        data = json.loads(payload)
        operator, rule = data["operator"], data["rule"]
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError(f"bad acknowledgement payload: {payload!r}") from error
    if not isinstance(operator, str) or not operator.strip() or len(operator) > 50:
        raise ValueError("an operator name (1 to 50 characters) is required")
    if not isinstance(rule, str):
        raise ValueError("a rule id is required")
    return parts[1], parts[2], parts[3], parts[4], rule, operator.strip()


class AlertService:

    def __init__(self, storage, send_command):
        self.storage = storage
        self.send_command = send_command

    def open(self, payload, rule):
        created = self.storage.open_alert(payload, rule["id"], rule["command"])
        if created:
            print(f"ALERT {rule['id']}: {payload['plant']}/{payload['cell']} is in fault, "
                  "operator action needed")
        return created

    def clear(self, payload, rule):
        self.storage.clear_alert(payload, rule["id"])

    def acknowledge(self, plant, area, line, cell, rule_id, operator):
        now = datetime.now(timezone.utc).isoformat()
        alert = self.storage.acknowledge_alert(plant, area, line, cell, rule_id, operator, now)
        if alert is None:
            print(f"ACK ignored: no open alert for {plant}/{cell} ({rule_id})")
            return False
        location = {"plant": plant, "area": area, "line": line, "cell": cell, "timestamp": now}
        self.send_command(location, {"id": alert["rule"], "command": alert["command"]})
        print(f"ACK by {operator}: {plant}/{cell} -> {alert['command']}")
        return True