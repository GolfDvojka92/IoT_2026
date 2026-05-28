from datetime import datetime
import time
import json
import threading
import paho.mqtt.client as mqtt
from shared.mqtt_module import MQTTModule
from shared.ssdp_module import SSDPModule

MAX_AGE            = 120        # in full implementation all devices should get their max_age, this is done for simplicity

# Subscribes to
ALL_TOPICS = "baby/#"
# Device types
TOPIC_FAN_TYPE     = "urn:babymonitor:device:TemperatureSensor:1"
TOPIC_HEATER_TYPE  = "urn:babymonitor:device:LightSensor:1"
TOPIC_MOTOR_TYPE   = "urn:babymonitor:device:Microphone:1"
TOPIC_SPEAKER_TYPE = "urn:babymonitor:device:Fan:1"
TOPIC_LAMP_TYPE    = "urn:babymonitor:device:Heater:1"
TOPIC_LIGHT_TYPE   = "urn:babymonitor:device:Speaker:1"
TOPIC_MIC_TYPE     = "urn:babymonitor:device:Lamp:1"
TOPIC_TEMP_TYPE    = "urn:babymonitor:device:Toy:1"

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
DEVICE_ID           = "controller"
PUBLISH_INTERVAL    = 10                                   # seconds between readings in normal operation
DEVICE_TYPE         = "urn:babymonitor:controller:1"
DEVICE_LOCATION     = "http://localhost/description.xml"   # placeholder

ALLOWED_DEVICE_TYPES = (
    TOPIC_FAN_TYPE,
    TOPIC_HEATER_TYPE,
    TOPIC_MOTOR_TYPE,
    TOPIC_SPEAKER_TYPE,
    TOPIC_LAMP_TYPE,
    TOPIC_LIGHT_TYPE,
    TOPIC_MIC_TYPE,
    TOPIC_TEMP_TYPE,
    "urn:babymonitor:controller:1"
)

class Controller:

    def __init__(self):
        self.device_status  = {}    # usn -> "online" | "offline" | "unavailable"
        self.last_seen      = {}    # usn -> datetime

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

            
        except Exception as e:
            print("Error:", e)

    # Max age expiry check
    def _check_expiry(self):
        while True:
            now = datetime.now()
            for usn, last in list(self.last_seen.items()):  # list() to avoid mutation during iteration
                elapsed = (now - last).total_seconds()
                if elapsed > MAX_AGE and self.device_status.get(usn) == "online":
                    self.device_status[usn] = "unavailable"
                    print(f"[controller] Device went unavailable (MAX_AGE expired): {usn}")
            time.sleep(5)

    # SSDP message handling
    def _handle_ssdp_message(self, message: str, addr: tuple):

        nt = self.ssdp._parse_header(message, "NT")
        usn = self.ssdp._parse_header(message, "USN")
        
        if "ssdp:alive" in message:
            if nt in ALLOWED_DEVICE_TYPES:
                self.device_status[usn] = "online"
                self.last_seen[usn]     = datetime.now()
                print(f"[controller] Authorized device online: {usn} at {addr[0]}")
            else:
                print(f"[controller] WARNING: Unauthorized device ignored — NT='{nt}' USN='{usn}' IP={addr[0]}")

        elif "ssdp:byebye" in message:
            if nt in ALLOWED_DEVICE_TYPES:
                self.device_status[usn] = "online"
                self.last_seen.pop(usn, None);
                print(f"[controller] Authorized device offline: {usn} at {addr[0]}")
            else:
                print(f"[controller] WARNING: Byebye from unauthorized device ignored — NT='{nt}' IP={addr[0]}")

        elif "M-SEARCH" in message:
            pass  # ignore search requests from other devices


    # --------------- START ----------------
    def start(self):
        print("[controller] Starting...")

        self.ssdp.start_listener()
        self.ssdp.search("ssdp:all")

        self.mqtt.connect()

        threading.Thread(target=self._check_expiry, daemon=True).start()

        while True:
            time.sleep(1)


if __name__ == "__main__":
    c = Controller()
    try:
        c.start()
    except KeyboardInterrupt:
        print("Stopping controller...")
