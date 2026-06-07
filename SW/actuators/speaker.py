from shared.base_actuator import BaseActuator
import os
import pygame

class Speaker(BaseActuator):
    DEVICE_ID       = "speaker_01"
    DEVICE_TYPE     = "urn:babymonitor:device:Speaker:1"
    DEVICE_LOCATION = "http://192.168.1.10:8080/description.xml"

    TOPIC_CMD       = "baby/actuator/speaker/cmd"
    TOPIC_STATE     = "baby/actuator/speaker/state"

    LABEL = "speaker"

    def __init__(self):
        super().__init__()

        pygame.mixer.init()

        self.music_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "music",
            "music-box.mp3"
        )

        self.is_playing = False

    def _apply_command(self, command: str):
        self.state = command

        if command == "ON":
            if not self.is_playing:
                print("[SPEAKER] Playing sound")

                pygame.mixer.music.load(self.music_path)
                pygame.mixer.music.play(-1)  # -1 = loop (background)

                self.is_playing = True

        elif command == "OFF":
            if self.is_playing:
                print("[SPEAKER] Stopping sound")

                pygame.mixer.music.stop()

                self.is_playing = False


if __name__ == "__main__":
    device = Speaker()

    try:
        device.start()
    except KeyboardInterrupt:
        device.stop()