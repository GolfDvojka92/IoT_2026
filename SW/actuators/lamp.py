from shared.base_actuator import BaseActuator
import json

class Lamp(BaseActuator):
    DEVICE_ID       = "lamp_01"
    DEVICE_TYPE     = "urn:babymonitor:device:Lamp:1"
    DEVICE_LOCATION = "http://192.168.1.10:8080/description.xml"
    TOPIC_CMD       = "baby/actuator/lamp/cmd"
    TOPIC_STATE     = "baby/actuator/lamp/state"
    LABEL           = "lamp"

    VALID_COMMANDS = ("SET_BRIGHTNESS",)

    def __init__(self):
        super().__init__()
        self.brightness = 0

    def _on_message(self, client, userdata, msg):
        payload = json.loads(msg.payload.decode())
        cmd = payload.get("cmd")
        value = payload.get("value")

        if cmd == "SET_BRIGHTNESS":
            self.brightness = max(0, min(100, int(value)))
            self.state = "ON" if self.brightness > 0 else "OFF"

            print(f"[LAMP] Brightness = {self.brightness}%")
            self.publish_state()


if __name__ == "__main__":
    device = Lamp()
    try:
        device.start()
    except KeyboardInterrupt:
        device.stop()