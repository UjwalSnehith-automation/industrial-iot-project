import sqlite3


class Storage:

    def __init__(self, path="data.db"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS readings (
                   ts TEXT, plant TEXT, area TEXT, line TEXT,
                   cell TEXT, metric TEXT, value REAL)"""
        )
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS actions (
                   ts TEXT, plant TEXT, area TEXT, line TEXT,
                   cell TEXT, rule TEXT, command TEXT)"""
        )
        self.db.execute(
            """CREATE TABLE IF NOT EXISTS alerts (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   ts TEXT, plant TEXT, area TEXT, line TEXT, cell TEXT,
                   rule TEXT, command TEXT, state TEXT, ack_ts TEXT, ack_by TEXT)"""
        )
        self.db.commit()

    def save_reading(self, p):
        self.db.execute(
            "INSERT INTO readings VALUES (?,?,?,?,?,?,?)",
            (p["timestamp"], p["plant"], p["area"], p["line"], p["cell"], p["metric"], float(p["value"])),
        )
        self.db.commit()

    def save_action(self, p, rule_id, command):
        self.db.execute(
            "INSERT INTO actions VALUES (?,?,?,?,?,?,?)",
            (p["timestamp"], p["plant"], p["area"], p["line"], p["cell"], rule_id, command),
        )
        self.db.commit()


    def open_alert(self, p, rule_id, command):
        existing = self.db.execute(
            "SELECT 1 FROM alerts WHERE plant=? AND area=? AND line=? AND cell=? AND rule=? AND state='open'",
            (p["plant"], p["area"], p["line"], p["cell"], rule_id),
        ).fetchone()
        if existing:
            return False
        self.db.execute(
            "INSERT INTO alerts (ts, plant, area, line, cell, rule, command, state) VALUES (?,?,?,?,?,?,?,'open')",
            (p["timestamp"], p["plant"], p["area"], p["line"], p["cell"], rule_id, command),
        )
        self.db.commit()
        return True

    def clear_alert(self, p, rule_id):
        self.db.execute(
            "UPDATE alerts SET state='cleared' WHERE plant=? AND area=? AND line=? AND cell=? AND rule=? AND state='open'",
            (p["plant"], p["area"], p["line"], p["cell"], rule_id),
        )
        self.db.commit()

    def acknowledge_alert(self, plant, area, line, cell, rule_id, operator, ts):
        row = self.db.execute(
            "SELECT * FROM alerts WHERE plant=? AND area=? AND line=? AND cell=? AND rule=? AND state='open'",
            (plant, area, line, cell, rule_id),
        ).fetchone()
        if row is None:
            return None
        self.db.execute(
            "UPDATE alerts SET state='acknowledged', ack_ts=?, ack_by=? WHERE id=?",
            (ts, operator, row["id"]),
        )
        self.db.commit()
        return dict(row)

    def alerts(self, state=None):
        query, args = "SELECT * FROM alerts", ()
        if state:
            query, args = query + " WHERE state=?", (state,)
        return [dict(r) for r in self.db.execute(query + " ORDER BY id", args).fetchall()]

    def close(self):
        self.db.close()