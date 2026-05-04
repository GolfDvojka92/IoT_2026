import time
import json
import threading
import paho.mqtt.client as mqtt
from shared.ssdp_module import SSDPModule

# ---------------------------------#
#           MQTT CONFIG            #
# ---------------------------------#
BROKER = "localhost"
TOPICS = "baby/#"

class Controller:

    def __init__(self):
        self.devices = {}

        # MQTT client
        self.client = mqtt.Client(client_id="controller")

        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

        # SSDP
        self.ssdp = SSDPModule(
            device_id="controller",
            device_type="urn:babymonitor:controller:1",
            location="http://localhost/controller"
        )

    # ---------------- MQTT ----------------
    def start_mqtt(self):
        self.client.connect(BROKER, 1883, 60)
        self.client.loop_start()

    def on_connect(self, client, userdata, flags, rc):
        print("[CONTROLLER] MQTT connected")
        client.subscribe(TOPICS)

    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            print(f"[MQTT] {msg.topic} -> {payload}")

            # SIMPLE RULE ENGINE
            if msg.topic == "baby/sensor/microphone":
                if payload.get("sound") == "CRYING":
                    print("[DECISION] Baby crying -> turning ON fan")

                    # TEST COMMAND TO FAN
                    command = {
                        "state": "ON"
                    }

                    self.client.publish(
                        "baby/actuator/fan/cmd",
                        json.dumps(command)
                    )

                    print("[CONTROLLER] Sent FAN ON command")
        except Exception as e:
            print("Error:", e)

    # ---------------- SSDP ----------------
    def start_ssdp(self):
        self.ssdp.start_listener()
        self.ssdp.search("ssdp:all")

    # ---------------- RUN ----------------
    def run(self):
        print("[CONTROLLER] Starting...")

        self.start_ssdp()
        self.start_mqtt()

        while True:
            time.sleep(1)


if __name__ == "__main__":
    c = Controller()
    try:
        c.run()
    except KeyboardInterrupt:
        print("Stopping controller...")