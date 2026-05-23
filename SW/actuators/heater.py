from shared.base_actuator import BaseActuator

class Heater(BaseActuator):
    DEVICE_ID       = "heater_01"
    DEVICE_TYPE     = "urn:babymonitor:device:Heater:1"
    DEVICE_LOCATION = "http://192.168.1.10:8080/description.xml"
    TOPIC_CMD       = "baby/actuator/heater/cmd"
    TOPIC_STATE     = "baby/actuator/heater/state"
    LABEL           = "heater"

if __name__ == "__main__":
    device = Heater()
    try:
        device.start()
    except KeyboardInterrupt:
        device.stop()