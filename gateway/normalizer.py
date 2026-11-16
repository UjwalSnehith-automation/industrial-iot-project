from datetime import datetime, timezone

def normalize(path, value, units, timestamp=None):
    if len(path)!=6:
        raise ValueError(f"expected 6 path levels, got {path}")
    enterprise, plant, area, line, cell, metric = path

    ts = timestamp or datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    
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
            "timestamp": ts.isoformat(),
        },
    }