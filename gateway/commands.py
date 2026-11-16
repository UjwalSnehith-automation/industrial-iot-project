import json

ALLOWED_ACTIONS = {"reset"}

def parse_command(topic, payload):
    
    parts = topic.split("/")
    if len(parts) != 6 or parts[-1] != "command":
        raise ValueError(f"not a command topic: {topic}")
    try:
        action = json.loads(payload)["action"]
    except (ValueError, KeyError, TypeError) as error:
        raise ValueError(f"bad command payload: {payload!r}") from error
    if action not in ALLOWED_ACTIONS:
        raise ValueError(f"action not allowed: {action!r}")
    return parts, action