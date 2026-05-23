from shared.base_actuator import BaseActuator

class Toy(BaseActuator):
    DEVICE_ID       = "toy_01"
    DEVICE_TYPE     = "urn:babymonitor:device:Toy:1"
    DEVICE_LOCATION = "http://192.168.1.10:8080/description.xml"
    TOPIC_CMD       = "baby/actuator/toy/cmd"
    TOPIC_STATE     = "baby/actuator/toy/state"
    LABEL           = "toy"

if __name__ == "__main__":
    device = Toy()
    try:
        device.start()
    except KeyboardInterrupt:
        device.stop()