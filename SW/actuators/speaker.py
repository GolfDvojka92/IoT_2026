import time
import json
from shared.mqtt_module import MQTTModule
from shared.ssdp_module import SSDPModule

# Topics
TOPIC_CMD   = "baby/actuator/speaker/cmd"
TOPIC_STATE = "baby/actuator/speaker/state"

# ---------------------------------#
#              CONFIG              #
# ---------------------------------#
DEVICE_ID        = "speaker_01"
DEVICE_TYPE      = "urn:babymonitor:device:Speaker:1"
DEVICE_LOCATION  = "http://192.168.1.10:8080/description.xml"

class Speaker:

    def __init__(self):
        self.state = "OFF"
        self._running = False

        # MQTT
        self.mqtt = MQTTModule(
            device_id = DEVICE_ID,
            subscriptions = [TOPIC_CMD]
        )

        # Override message handler
        self.mqtt._on_message = self.on_message

        # SSDP
        self.ssdp = SSDPModule(
            device_id = DEVICE_ID,
            device_type = DEVICE_TYPE,
            location = DEVICE_LOCATION
        )

    # ---------------------------------#
    #        MESSAGE HANDLER           #
    # ---------------------------------#
    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            command = payload.get("state")

            print(f"[SPEAKER] Command received: {command}")

            if command in ["ON", "OFF"]:
                self.state = command
                self.publish_state()

        except Exception as e:
            print("[SPEAKER] Error:", e)

    # ---------------------------------#
    #        PUBLISH STATE             #
    # ---------------------------------#
    def publish_state(self):
        payload = {
            "device_id": DEVICE_ID,
            "state": self.state,
            "timestamp": time.time()
        }

        self.mqtt.publish(TOPIC_STATE, payload)
        print(f"[SPEAKER] State -> {self.state}")

    # ---------------------------------#
    #            START                 #
    # ---------------------------------#
    def start(self):
        print(f"[{DEVICE_ID}] Starting...")

        self.ssdp.advertise()
        self.mqtt.connect()

        self.publish_state()  # initial state

        self._running = True

        while self._running:
            time.sleep(1)

    # ---------------------------------#
    #            STOP                  #
    # ---------------------------------#
    def stop(self):
        print(f"[{DEVICE_ID}] Stopping...")
        self._running = False

        self.mqtt.publish(
            TOPIC_STATE,
            {"device_id": DEVICE_ID, "state": "OFF", "status": "offline"},
            retain=True
        )

        time.sleep(0.5)
        self.ssdp.send_byebye()
        self.mqtt.disconnect()


if __name__ == "__main__":
    speaker = Speaker()
    try:
        speaker.start()
    except KeyboardInterrupt:
        speaker.stop()