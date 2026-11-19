import json
import paho.mqtt.client as mqtt
from central.alerts import AlertService, parse_ack
from central.data_processor import RuleEngine
from central.storage import Storage
from config.loader import load_config


def main():
    cfg = load_config()
    enterprise = cfg["enterprise"]
    storage = Storage("data.db")

    def send_command(location, rule):
        topic = "/".join([enterprise, location["plant"], location["area"],
                          location["line"], location["cell"], "command"])
        # retain=False: a command is an instruction for now, not a state to remember
        client.publish(topic, json.dumps({"action": rule["command"]}), qos=1, retain=False)
        storage.save_action(location, rule["id"], rule["command"])
        print(f"COMMAND {rule['command']}: {location['plant']}/{location['cell']} ({rule['id']})")

    alerts = AlertService(storage, send_command)

    def needs_operator(rule):
        return rule.get("requires_ack", True)     
    def on_fault(payload, rule):
        if needs_operator(rule):
            alerts.open(payload, rule)            
        else:
            send_command(payload, rule)            

    def on_clear(payload, rule):
        if needs_operator(rule):
            alerts.clear(payload, rule)

    def escalate(payload, rule):                  
        storage.save_action(payload, rule["id"], "ALERT: reset limit reached, maintenance needed")
        print(f"ALERT {rule['id']}: {payload['plant']}/{payload['cell']} "
              "reached the reset limit, maintenance needed")

    engine = RuleEngine(cfg.get("rules", []), on_fault, escalate, on_clear=on_clear)

    def on_connect(client, userdata, flags, reason_code, properties):
        client.subscribe(f"{enterprise}/#", qos=1)
        print("connected, subscribed to", f"{enterprise}/#")

    def on_message(client, userdata, message):
        if message.topic.endswith("/command"):
            return                      
        if message.topic.endswith("/ack"):
            try:
                alerts.acknowledge(*parse_ack(message.topic, message.payload))
            except ValueError as error:
                print(f"ACK ignored: {error}")
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