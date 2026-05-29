import time
from shared.mqtt_module import MQTTModule
from shared.ssdp_module import SSDPModule

class BaseDevice:
    """
    Common base for all devices (sensors and actuators).

    Subclasses must define:
        DEVICE_ID       (str)  – unique device name
        DEVICE_TYPE     (str)  – SSDP device type
        DEVICE_LOCATION (str)  – SSDP location (placeholder)
        TOPIC_STATE     (str)  – topic for online/offline status

    Subclasses must implement:
        _on_start()     – logic executed after successful connection
                          (sensor: reading loop, actuator: idle loop)
    """

    DEVICE_ID       = NotImplemented
    DEVICE_TYPE     = NotImplemented
    DEVICE_LOCATION = NotImplemented

    def __init__(self, subscriptions: list[str] = []):
        self._running = False

        self.mqtt = MQTTModule(
            device_id     = self.DEVICE_ID,
            subscriptions = subscriptions
        )
        self.ssdp = SSDPModule(
            device_id   = self.DEVICE_ID,
            device_type = self.DEVICE_TYPE,
            location    = self.DEVICE_LOCATION
        )

        self.usn = f"uuid:{self.DEVICE_ID}::{self.DEVICE_TYPE}"

    # ------------------------------------------------ #
    #            Hook that subclasses override          #
    # ------------------------------------------------ #

    def _on_start(self):
        """Called after the device goes online. Must be implemented in subclass."""
        raise NotImplementedError

    # ------------------------------------------------ #
    #               Startup and shutdown               #
    # ------------------------------------------------ #

    def start(self):
        print(f"[{self.DEVICE_ID}] Starting up...")

        self.ssdp.start_listener()
        self.ssdp.start_advertiser()

        self.mqtt.connect()
        time.sleep(1)  # short delay to ensure connection is established

        self.mqtt.publish(
            topic   = self.TOPIC_STATE,
            payload = { "usn": self.usn, "device_id": self.DEVICE_ID, "status": "online" },
            retain  = True
        )

        self._running = True
        self._on_start()

    def stop(self):
        print(f"[{self.DEVICE_ID}] Shutting down...")
        self._running = False

        self.mqtt.publish(
            topic   = self.TOPIC_STATE,
            payload = { "usn": self.usn, "device_id": self.DEVICE_ID, "status": "offline" },
            retain  = True
        )

        time.sleep(0.5)
        self.ssdp.stop_bg_threads()
        self.ssdp.send_byebye()
        self.mqtt.disconnect()