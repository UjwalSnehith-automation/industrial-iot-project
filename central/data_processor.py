import time
from collections import defaultdict, deque


class RuleEngine:
    
    def __init__(self, rules, send_command, escalate=None, clock=time.monotonic):
        self.rules = rules
        self.send_command = send_command   
        self.escalate = escalate           
        self.clock = clock                 
        self.active = set()                
        self.history = defaultdict(deque)  
        self.alerted = set()               

    def _allowed(self, rule, key):
        limit = rule.get("max_resets")
        if limit is None:                  
            return True
        now = self.clock()
        window = rule.get("window_seconds", 120)
        times = self.history[key]
        while times and now - times[0] > window:
            times.popleft()                
        if len(times) >= limit:
            return False
        times.append(now)
        return True

    def process(self, payload):
        for rule in self.rules:
            if payload["metric"] != rule["metric"]:
                continue
            key = (rule["id"], payload["plant"], payload["area"], payload["line"], payload["cell"])
            if payload["value"] == rule["equals"]:
                if key not in self.active:
                    self.active.add(key)
                    if self._allowed(rule, key):
                        self.alerted.discard(key)
                        self.send_command(payload, rule)
                    elif key not in self.alerted:
                        self.alerted.add(key)
                        if self.escalate:
                            self.escalate(payload, rule)
            else:
                self.active.discard(key)