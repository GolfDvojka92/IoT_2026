from datetime import datetime
from time import sleep
from shared.base_sensor import BaseSensor
import threading
import os

TOPIC_READING       = "baby/sensor/temperature"
TOPIC_STATE         = "baby/sensor/temperature/state"

DEVICE_ID           = "temperature_sensor_01"
PUBLISH_INTERVAL    = 10
DEVICE_TYPE         = "urn:babymonitor:device:TemperatureSensor:1"
DEVICE_LOCATION     = "http://192.168.1.10:8080/description.xml"

TOPIC_FAN_STATE     = "baby/actuator/fan/state"
TOPIC_HEATER_STATE     = "baby/actuator/heater/state"

class TemperatureSensor(BaseSensor):

    DEVICE_ID        = DEVICE_ID
    DEVICE_TYPE      = DEVICE_TYPE
    DEVICE_LOCATION  = DEVICE_LOCATION
    TOPIC_READING    = TOPIC_READING
    PUBLISH_INTERVAL = PUBLISH_INTERVAL
    TOPIC_STATE      = TOPIC_STATE

    def __init__(self):
        super().__init__()
        self.reading = 22.5
        self.states = {
            TOPIC_FAN_STATE: False,
            TOPIC_HEATER_STATE: False
        }
        self.mqtt.client.on_message = self._on_message

    def _start_temp_sim(self):
        # Starts a background thread that simulates the room cooling down or heating up from the fan or heater
        # Runs alongside the main reading loop without blocking it.
        thread = threading.Thread(target=self._temp_sim, daemon=True)
        thread.start()

    def _temp_sim(self):
        while True:
            if self.states[TOPIC_FAN_STATE]:
                self.reading = round(self.reading - 0.1, 1)
            elif self.states[TOPIC_HEATER_STATE]:
                self.reading = round(self.reading + 0.1, 1)
            sleep(0.4)

    def _start_test_input(self):
        # Starts a background thread that listens for typed commands during testing.
        # Runs alongside the main reading loop without blocking it.
        thread = threading.Thread(target=self._test_input_loop, daemon=True)
        thread.start()

    def _test_input_loop(self):
        print(f"[{DEVICE_ID}] Test mode active. Commands: 'set <value>', 'status', 'quit', 'fan <state>', 'heater <state>'")
        while self._running:
            try:
                command = input().strip()

                if command.startswith("set "):
                    try:
                        self.reading = float(command.split(" ")[1])
                        print(f"[{DEVICE_ID}] Reading set to {self.reading}°C")
                    except (IndexError, ValueError):
                        print(f"[{DEVICE_ID}] Usage: set <number>")
                elif command.startswith("fan "):
                    state = command.split(" ")[1]
                    if state in {"on", "off"}:
                        self.states[TOPIC_FAN_STATE] = state == "on"
                        if self.states[TOPIC_FAN_STATE]:
                            self.states[TOPIC_HEATER_STATE] = False
                        print(f"[{DEVICE_ID}] Simulating fan {state}")
                    else:
                        print(f"[{DEVICE_ID}] Usage: fan <state>")
                elif command.startswith("heater "):
                    state = command.split(" ")[1]
                    if state in {"on", "off"}:
                        self.states[TOPIC_HEATER_STATE] = state == "on"
                        if self.states[TOPIC_HEATER_STATE]:
                            self.states[TOPIC_FAN_STATE] = False
                        print(f"[{DEVICE_ID}] Simulating heater {state}")
                    else:
                        print(f"[{DEVICE_ID}] Usage: heater <state>")
                elif command == "status":
                    print(f"[{DEVICE_ID}] Current reading: {self.reading}")

                elif command == "quit":
                    self.stop()
                    os._exit(0)

            except EOFError:
                break
    
    def _read(self) -> float:
        return self.reading

    def _build_payload(self, value: float) -> dict:
        return {
            "usn":          self.usn,   
            "device_id":    self.DEVICE_ID,
            "temperature":  value,
            "unit":         "C",
            "timestamp":    datetime.now().isoformat()
        }

    # Daemons need to be started before the _on_start call
    def _on_start(self):
        self._start_temp_sim()
        self._start_test_input()
        self.mqtt.client.subscribe("baby/actuator/fan/state")
        self.mqtt.client.subscribe("baby/actuator/heater/state")
        return super()._on_start()

    def _on_message(self, client, userdata, msg):
        payload = msg.payload.decode("utf-8")
        topic = msg.topic
        if topic in {TOPIC_FAN_STATE, TOPIC_HEATER_STATE}:
            if "ON" in payload:
                self.states[topic] = True
            else:
                self.states[topic] = False

if __name__ == "__main__":
    sensor = TemperatureSensor()
    try:
        sensor.start()
    except KeyboardInterrupt:
        sensor.stop()
