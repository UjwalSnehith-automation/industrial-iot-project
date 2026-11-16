from datetime import datetime, timezone

def to_utc(ts):
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def normalize(path, value, units, timestamp=None):
    
    if len(path) != 6:
        raise ValueError(f"expected 6 path levels, got {path}")
    enterprise, plant, area, line, cell, metric = path

    received = datetime.now(timezone.utc)
    source = to_utc(timestamp) if timestamp is not None else received

    return {
        "topic": "/".join(path),
        "payload": {
            "enterprise": enterprise,
            "plant": plant,
            "area": area,
            "line": line,
            "cell": cell,
            "metric": metric,
            "value": value,
            "unit": units.get(metric, ""),
            "timestamp": source.isoformat(),
            "received_timestamp": received.isoformat(),
        },
    }