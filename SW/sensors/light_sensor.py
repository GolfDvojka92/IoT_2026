import random
import time
import json
from shared.mqtt_module import MQTTModule
from shared.ssdp_module import SSDPModule

# Publishes to
TOPIC_READING   = "baby/sensor/light"         # periodic temperature readings
TOPIC_STATE     = "baby/sensor/light/state"   # our own online/offline status

# ---------------------------------#
#              CONFIG              #
# ---------------------------------#
DEVICE_ID        = "light_sensor_01"
PUBLISH_INTERVAL = 10                                           # seconds between readings in normal operation
DEVICE_TYPE      = "urn:babymonitor:device:LightSensor:1"
DEVICE_LOCATION  = "http://192.168.1.10:8080/description.xml"   # placeholder

class LightSensor:

    def __init__(self):
        # Set up MQTT
        self.mqtt = MQTTModule(
            device_id     = DEVICE_ID,
            subscriptions = []
        )

        # Set up SSDP — so the controller can discover us on the network
        self.ssdp = SSDPModule(
            device_id    = DEVICE_ID,
            device_type  = DEVICE_TYPE,
            location     = DEVICE_LOCATION
        )

        self._running = False

    # ---------------------------------#
    #       Startup and shutdown       #
    # ---------------------------------#
    def start(self):
        print(f"[{DEVICE_ID}] Starting up...")

        # NOTIFY the controller
        self.ssdp.advertise()

        # Connect to the MQTT broker
        self.mqtt.connect()
        time.sleep(1)  # brief pause to let the connection establish

        # Sets state to online (retained=True so late subscribers see it)
        self.mqtt.publish(
            topic   = TOPIC_STATE,
            payload = {"device_id": DEVICE_ID, "status": "online"},
            retain  = True
        )

        self._running = True
        self._reading_loop()

    def stop(self):
        print(f"[{DEVICE_ID}] Shutting down...")
        self._running = False

        # Set state to offline before disconnecting
        self.mqtt.publish(
            topic   = TOPIC_STATE,
            payload = {"device_id": DEVICE_ID, "status": "offline"},
            retain  = True
        )

        # Give the broker a moment to deliver the offline message
        time.sleep(0.5)

        self.ssdp.send_byebye()
        self.mqtt.disconnect()

    # ---------------------------------#
    #         Main reading loop        #
    # ---------------------------------#
    def _reading_loop(self):
        while self._running:
            light = self._read_light()
            self._publish_reading(light)
            time.sleep(PUBLISH_INTERVAL)

    # ---------------------------------#
    #      Sensor read (simulation)    #
    # ---------------------------------#
    def _read_light(self) -> float:
        # TODO: replace with actual sensor reading
        return random.randint(0, 1000) # placeholder

    # ---------------------------------#
    #            Publishing            #
    # ---------------------------------#
    def _publish_reading(self, light: float):
        payload = {
            "device_id":   DEVICE_ID,
            "light": light,
            "unit":        "lux",
            "timestamp":   time.time()
        }
        self.mqtt.publish(TOPIC_READING, payload)
        print(f"[{DEVICE_ID}] Published reading: {light}")


if __name__ == "__main__":
    sensor = LightSensor()
    try:
        sensor.start()
    except KeyboardInterrupt:
        sensor.stop()