import json
import paho.mqtt.client as mqtt

class MqttPublisher:
    def __init__(self, host, port):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.connect(host, port)
        self.client.loop_start()

    def publish(self, message):
        self.client.publish(message["topic"], json.dumps(message["payload"]), qos=1, retain=True)

    def close(self):
        self.client.loop_stop()
        self.client.disconnect()