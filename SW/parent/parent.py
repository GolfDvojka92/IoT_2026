from shared.base_actuator import BaseActuator

TOPIC_PARENT_CMD   = "baby/parent/control"
TOPIC_PARENT_STATE = "baby/parent/state"
TOPIC_PARENT_NOTIF = "baby/parent/notifications"
TOPIC_PARENT_ALERT = "baby/parent/alerts"

DEVICE_ID       = "parent_01"
DEVICE_LOCATION = "http://192.168.1.10:8080/description.xml"
DEVICE_TYPE     = "urn:babymonitor:device:Parent:1"
LABEL           = "parent_controller"

class Parent(BaseActuator):
    DEVICE_ID       = DEVICE_ID
    DEVICE_TYPE     = DEVICE_TYPE
    DEVICE_LOCATION = DEVICE_LOCATION
    TOPIC_CMD       = TOPIC_PARENT_CMD
    TOPIC_STATE     = TOPIC_PARENT_STATE
    LABEL           = LABEL

    def __init__(self):
        super().__init__()
        # Hook into on_connect to subscribe to extra topics after connection
        _original_on_connect = self.mqtt._on_connect
        

        def _on_connect_extended(client, userdata, flags, rc):
            _original_on_connect(client, userdata, flags, rc)
            if rc == 0:
                client.subscribe(TOPIC_PARENT_NOTIF)
                client.subscribe(TOPIC_PARENT_ALERT)
                print(f"[{LABEL}] Subscribed → {TOPIC_PARENT_NOTIF}")
                print(f"[{LABEL}] Subscribed → {TOPIC_PARENT_ALERT}")

        self.mqtt.client.on_connect = _on_connect_extended

if __name__ == "__main__":
    parent = Parent()
    try:
        parent.start()
    except KeyboardInterrupt:
        parent.stop()