from datetime import datetime
import time
import json
import threading
import paho.mqtt.client as mqtt
from shared.mqtt_module import MQTTModule
from shared.ssdp_module import SSDPModule

MAX_AGE                      = 30       # in full implementation all devices should get their max_age, this is done for simplicity
STATUS_REPORT_INTERVAL_TICKS = 6        # 6 × 5s = 30s between status reports
UNAUTHORIZED_ALERT_THRESHOLD = 3        # number of attempts before sending an alert

ALL_TOPICS = "baby/#"

# Device types
TOPIC_TEMP_TYPE       = "urn:babymonitor:device:TemperatureSensor:1"
TOPIC_LIGHT_TYPE      = "urn:babymonitor:device:LightSensor:1"
TOPIC_MIC_TYPE        = "urn:babymonitor:device:Microphone:1"
TOPIC_FAN_TYPE        = "urn:babymonitor:device:Fan:1"
TOPIC_HEATER_TYPE     = "urn:babymonitor:device:Heater:1"
TOPIC_SPEAKER_TYPE    = "urn:babymonitor:device:Speaker:1"
TOPIC_LAMP_TYPE       = "urn:babymonitor:device:Lamp:1"
TOPIC_TOY_TYPE      = "urn:babymonitor:device:Toy:1"
TOPIC_PARENT_TYPE     = "urn:babymonitor:device:Parent:1"

# Subscribes to
TOPIC_MICROPHONE      = "baby/sensor/microphone"
TOPIC_LIGHT           = "baby/sensor/light"
TOPIC_TEMPERATURE     = "baby/sensor/temperature"
TOPIC_PARENT_CONTROL  = "baby/parent/control"
TOPIC_FAN_STATE       = "baby/actuator/fan/state"
TOPIC_HEATER_STATE    = "baby/actuator/heater/state"
TOPIC_TOY_STATE       = "baby/actuator/toy/state"
TOPIC_SPEAKER_STATE   = "baby/actuator/speaker/state"
TOPIC_LAMP_STATE      = "baby/actuator/lamp/state"
TOPIC_PARENT_STATE    = "baby/parent/control/state"

# Publishes to
TOPIC_FAN_CMD         = "baby/actuator/fan/cmd"
TOPIC_HEATER_CMD      = "baby/actuator/heater/cmd"
TOPIC_TOY_CMD         = "baby/actuator/toy/cmd"
TOPIC_SPEAKER_CMD     = "baby/actuator/speaker/cmd"
TOPIC_LAMP_CMD        = "baby/actuator/lamp/cmd"

TOPIC_PARENT_NOTIF    = "baby/parent/notifications"
TOPIC_PARENT_ALERT    = "baby/parent/alerts"

# ---------------------------------#
#              CONFIG              #
# ---------------------------------#
DEVICE_ID           = "controller"
PUBLISH_INTERVAL    = 10                                   # seconds between readings in normal operation
DEVICE_TYPE         = "urn:babymonitor:controller:1"
DEVICE_LOCATION     = "http://localhost/description.xml"   # placeholder

ALLOWED_DEVICE_TYPES = (
    TOPIC_FAN_TYPE,
    TOPIC_HEATER_TYPE,
    TOPIC_TOY_TYPE,
    TOPIC_SPEAKER_TYPE,
    TOPIC_LAMP_TYPE,
    TOPIC_LIGHT_TYPE,
    TOPIC_MIC_TYPE,
    TOPIC_TEMP_TYPE,
    TOPIC_PARENT_TYPE,
    "urn:babymonitor:controller:1"
)

