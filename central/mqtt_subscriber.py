import json
import paho.mqtt.client as mqtt
from central.data_processor import RuleEngine
from central.storage import Storage
from config.loader import load_config

def main():
    cfg = load_config()
    enterprise = cfg["enterprise"]
    storage = Storage("data.db")

    def send_command(payload, rule):
        topic = "/".join([enterprise, payload["plant"], payload["area"],
                          payload["line"], payload["cell"], "command"])
        client.publish(topic, json.dumps({"action": rule["command"]}), qos=1, retain=False)
        storage.save_action(payload, rule["id"], rule["command"])
        print(f"RULE {rule['id']}: {payload['plant']}/{payload['cell']} -> {rule['command']}")

    def escalate(payload, rule):
        storage.save_action(payload, rule["id"], "ALERT: reset limit reached, maintenance needed")
        print(f"ALERT {rule['id']}: {payload['plant']}/{payload['cell']} "
              "reached the reset limit, maintenance needed")

    engine = RuleEngine(cfg.get("rules", []), send_command, escalate)

    def on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe(f"{enterprise}/#", qos=1)
        print("connected, subscribed to", f"{enterprise}/#")

    def on_message(client, userdata, message):
        if message.topic.endswith("/command"):
            return                      
        payload = json.loads(message.payload)
        storage.save_reading(payload)
        engine.process(payload)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(cfg["broker"]["host"], cfg["broker"]["port"])
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        pass
    finally:
        storage.close()


if __name__ == "__main__":
    main()