# Smart Baby Monitoring Room
## HL REQ:
IoT implementation of a smart baby room designed for automatic parameter regulation and monitoring.
### MQTT Topic Structure Template
- Sensors publish -> ``baby/sensor/<type>``
- Logic engine subscribes -> ``baby/sensor/#``
- Actuator commands -> ``baby/actuator/<device>/cmd``
- Actuator state feedback -> ``baby/actuator/<device>/state``
- Parent notifications -> ``baby/parent/notifications``
- System alerts/errors -> ``baby/alerts/system``

## Environment & Microclimate Management
### REQ 1:
Monitor and regulate ambient temperature to ensure infant safety and comfort.
#### REQ 1.1: High-temperature threshold management (>26°C)
##### REQ 1.1.1: Automatic cooling cycle
###### REQ 1.1.1.1: Initiate cooling when temperature exceeds 26°C
###### SOL 1.1.1.1:
Temperature sensor (DHT22_Sim) publishes data to ``baby/sensor/temp``.

- Payload example: ``{"value": 27.3, "unit": "C"}``.

The logic engine subscribes to ``baby/sensor/#``. 
When the value exceeds 26°C, it publishes a ``COOLING_ON`` command to ``baby/actuator/fan/cmd`` via MQTT.

- Payload example: ``{"command": "COOLING_ON"}``.
###### REQ 1.1.1.2: Maintain cooling until target temperature (22°C) is reached
###### SOL 1.1.1.2:
SOL_1.1.1.2:
The logic engine continues monitoring temperature. When the value of 22°C is reached, it publishes a COOLING_OFF command to baby/actuator/fan/cmd via MQTT.

- Payload example: {"command": "COOLING_OFF"}.
