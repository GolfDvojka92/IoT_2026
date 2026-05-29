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
TOPIC_MOTOR_TYPE      = "urn:babymonitor:device:Toy:1"
TOPIC_PARENT_TYPE     = "urn:babymonitor:device:Parent:1"

# Subscribes to
TOPIC_MICROPHONE      = "baby/sensor/microphone"
TOPIC_LIGHT           = "baby/sensor/light"
TOPIC_TEMPERATURE     = "baby/sensor/temperature"
TOPIC_PARENT_CONTROL  = "baby/parent/control"
TOPIC_FAN_STATE       = "baby/actuator/fan/state"
TOPIC_HEATER_STATE    = "baby/actuator/heater/state"
TOPIC_MOTOR_STATE     = "baby/actuator/motor/state"
TOPIC_SPEAKER_STATE   = "baby/actuator/speaker/state"
TOPIC_LAMP_STATE      = "baby/actuator/lamp/state"
TOPIC_PARENT_STATE    = "baby/parent/control/state"

# Publishes to
TOPIC_FAN_CMD         = "baby/actuator/fan/cmd"
TOPIC_HEATER_CMD      = "baby/actuator/heater/cmd"
TOPIC_MOTOR_CMD       = "baby/actuator/motor/cmd"
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
    TOPIC_MOTOR_TYPE,
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
        self.device_status         = {}   # usn -> "online" | "offline" | "unavailable"
        self.last_seen             = {}   # usn -> datetime
        self.unauthorized_attempts = {}   # nt  -> attempt count
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
                TOPIC_MOTOR_STATE,
                TOPIC_SPEAKER_STATE,
                TOPIC_LAMP_STATE,
                TOPIC_PARENT_STATE
            ]
        )
        self.mqtt._on_message = self._on_message

        # SSDP
        self.ssdp = SSDPModule(
            device_id   = DEVICE_ID,
            device_type = DEVICE_TYPE,
            location    = DEVICE_LOCATION
        )
        self.ssdp._handle_ssdp_message = self._handle_ssdp_message

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())

            usn = payload.get("usn")
            if not usn:
                return  # Ignore broken messages

            # Ignore messages from unknown devices
            with self.lock:
                if self.device_status.get(usn) != "online":
                    print(f"[MQTT] Ignored message from non-online device: {usn}")
                    return
                
                self.last_seen[usn] = datetime.now()

            print(f"[MQTT] {usn} -> {payload}")

        except Exception as e:
            print("Error:", e)
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