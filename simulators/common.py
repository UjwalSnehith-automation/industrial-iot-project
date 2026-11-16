import asyncio
import logging
from asyncua import Server, ua
from simulators.machine_model import MachineModel

log = logging.getLogger("simulator")

async def run_plant(cfg, plant_index):
    plant = cfg["plants"][plant_index]
    enterprise = cfg["enterprise"]

    server = Server()
    await server.init()
    server.set_endpoint(f"opc.tcp://0.0.0.0:{plant['opcua_port']}/")
    server.set_server_name(plant["name"])
    server.set_security_policy([ua.SecurityPolicyType.NoSecurity])
    idx = await server.register_namespace(f"urn:{enterprise}:{plant['id']}")

    enterprise_obj = await server.nodes.objects.add_object(idx, enterprise)
    plant_obj = await enterprise_obj.add_object(idx, plant['id'])

    machines =[]
    for area in plant["areas"]:
        area_obj = await plant_obj.add_object(idx, area['id'])
        for line in area["lines"]:
            line_obj = await area_obj.add_object(idx, line['id'])
            for cell in line["cells"]:
                cell_obj = await line_obj.add_object(idx, cell)

                nodes ={}
                for metric in cfg['metrics']:
                    initial = 0 if metric in ("part_count", "status") else 0.0
                    nodes[metric] = await cell_obj.add_variable(idx, metric, initial)

                cmd_node = await cell_obj.add_variable(idx, "command", "")
                await cmd_node.set_writable()

                machines.append((MachineModel(), nodes, cmd_node))

    async with server:
        log.info("%s running on port %s with %d machines", plant["name"], plant["opcua_port"], len(machines))
        while True:
            for model, nodes, cmd_node in machines:
                command = await cmd_node.read_value()
                if command:
                    model.apply_command(command)
                    await cmd_node.write_value("")
                values = model.step()
                for metric, node in nodes.items():
                    await node.write_value(values[metric])
            await asyncio.sleep(1)