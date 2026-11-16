import asyncio

from asyncua import Client, ua

from config.loader import load_config


async def walk(node, depth=0):
    for child in await node.get_children():
        name = (await child.read_browse_name()).Name
        if await child.read_node_class() == ua.NodeClass.Variable:
            print("  " * depth + f"{name} = {await child.read_value()}")
        else:
            print("  " * depth + name)
            await walk(child, depth + 1)


async def main():
    cfg = load_config()
    port = cfg["plants"][2]["opcua_port"]
    async with Client(f"opc.tcp://localhost:{port}/") as client:
        root = await client.nodes.objects.get_child(
            [f"{await client.get_namespace_index(f'urn:{cfg['enterprise']}:{cfg['plants'][2]['id']}')}:{cfg['enterprise']}"]
        )
        print(name)
        await walk(root)


asyncio.run(main())