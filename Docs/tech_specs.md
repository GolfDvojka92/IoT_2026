# Smart Baby Monitoring Room
## HLR:
IoT implementation of a smart baby room designed for automatic parameter regulation and monitoring.
### MQTT Topic Structure Template
- Sensors publish -> ``baby/sensor/<type>``
- Logic engine subscribes -> ``baby/sensor/#``
- Actuator commands -> ``baby/actuator/<device>/cmd``
- Actuator state feedback -> ``baby/actuator/<device>/state``
- Parent notifications -> ``baby/parent/notifications``
- System alerts/errors -> ``baby/alerts/system``

## Environment & Microclimate Management
## SW-1: The system monitors and regulates ambient temperature to ensure infant safety and comfort.
- **SW-1.1**: Temperature threshold management (18°C > current_temp > 26°C, target_temp = 22°C)
    - **SW-1.1.1**: Automatic cooling cycle
        - **SW-1.1.1.1**: Initiate cooling when temperature exceeds 26°C
        - **ARCH**: Temperature sensor (DHT22_Sim) publishes data to ``baby/sensor/temp``.
            - Payload example: ``{"value": 27.3, "unit": "C"}``.
        The logic engine subscribes to ``baby/sensor/``. 
        When the value exceeds 26°C, it publishes a ``COOLING_ON`` command to ``baby/actuator/fan/cmd`` via MQTT.
            - Payload example: ``{"command": "COOLING_ON"}``.
=====

    - SW-1.1.1.2: Maintain cooling until target temperature (22°C) is reached
    - **ARCH**:
The logic engine continues monitoring temperature. When the value of 22°C is reached, it publishes a COOLING_OFF command to baby/actuator/fan/cmd via MQTT.

- Payload example: {"command": "COOLING_OFF"}.
