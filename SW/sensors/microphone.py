import random
import time
from shared.base_sensor import BaseSensor

TOPIC_READING    = "baby/sensor/microphone"
TOPIC_STATE      = "baby/sensor/microphone/state"

DEVICE_ID        = "microphone_01"
PUBLISH_INTERVAL = 10
DEVICE_TYPE      = "urn:babymonitor:device:Microphone:1"
DEVICE_LOCATION  = "http://192.168.1.10:8080/description.xml"

class Microphone(BaseSensor):

    DEVICE_ID        = DEVICE_ID
    DEVICE_TYPE      = DEVICE_TYPE
    DEVICE_LOCATION  = DEVICE_LOCATION
    TOPIC_READING    = TOPIC_READING
    TOPIC_STATE      = TOPIC_STATE
    PUBLISH_INTERVAL = PUBLISH_INTERVAL

    def _read(self):
        # TODO: replace with actual sensor reading - use model
        return random.choice(["QUIET", "NOISE", "CRYING"])

    def _build_payload(self, value) -> dict:
        return {
            "device_id": self.DEVICE_ID,
            "sound":     value,
            "timestamp": time.time()
        }


if __name__ == "__main__":
    sensor = Microphone()
    try:
        sensor.start()
    except KeyboardInterrupt:
        sensor.stop()