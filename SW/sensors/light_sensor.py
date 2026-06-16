from datetime import datetime
from shared.base_sensor import BaseSensor

TOPIC_READING    = "baby/sensor/light"
TOPIC_STATE      = "baby/sensor/light/state"
DEVICE_ID        = "light_sensor_01"
PUBLISH_INTERVAL = 10
DEVICE_TYPE      = "urn:babymonitor:device:LightSensor:1"
DEVICE_LOCATION  = "http://192.168.1.10:8080/description.xml"

class LightSensor(BaseSensor):
    DEVICE_ID        = DEVICE_ID
    DEVICE_TYPE      = DEVICE_TYPE
    DEVICE_LOCATION  = DEVICE_LOCATION
    TOPIC_READING    = TOPIC_READING
    PUBLISH_INTERVAL = PUBLISH_INTERVAL
    TOPIC_STATE      = TOPIC_STATE

    def __init__(self):
        super().__init__()
        self.light = 900
        self.step = -50

    def _read(self):
        self.light += self.step

        if self.light <= 50:
            self.light = 50
            self.step = 50
        elif self.light >= 900:
            self.light = 900
            self.step = -50
        return self.light

    def _build_payload(self, value):
        return {
            "usn": self.usn,
            "device_id": self.DEVICE_ID,
            "light": value,
            "unit": "lux",
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    sensor = LightSensor()
    try:
        sensor.start()
    except KeyboardInterrupt:
        sensor.stop()