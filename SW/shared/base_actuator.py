import time
import json
from shared.base_device import BaseDevice


class BaseActuator(BaseDevice):
    """
    Base for all actuators.

    Subclasses must define:
        TOPIC_CMD      (str)        – topic for receiving commands
        VALID_COMMANDS (tuple/list) – allowed command values (default: ON/OFF)
        LABEL          (str)        – device name for log messages (e.g. "FAN")

    Subclasses may override:
        _apply_command(command) – physical action + state update
        _on_message(...)        – if payload has a more complex structure
    """

    TOPIC_CMD      = NotImplemented
    VALID_COMMANDS = ("ON", "OFF")
    LABEL          = "ACTUATOR"

    def __init__(self):
        super().__init__(subscriptions=[self.TOPIC_CMD])
        self.state = "OFF"
        self.mqtt._on_message = self._on_message

    # ------------------------------------------------ #
    #       Methods that subclasses may override        #
    # ------------------------------------------------ #
    def _apply_command(self, command: str):
        """Applies a command. Override for additional logic (e.g. GPIO)."""
        self.state = command

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            command = payload.get("state")
            print(f"[{self.LABEL}] Command received: {command}")

            if command in self.VALID_COMMANDS:
                self._apply_command(command)
                self.publish_state()

        except Exception as e:
            print(f"[{self.LABEL}] Error: {e}")

    # ------------------------------------------------ #
    #                 Publish state                    #
    # ------------------------------------------------ #

    def publish_state(self):
        payload = {
            "device_id": self.DEVICE_ID,
            "state":     self.state,
            "timestamp": time.time()
        }
        self.mqtt.publish(self.TOPIC_STATE, payload)
        print(f"[{self.LABEL}] State -> {self.state}")

    # ------------------------------------------------ #
    #                   Idle loop                      #
    # ------------------------------------------------ #

    def _on_start(self):
        while self._running:
            time.sleep(1)

    # ------------------------------------------------ #
    #            Actuator-specific stop override       #
    # ------------------------------------------------ #

    def stop(self):
        print(f"[{self.DEVICE_ID}] Stopping...")
        self._running = False

        self.mqtt.publish(
            self.TOPIC_STATE,
            {"device_id": self.DEVICE_ID, "state": "OFF", "status": "offline"},
            retain=True
        )

        time.sleep(0.5)
        self.ssdp.stop_bg_threads()
        self.ssdp.send_byebye()
        self.mqtt.disconnect()