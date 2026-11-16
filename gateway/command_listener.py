import logging
import paho.mqtt.client as mqtt
from gateway.commands import parse_command

log = logging.getLogger("gateway")

class CommandListener:

    def __init__(self, host, port, enterprise, queues, loop):
        self.queues = queues            
        self.loop = loop
        self.topic = f"{enterprise}/+/+/+/+/command"
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(host, port)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, reason_code, properties):
        client.subscribe(self.topic, qos=1)
        log.info("listening for commands on %s", self.topic)

    def on_message(self, client, userdata, message):
        try:
            parts, action = parse_command(message.topic, message.payload)
        except ValueError as error:
            log.warning("ignored command: %s", error)
            return
        queue = self.queues.get(parts[1])
        if queue is None:
            log.warning("command for unknown plant %s", parts[1])
            return
        self.loop.call_soon_threadsafe(queue.put_nowait, (parts, action))

    def close(self):
        self.client.loop_stop()
        self.client.disconnect()