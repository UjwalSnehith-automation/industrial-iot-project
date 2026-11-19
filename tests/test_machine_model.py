import random
from simulators import machine_model
from simulators.machine_model import MachineModel

def faulty_machine():
    m = MachineModel()
    m.status = 2
    return m

def test_a_fault_stays_until_a_reset():
    random.seed(1)
    m = faulty_machine()
    for _ in range(500):
        values = m.step()
    assert values["status"] == 2                      

def test_reset_clears_a_fault():
    m = faulty_machine()
    m.apply_command("reset")
    assert m.status == 0

def test_reset_is_ignored_when_there_is_no_fault():
    m = MachineModel()
    m.status = 1
    m.apply_command("reset")
    assert m.status == 1

def test_unknown_commands_are_ignored():
    m = faulty_machine()
    m.apply_command("shutdown")
    assert m.status == 2

def test_automatic_repair_can_be_switched_on():
    old = machine_model.REPAIR_CHANCE
    machine_model.REPAIR_CHANCE = 1.0
    try:
        m = faulty_machine()
        m.step()
        assert m.status == 0
    finally:
        machine_model.REPAIR_CHANCE = old