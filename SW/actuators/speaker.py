from shared.base_actuator import BaseActuator

class Speaker(BaseActuator):
    DEVICE_ID       = "speaker_01"
    DEVICE_TYPE     = "urn:babymonitor:device:Speaker:1"
    DEVICE_LOCATION = "http://192.168.1.10:8080/description.xml"

    TOPIC_CMD       = "baby/actuator/speaker/cmd"
    TOPIC_STATE     = "baby/actuator/speaker/state"

    LABEL = "speaker"

    def __init__(self):
        super().__init__()

    def _apply_command(self, command: str):
        self.state = command

        if command == "ON":
            # TODOO: PLAY WAV
            print("[SPEAKER] Playing sound")
           
        elif command == "OFF":
            print("[SPEAKER] Stopping sound")
          

if __name__ == "__main__":
    device = Speaker()

    try:
        device.start()

    except KeyboardInterrupt:
        device.stop()