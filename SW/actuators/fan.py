# fan.py
from shared.base_actuator import BaseActuator

class Fan(BaseActuator):
    DEVICE_ID       = "fan_01"
    DEVICE_TYPE     = "urn:babymonitor:device:Fan:1"
    DEVICE_LOCATION = "http://192.168.1.10:8080/description.xml"
    TOPIC_CMD       = "baby/actuator/fan/cmd"
    TOPIC_STATE     = "baby/actuator/fan/state"
    LABEL           = "fan"

if __name__ == "__main__":
    device = Fan()
    try:
        device.start()
    except KeyboardInterrupt:
        device.stop()