import time
from shared.base_sensor import BaseSensor

TOPIC_READING    = "baby/sensor/temperature"
TOPIC_STATE      = "baby/sensor/temperature/state"

DEVICE_ID        = "temperature_sensor_01"
PUBLISH_INTERVAL = 10
DEVICE_TYPE      = "urn:babymonitor:device:TemperatureSensor:1"
DEVICE_LOCATION  = "http://192.168.1.10:8080/description.xml"

class TemperatureSensor(BaseSensor):

    DEVICE_ID        = DEVICE_ID
    DEVICE_TYPE      = DEVICE_TYPE
    DEVICE_LOCATION  = DEVICE_LOCATION
    TOPIC_READING    = TOPIC_READING
    TOPIC_STATE      = TOPIC_STATE
    PUBLISH_INTERVAL = PUBLISH_INTERVAL

    def _read(self) -> float:
        # TODO: replace with actual sensor reading
        return 22.5  # placeholder

    def _build_payload(self, value: float) -> dict:
        return {
            "device_id":   self.DEVICE_ID,
            "temperature": value,
            "unit":        "C",
            "timestamp":   time.time()
        }


if __name__ == "__main__":
    sensor = TemperatureSensor()
    try:
        sensor.start()
    except KeyboardInterrupt:
        sensor.stop()