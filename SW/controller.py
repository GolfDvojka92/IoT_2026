import time
import json
import threading
import paho.mqtt.client as mqtt
from shared.mqtt_module import MQTTModule
from shared.ssdp_module import SSDPModule

# Subscribes to
ALL_TOPICS = "baby/#"
# Actuator state confirmations (what each actuator reports it is doing)
TOPIC_FAN_STATE     = "baby/actuator/fan/state"
TOPIC_HEATER_STATE  = "baby/actuator/heater/state"
TOPIC_MOTOR_STATE   = "baby/actuator/motor/state"
TOPIC_SPEAKER_STATE = "baby/actuator/speaker/state"
TOPIC_LAMP_STATE    = "baby/actuator/lamp/state"

# Publishes to
## actuator commands
TOPIC_FAN_CMD       = "baby/actuator/fan/cmd"
TOPIC_HEATER_CMD    = "baby/actuator/heater/cmd"
TOPIC_MOTOR_CMD     = "baby/actuator/motor/cmd"
TOPIC_SPEAKER_CMD   = "baby/actuator/speaker/cmd"
TOPIC_LAMP_CMD      = "baby/actuator/lamp/cmd"
## parent notifications
TOPIC_STATUS        = "baby/parent/notifications"

# ---------------------------------#
#              CONFIG              #
# ---------------------------------#
DEVICE_ID        = "controller"
PUBLISH_INTERVAL = 10                                   # seconds between readings in normal operation
DEVICE_TYPE      = "urn:babymonitor:controller:1"
DEVICE_LOCATION  = "http://localhost/description.xml"   # placeholder


class Controller:

    def __init__(self):
        self.devices = {
            "temp_sensor"   : False,
            "light_sensor"  : False,
            "microphone"    : False,
            "fan"           : False,
            "heater"        : False,
            "motor"         : False,
            "speaker"       : False,
            "lamp"          : False,
        }

        self.state = {
            "temperature"   : None,
            "light"         : None,
            "microphone"    : None,
            "fan"           : None,
            "heater"        : None,
            "motor"         : None,
            "speaker"       : None,
            "lamp"          : None,
        }

        # MQTT client
        self.mqtt = MQTTModule(
            device_id = DEVICE_ID,
            subscriptions = [
                ALL_TOPICS
            ]
        )
        self.mqtt._on_message = self._on_message

        # SSDP
        self.ssdp = SSDPModule(
            device_id   = DEVICE_ID,
            device_type = DEVICE_TYPE,
            location    = DEVICE_LOCATION
        )
        self.ssdp._handle_ssdp_message = self._handle_ssdp_message

    def _on_message(self, client, userdata, msg):
        try:
            topic   = msg.topic
            payload = json.loads(msg.payload.decode())
            print(f"[MQTT] {topic} -> {payload}")

            # SIMPLE RULE ENGINE
            if msg.topic == "baby/sensor/microphone":
                if payload.get("sound") == "CRYING":
                    print("[DECISION] Baby crying -> turning ON fan")

                    # TEST COMMAND TO FAN
                    command = {
                        "state": "ON"
                    }

                    self.client.publish(
                        "baby/actuator/fan/cmd",
                        json.dumps(command)
                    )

                    print("[CONTROLLER] Sent FAN ON command")
            elif msg.topic in (
                    TOPIC_FAN_STATE,
                    TOPIC_HEATER_STATE,
                    TOPIC_MOTOR_STATE,
                    TOPIC_SPEAKER_STATE,
                    TOPIC_LAMP_STATE
                ):
                self._handle_actuator_state(topic, payload)
        except Exception as e:
            print("Error:", e)

    def _handle_actuator_state(self, topic: str, payload: dict):
        # Map topic to devices key
        mapping = {
            TOPIC_FAN_STATE:     "fan",
            TOPIC_HEATER_STATE:  "heater",
            TOPIC_MOTOR_STATE:   "motor",
            TOPIC_SPEAKER_STATE: "speaker",
            TOPIC_LAMP_STATE:    "lamp",
        }
        key = mapping.get(topic)
        self.devices[key] = (payload.get("status") == "online")

    # SSDP message handling
    def _handle_ssdp_message(self, message: str, addr: str):
        if "ssdp:alive" in message:
            print(f"[{self.device_id}] Device came online: {addr[0]}")
        elif "ssdp:byebye" in message:
            print(f"[{self.device_id}] Device went offline: {addr[0]}")
        elif "M-SEARCH" in message:
            pass  # ignore search requests from other devices


    # --------------- START ----------------
    def start(self):
        print("[CONTROLLER] Starting...")

        self.ssdp.start_listener()
        self.ssdp.search("ssdp:all")

        self.mqtt.connect()

        while True:
            time.sleep(1)


if __name__ == "__main__":
    c = Controller()
    try:
        c.start()
    except KeyboardInterrupt:
        print("Stopping controller...")
