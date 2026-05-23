from shared.base_actuator import BaseActuator

class Lamp(BaseActuator):
    DEVICE_ID       = "lamp_01"
    DEVICE_TYPE     = "urn:babymonitor:device:Lamp:1"
    DEVICE_LOCATION = "http://192.168.1.10:8080/description.xml"
    TOPIC_CMD       = "baby/actuator/lamp/cmd"
    TOPIC_STATE     = "baby/actuator/lamp/state"
    LABEL           = "lamp"

if __name__ == "__main__":
    device = Lamp()
    try:
        device.start()
    except KeyboardInterrupt:
        device.stop()