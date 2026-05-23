import time
from shared.base_device import BaseDevice


class BaseSensor(BaseDevice):
    """
    Base for all sensors.

    Subclasses must define:
        TOPIC_READING    (str) – topic where sensor readings are published
        PUBLISH_INTERVAL (int) – interval between readings in seconds

    Subclasses must implement:
        _read()               -> any  – reads the current sensor value
        _build_payload(value) -> dict – builds MQTT publish payload
    """

    TOPIC_READING    = NotImplemented
    PUBLISH_INTERVAL = 10

    def __init__(self):
        super().__init__(subscriptions=[])

    # ------------------------------------------------ #
    #         Methods that subclasses implement         #
    # ------------------------------------------------ #

    def _read(self):
        raise NotImplementedError

    def _build_payload(self, value) -> dict:
        raise NotImplementedError

    # ------------------------------------------------ #
    #                  Reading loop                    #
    # ------------------------------------------------ #

    def _on_start(self):
        while self._running:
            value = self._read()
            payload = self._build_payload(value)
            self.mqtt.publish(self.TOPIC_READING, payload)
            print(f"[{self.DEVICE_ID}] Published: {value}")
            time.sleep(self.PUBLISH_INTERVAL)