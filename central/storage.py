import sqlite3

class Storage:

    def __init__(self, path="data.db"):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS readings (ts TEXT, plant TEXT, area TEXT, line TEXT,cell TEXT, metric TEXT, value REAL)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS actions (ts TEXT, plant TEXT, area TEXT, line TEXT,cell TEXT, rule TEXT, command TEXT)""")
        self.db.commit()

    def save_reading(self, p):
        self.db.execute("INSERT INTO readings VALUES (?,?,?,?,?,?,?)",(p["timestamp"], p["plant"], p["area"], p["line"], p["cell"], p["metric"], float(p["value"])),)
        self.db.commit()

    def save_action(self, p, rule_id, command):
        self.db.execute("INSERT INTO actions VALUES (?,?,?,?,?,?,?)",(p["timestamp"], p["plant"], p["area"], p["line"], p["cell"], rule_id, command),)
        self.db.commit()

    def close(self):
        self.db.close()