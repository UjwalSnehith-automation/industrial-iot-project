import os
import random

FAULT_CHANCE = float(os.environ.get("FAULT_CHANCE", "0.03"))

REPAIR_CHANCE = float(os.environ.get("REPAIR_CHANCE", "0.0"))


class MachineModel:

    def __init__(self):
        self.temperature = 25.0
        self.part_count = 0
        self.status = 0

    def apply_command(self, command):
        if command == "reset" and self.status == 2:
            self.status = 0

    def step(self):
        if self.status == 2:
            if random.random() < REPAIR_CHANCE:
                self.status = 0
        elif self.status == 0:
            if random.random() < 0.20:
                self.status = 1
        else:
            r = random.random()
            if r < FAULT_CHANCE:
                self.status = 2
            elif r < FAULT_CHANCE + 0.05:
                self.status = 0

        target = 70.0 if self.status == 1 else 25.0
        self.temperature += (target - self.temperature) * 0.2 + random.uniform(-0.5, 0.5)

        if self.status == 1:
            self.part_count += random.randint(0, 2)
            power = 12.0 + random.uniform(-1.0, 1.0)
        else:
            power = 0.5

        return {
            "temperature": round(self.temperature, 2),
            "power": round(power, 2),
            "part_count": self.part_count,
            "status": self.status,
        }