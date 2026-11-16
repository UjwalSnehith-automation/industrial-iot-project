import asyncio
import logging
from config.loader import load_config
from gateway.command_listener import CommandListener
from gateway.mqtt_publisher import MqttPublisher
from gateway.opcua_client import read_plant

async def main():
    cfg = load_config()
    broker = cfg["broker"]
    publisher = MqttPublisher(broker["host"], broker["port"])
    queues = {plant["id"]: asyncio.Queue() for plant in cfg["plants"]}
    listener = CommandListener(broker["host"], broker["port"], cfg["enterprise"],
                               queues, asyncio.get_running_loop())
    try:
        await asyncio.gather(*(
            read_plant(cfg, plant, publisher.publish, queues[plant["id"]])
            for plant in cfg["plants"]
        ))
    finally:
        listener.close()
        publisher.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("asyncua").setLevel(logging.ERROR)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass