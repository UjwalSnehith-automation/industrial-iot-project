import asyncio
import logging
from asyncua import Client
from config.loader import load_config
from gateway.normalizer import normalize

log = logging.getLogger("gateway")

class Handler:

    def __init__(self, paths, units, on_message):
        self.paths = paths            
        self.units = units
        self.on_message = on_message  

    def datachange_notification(self, node, value, data):
        path = self.paths[node.nodeid.to_string()]
        try:
            source_time = data.monitored_item.Value.SourceTimestamp
        except AttributeError:
            source_time = None
        self.on_message(normalize(path, value, self.units, source_time))

async def wait_and_apply_command(client, idx, commands, timeout=2):
    if commands is None:
        await asyncio.sleep(timeout)
        return
    try:
        parts, action = await asyncio.wait_for(commands.get(), timeout)
    except asyncio.TimeoutError:
        return
    try:
        node = await client.nodes.objects.get_child([f"{idx}:{p}" for p in parts])
        await node.write_value(action)
        log.info("command '%s' written to %s", action, "/".join(parts))
    except Exception as error:
        log.warning("could not send command to %s: %s", "/".join(parts), error)

async def read_plant(cfg, plant, on_message, commands=None):
    enterprise = cfg["enterprise"]
    url = f"opc.tcp://localhost:{plant['opcua_port']}/"
    while True:
        try:
            async with Client(url) as client:
                idx = await client.get_namespace_index(f"urn:{enterprise}:{plant['id']}")
                nodes, paths = [], {}
                for area in plant["areas"]:
                    for line in area["lines"]:
                        for cell in line["cells"]:
                            for metric in cfg["metrics"]:
                                path = [enterprise, plant["id"], area["id"], line["id"], cell, metric]
                                node = await client.nodes.objects.get_child([f"{idx}:{p}" for p in path])
                                nodes.append(node)
                                paths[node.nodeid.to_string()] = path
                handler = Handler(paths, cfg["metrics"], on_message)
                subscription = await client.create_subscription(500, handler)
                await subscription.subscribe_data_change(nodes)
                log.info("%s: subscribed to %d values", plant["id"], len(nodes))
                while True:
                    await wait_and_apply_command(client, idx, commands)
                    await client.check_connection()   
        except Exception as error:
            log.warning("%s: %s - retrying in 5 s", plant["id"], error)
            await asyncio.sleep(5)

async def main():
    cfg = load_config()

    def show(message):
        p = message["payload"]
        unit = "" if p["metric"] == "status" else p["unit"]
        print(f"{message['topic']} = {p['value']} {unit}")

    await asyncio.gather(*(read_plant(cfg, plant, show) for plant in cfg["plants"]))

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("asyncua").setLevel(logging.ERROR)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass