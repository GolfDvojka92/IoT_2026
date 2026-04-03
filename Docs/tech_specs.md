# Smart Baby Monitoring Room
## HLR: IoT implementation of a smart baby room designed for automatic parameter regulation and monitoring
### MQTT Topic Structure Template
- Sensors publish -> ``baby/sensor/<type>``
- Logic engine subscribes -> ``baby/sensor/#``
- Actuator commands -> ``baby/actuator/<device>/cmd``
- Actuator state feedback -> ``baby/actuator/<device>/state``
- Parent notifications -> ``baby/parent/notifications``
- System alerts/errors -> ``baby/alerts/system``

## SW-1: Environment & Microclimate Management
The system monitors and regulates ambient temperature to ensure infant safety and comfort
- **SW-1.1**: Temperature threshold management (18°C > ``current_temp`` > 26°C, ``target_temp`` = 22°C)
    - **SW-1.1.1**: Automatic cooling cycle
        - **SW-1.1.1.1**: Initiate cooling when temperature exceeds 26°C
        - **ARCH**:
            - Temperature sensor (DHT22_Sim) publishes data to ``baby/sensor/temp``
                - Payload example: ``{"value": 273, "unit": "C"}``.
            - The logic engine subscribes to ``baby/sensor/`` 
            - When the value exceeds 26°C, it publishes a ``COOLING_ON`` command to ``baby/actuator/fan/cmd`` via MQTT
                - Payload example: ``{"command": "COOLING_ON"}``
        - **SW-1.1.1.2**: Maintain cooling until target temperature (22°C) is reached
        - **ARCH**:
            - The logic engine continues monitoring temperature When the value of 22°C is reached, it publishes a ``COOLING_OFF`` command to ``baby/actuator/fan/cmd`` via MQTT.
                - Payload example: ``{"command": "COOLING_OFF"}``
    - **SW-1.1.2**: Automatic heating cycle
        - **SW-1.1.2.1**: The system initiates heating when temperature drops below 18°C
        - **ARCH**:
            - Temperature values are consumed from ``baby/sensor/temp``
            - If temperature falls below 18°C, it publishes ``HEATER_ON`` to ``baby/actuator/heater/cmd``
                - Payload example: ``{"command": "HEATER_ON"}``
        - **SW-1.1.2.2**: Maintain heating until target temperature (22°C) is reached
        - **ARCH**:
            - The logic engine continues monitoring temperature. When the value of 21°C is reached, it publishes a ``HEATER_OFF`` command to ``baby/actuator/heater/cmd`` via MQTT.
                - Payload example: ``{"command": "HEATER_OFF"}``
- **SW-1.2**: Parent notification and error handling
    - **SW-1.2.1**: Critical temperature alert
        - **SW-1.2.1.1**: The system notifies parents if unsafe temperature persists
        - **ARCH**:
            - A ``Safety_Timer`` is started when either heating or cooling cycle is activated. If the target temperature is not reached within 10 minutes, the system publishes payload to ``baby/parent/notifications``
                - Payload example: `{"type": "ALERT", "code": "TEMP_STUCK", "priority": "HIGH"}`    
        - **SW-1.2.1.2**: Maintain cooling until target temperature (22°C) is reached
        - **ARCH**:
            - The logic engine continues monitoring temperature When the value of 22°C is reached, it publishes a ``COOLING_OFF`` command to ``baby/actuator/fan/cmd`` via MQTT.
                - Payload example: ``{"command": "COOLING_OFF"}``
    - **SW-1.2.2**: Automatic heating cycle
        - **SW-1.2.2.1**: The system initiates heating when temperature drops below 18°C
        - **ARCH**:
            - Temperature values are consumed from ``baby/sensor/temp``
            - If temperature falls below 18°C, it publishes ``HEATER_ON`` to ``baby/actuator/heater/cmd``
                - Payload example: ``{"command": "HEATER_ON"}``
        - **SW-1.2.2.2**: Maintain heating until target temperature (22°C) is reached
        - **ARCH**:
            - The logic engine continues monitoring temperature. When the value of 21°C is reached, it publishes a ``HEATER_OFF`` command to ``baby/actuator/heater/cmd`` via MQTT.
                - Payload example: ``{"command": "HEATER_OFF"}``