class Controller:

    def __init__(self):
        self.usn = f"uuid:{DEVICE_ID}::{DEVICE_TYPE}"

        self.device_status         = {}                 # usn -> "online" | "offline" | "unavailable"
        self.last_seen             = {}                 # usn -> datetime
        self.unauthorized_attempts = {}                 # nt  -> attempt count
        self.last_commands         = {}                 # topic -> last cmd
        self.lock                  = threading.Lock()

        # MQTT client
        self.mqtt = MQTTModule(
            device_id = DEVICE_ID,
            subscriptions = [
                TOPIC_MICROPHONE,
                TOPIC_LIGHT,
                TOPIC_PARENT_CONTROL,
                TOPIC_TEMPERATURE,
                TOPIC_FAN_STATE,
                TOPIC_HEATER_STATE,
                TOPIC_TOY_STATE,
                TOPIC_SPEAKER_STATE,
                TOPIC_LAMP_STATE,
                TOPIC_PARENT_STATE
            ]
        )

        self.mqtt.client.on_message = self._on_message

        # TODOO: DEFINE ALL NEEDED HANDLERS
        self.handlers = {
            TOPIC_MICROPHONE :      self._handle_microphone,
            TOPIC_TEMPERATURE:      self._handle_temperature,
            TOPIC_LIGHT :           self._handle_light,
            TOPIC_PARENT_CONTROL :  self._handle_parent
        }

        # SSDP
        self.ssdp = SSDPModule(
            device_id   = DEVICE_ID,
            device_type = DEVICE_TYPE,
            location    = DEVICE_LOCATION
        )
        self.ssdp._handle_ssdp_message = self._handle_ssdp_message

        self.parent_override = False
        self.current_temp = None
        self.fan_state = "OFF"
        self.heater_state = "OFF"
        self.toy_state = "OFF"
        self.speaker_state = "OFF"
        self.lamp_state = "OFF"
        self.lamp_brightness = 0
        self.last_notification = None
        self.baby_was_crying = False

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())

            usn = payload.get("usn")
            if not usn:
                return  # Ignore broken messages
            topic = msg.topic

            # Ignore messages from unknown devices
            with self.lock:
                if self.device_status.get(usn) != "online":
                    print(f"[MQTT] Ignored message from non-online device: {usn}")
                    return
                
                self.last_seen[usn] = datetime.now()

            print(f"[MQTT] {usn} -> {payload}")

            handler = self.handlers.get(topic)
            if handler:
                handler(payload)
            else:
                print(f"[MQTT] No handler for topic: {topic}")

        except Exception as e:
            print("Error:", e)

    # Helper function used as FSM -  don't send command if it's the same as the last one
    def _publish_if_changed(self, topic, cmd):
        key = topic

        if self.last_commands.get(key) == cmd:
            return  

        self.last_commands[key] = cmd

        self.mqtt.publish(
            topic,
            {
                "usn": self.usn,
                "device_id": DEVICE_ID,
                "cmd": cmd,
                "timestamp": datetime.now().isoformat()
            }
        )

    def _publish_parent_state(self):
        self.mqtt.publish(
            TOPIC_PARENT_STATE,
            {
                "usn": self.usn,
                "temperature": self.current_temp,
                "fan": self.fan_state,
                "heater": self.heater_state,
                "toy": self.toy_state,
                "music": self.speaker_state,
                "lamp": self.lamp_state,
                "brightness": self.lamp_brightness,
                "parent_override": self.parent_override,
                "timestamp": datetime.now().isoformat()
            }
        )

    def _publish_notification(self, message):
        if self.last_notification == message:
            return

        self.last_notification = message
        self.mqtt.publish(TOPIC_PARENT_NOTIF, message)

    def _handle_microphone(self, payload):
        sound = payload.get("sound")

        if self.parent_override:
            print("[MIC] Parent override active")
            self._publish_parent_state()
            return
        
        if sound == "BabyCry":
            self.speaker_state = "ON"
            self.toy_state = "ON"
            print("[ACTION] Cry detected -> ON speaker + toy")

            self._publish_if_changed(TOPIC_SPEAKER_CMD, "ON")
            self._publish_if_changed(TOPIC_TOY_CMD, "ON")

            if not self.baby_was_crying:
                self._publish_notification("Baby is crying!")
                self.baby_was_crying = True

        else:
            self.speaker_state = "OFF"
            self.toy_state = "OFF"
            print("[ACTION] No cry -> OFF speaker + toy")

            self._publish_if_changed(TOPIC_SPEAKER_CMD, "OFF")
            self._publish_if_changed(TOPIC_TOY_CMD, "OFF")
            
            if self.baby_was_crying:
                self._publish_notification("Baby stopped crying.")
                self.baby_was_crying = False

        self._publish_parent_state()

    def _handle_temperature(self, payload):        
        current_temp = payload.get("temperature")

        self.current_temp = current_temp
        if self.parent_override:
            print("[TEMP] Parent override active")
            self._publish_parent_state()
            return  
        
        print(f"[DEBUG] Current temp: {current_temp}")
        if current_temp >= 30:
            self._publish_notification("Temperature too high!")
        elif current_temp <= 15:
            self._publish_notification("Temperature too low!")

        if current_temp <= 18:
            self.heater_state = "ON"
            self.fan_state = "OFF"
            print("[ACTION] Low room temperature detected -> ON heater")
            self._publish_if_changed(TOPIC_HEATER_CMD, "ON")
            self._publish_if_changed(TOPIC_FAN_CMD, "OFF")
        elif current_temp >= 26:
            self.heater_state = "OFF"
            self.fan_state = "ON"
            print("[ACTION] High room temperature detected -> ON fan")
            self._publish_if_changed(TOPIC_HEATER_CMD, "OFF")
            self._publish_if_changed(TOPIC_FAN_CMD, "ON")
        else:
            if current_temp >= 21 and current_temp <= 23:
                self.heater_state = "OFF"
                self.fan_state = "OFF"
                print("[ACTION] Target room temperature reached -> OFF fan, OFF heater")
                self._publish_if_changed(TOPIC_HEATER_CMD, "OFF")
                self._publish_if_changed(TOPIC_FAN_CMD, "OFF")

    def _handle_light(self, payload):
        light = payload.get("light")

        if self.parent_override:
            print("[LIGHT] Parent override active")
            self._publish_parent_state()
            return

        if light < 0:
            light = 0
        if light > 900:
            light = 900

        brightness = int((900 - light) / 10)
        if brightness < 0:
            brightness = 0
        if brightness > 100:
            brightness = 100

        self.lamp_brightness = brightness
        self.lamp_state = "ON" if self.lamp_brightness > 0 else "OFF"
        if self.lamp_brightness >= 80:
            self._publish_notification("Night mode active, lamp is bright.")
        elif self.lamp_brightness == 0:
            self._publish_notification("Daylight detected, lamp is off.")

        print(f"[DEBUG] Current light: {light} lux")
        print(f"[ACTION] Set lamp brightness -> {self.lamp_brightness}%")

        self.mqtt.publish(
            TOPIC_LAMP_CMD,
            {
                "usn": self.usn,
                "device_id": DEVICE_ID,
                "cmd": "SET_BRIGHTNESS",
                "value": self.lamp_brightness,
                "timestamp": datetime.now().isoformat()
            }
        )

        self._publish_parent_state()

    def _handle_parent(self, payload):
        cmd = payload.get("cmd")
        value = payload.get("value")

        print(f"[PARENT] Command: {cmd}")

        if cmd == "AUTO" or cmd == "LAMP_AUTO":
            self.parent_override = False
            print("[PARENT] Auto mode enabled")
            self._publish_parent_state()
            return

        if cmd != "GET_TEMPERATURE":
            self.parent_override = True

        if cmd == "FAN_ON":
            self.fan_state = "ON"
            self.heater_state = "OFF"
            self._publish_if_changed(TOPIC_HEATER_CMD, "OFF")
            self._publish_if_changed(TOPIC_FAN_CMD, "ON")

        elif cmd == "FAN_OFF":
            self.fan_state = "OFF"
            self._publish_if_changed(TOPIC_FAN_CMD, "OFF")

        elif cmd == "HEATER_ON":
            self.heater_state = "ON"
            self.fan_state = "OFF"
            self._publish_if_changed(TOPIC_FAN_CMD, "OFF")
            self._publish_if_changed(TOPIC_HEATER_CMD, "ON")

        elif cmd == "HEATER_OFF":
            self.heater_state = "OFF"
            self._publish_if_changed(TOPIC_HEATER_CMD, "OFF")

        elif cmd == "GET_TEMPERATURE":
            self._publish_parent_state()

        elif cmd == "TOY_ON":
            self.toy_state = "ON"
            self._publish_if_changed(TOPIC_TOY_CMD, "ON")

        elif cmd == "TOY_OFF":
            self.toy_state = "OFF"
            self._publish_if_changed(TOPIC_TOY_CMD, "OFF")

        elif cmd == "MUSIC_ON":
            self.speaker_state = "ON"
            self._publish_if_changed(TOPIC_SPEAKER_CMD, "ON")

        elif cmd == "MUSIC_OFF":
            self.speaker_state = "OFF"
            self._publish_if_changed(TOPIC_SPEAKER_CMD, "OFF")

        elif cmd == "SET_LAMP_BRIGHTNESS":
            self.lamp_brightness = max(0, min(100, int(value)))
            self.lamp_state = "ON" if self.lamp_brightness > 0 else "OFF"

            self.mqtt.publish(
                TOPIC_LAMP_CMD,
                {
                    "usn": self.usn,
                    "device_id": DEVICE_ID,
                    "cmd": "SET_BRIGHTNESS",
                    "value": self.lamp_brightness,
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        self._publish_parent_state()

    # ------------------------------------------------------------------ #
    #  Status report                                                     #
    # ------------------------------------------------------------------ #
    def get_status_report(self) -> dict:
        """Returns a dict of all known devices grouped by status."""
        with self.lock:
            report = {"online": [], "offline": [], "unavailable": []}

            for usn, status in self.device_status.items():
                entry = {"usn": usn}

                if usn in self.last_seen:
                    entry["last_seen"] = self.last_seen[usn].strftime("%Y-%m-%d %H:%M:%S")

                report[status].append(entry)

            report["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            return report
        
    def _print_status_report(self):
        report = self.get_status_report()

        def print_group(label, devices):
            print(f"  {label} ({len(devices)}):")
            if devices:
                for e in devices:
                    print(f"    - {e['usn']}")
            else:
                print("    —")

        print("\n========== DEVICE STATUS REPORT ==========")
        print_group("Online",      report["online"])
        print_group("Offline",     report["offline"])
        print_group("Unavailable", report["unavailable"])
        print(f"  As of: {report['timestamp']}")
        print("==========================================\n")
        
    # ------------------------------------------------------------------ #
    #  Max age expiry check                                              #
    # ------------------------------------------------------------------ #
    def _check_expiry(self):
        cycle = 0
        while True:
            now = datetime.now()
            with self.lock:
                for usn, last in list(self.last_seen.items()):
                    elapsed = (now - last).total_seconds()
                    if elapsed > MAX_AGE and self.device_status.get(usn) == "online":
                        self.device_status[usn] = "unavailable"
                        print(f"[controller] Device went unavailable (MAX_AGE expired): {usn}")
                        device_name = usn.split("device:")[1].split(":")[0]
                        self.mqtt.publish(TOPIC_PARENT_ALERT, f"Device unavailable: {device_name}")
            cycle += 1
            if cycle % STATUS_REPORT_INTERVAL_TICKS == 0:
                self._print_status_report()
            time.sleep(5)

    # ------------------------------------------------------------------ #
    #  Access control                                                    #
    # ------------------------------------------------------------------ #
    def _handle_unauthorized(self, nt: str, usn: str, addr: tuple, msg_type: str):
        """
        Logs an unauthorized SSDP attempt and sends an MQTT alert
        once the attempt count reaches UNAUTHORIZED_ALERT_THRESHOLD.
        """
        with self.lock:
            self.unauthorized_attempts[nt] = self.unauthorized_attempts.get(nt, 0) + 1
            count = self.unauthorized_attempts[nt]

        print(f"[controller] WARNING: Unauthorized device ({msg_type}) ignored — "
              f"NT='{nt}' USN='{usn}' IP={addr[0]} (attempt #{count})")

        if count == UNAUTHORIZED_ALERT_THRESHOLD:
            alert = {
                "type":      "unauthorized_device",
                "nt":        nt,
                "usn":       usn,
                "ip":        addr[0],
                "attempts":  count,
                "timestamp": datetime.now().isoformat()
            }
            self.mqtt.publish(TOPIC_PARENT_ALERT, json.dumps(alert))
            print(f"[controller] ALERT sent: unauthorized device exceeded threshold — NT='{nt}'")

    # ------------------------------------------------------------------ #
    #  SSDP message handling                                             #
    # ------------------------------------------------------------------ #
    def _handle_ssdp_message(self, message: str, addr: tuple):
        nt  = self.ssdp._parse_header(message, "NT")
        usn = self.ssdp._parse_header(message, "USN")

        if "ssdp:alive" in message:
            if nt in ALLOWED_DEVICE_TYPES:
                with self.lock:
                    self.device_status[usn] = "online"
                    self.last_seen[usn]     = datetime.now()
                print(f"[controller] Authorized device online: {usn} at {addr[0]}")
            else:
                self._handle_unauthorized(nt, usn, addr, "alive")

        elif "ssdp:byebye" in message:
            if nt in ALLOWED_DEVICE_TYPES:
                with self.lock:
                    self.device_status[usn] = "offline"
                    self.last_seen.pop(usn, None)
                print(f"[controller] Authorized device offline: {usn} at {addr[0]}")
                device_name = usn.split("device:")[1].split(":")[0]
                self.mqtt.publish(TOPIC_PARENT_ALERT, f"Device offline: {device_name}")
            else:
                self._handle_unauthorized(nt, usn, addr, "byebye")

        elif "M-SEARCH" in message:
            pass  # ignore search requests from other devices

    # ------------------------------------------------------------------ #
    #  Start                                                               #
    # ------------------------------------------------------------------ #

    def start(self):
        print("[controller] Starting...")

        self.ssdp.start_listener()
        self.ssdp.search("ssdp:all")

        self.mqtt.connect()

        threading.Thread(target=self._check_expiry, daemon=True).start()

        while True:
            time.sleep(1)


if __name__ == "__main__":
    c = Controller()
    try:
        c.start()
    except KeyboardInterrupt:
        print("Stopping controller...")
