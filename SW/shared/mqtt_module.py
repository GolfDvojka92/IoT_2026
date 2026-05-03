import paho.mqtt.client as mqtt
import json
import time

BROKER_HOST = "localhost"   # TODO: On real system should be set to the IP of the controller RPi
BROKER_PORT = 1883
KEEPALIVE   = 60

class MQTTModule:
    def __init__(self, device_id: str, subscriptions: list[str] = []):

        self.device_id     = device_id                          #   unique device name
        self.subscriptions = subscriptions                      #   list of MQTT topics device subscibes to
        self.client        = mqtt.Client(client_id=device_id)   #   MQTT client

        # MQTT callback wiring: paho.mqtt library has empty callback functions meant to be populated in implementation
        self.client.on_connect    = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message    = self._on_message

    # ------------------------------------------------ #
    #               Callback overrides                 #
    # ------------------------------------------------ #
    def _on_connect(self, client, userdata, flags, rc):         #   rc: return code, returns 0 when connection is successful, all other params are non-important
        if rc == 0:
            print(f"[{self.device_id}] Connected to broker")
            for topic in self.subscriptions:
                client.subscribe(topic)
                print(f"[{self.device_id}] Subscribed → {topic}")
        else:
            print(f"[{self.device_id}] Connection failed (rc={rc})")

    def _on_disconnect(self, client, userdata, rc):
        print(f"[{self.device_id}] Disconnected (rc={rc})")

    # Function to be overwritten in every device implementation for message handling
    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8")
        print(f"[{self.device_id}] Message on '{msg.topic}': {payload}")

    # ------------------------------------------------ #
    #                   Public API                     #
    # ------------------------------------------------ #
    def connect(self):
        self.client.connect(BROKER_HOST, BROKER_PORT, KEEPALIVE)
        self.client.loop_start()          # non-blocking background thread

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    # Publishes a dict as a JSON string to the given topic
    def publish(self, topic: str, payload: dict, qos: int = 1, retain: bool = False):
        message = json.dumps(payload)
        result  = self.client.publish(topic, message, qos=qos, retain=retain)
        print(f"[{self.device_id}] Published to '{topic}': {message}")
        return result
