# Smart Baby Monitoring Room  
## HLR: IoT implementation of a smart baby room designed for automatic parameter regulation and monitoring  
### MQTT Topic Structure Template  
- Sensors publish &rarr; ``baby/sensor/<type>``  
- Logic engine subscribes &rarr; ``baby/sensor/#``  
- Actuator commands &rarr; ``baby/actuator/<device>/cmd``  
- Actuator state feedback &rarr; ``baby/actuator/<device>/state``  
- Parent notifications &rarr; ``baby/parent/notifications``  
- System alerts/errors &rarr; ``baby/alerts/system``  
  
## SW-1: Environment & Microclimate Management  
The system monitors and regulates ambient temperature to ensure infant safety and comfort  

### **SW-1.1**: Temperature threshold management (18°C > ``current_temp`` > 26°C, ``target_temp`` = 22°C)  
- **SW-1.1.1**: Temperature monitoring  
    - **SW-1.1.1.1**: The system consistantly records and updates ``current_temp``  
    - **ARCH**:  
        - Temperature sensor (DHT22_Sim) publishes data to ``baby/sensor/temp``  
            - Payload example: ``{"value": 27.3, "unit": "C"}``  
- **SW-1.1.2**: Automatic cooling cycle  
    - **SW-1.1.2.1**: The system initiates cooling when temperature exceeds 26°C  
    - **ARCH**:  
        - The logic engine subscribes to ``baby/sensor/#``   
        - Temperature values are queried from ``baby/sensor/temp``  
        - When the value exceeds 26°C, it publishes a ``COOLING_ON`` command to ``baby/actuator/fan/cmd`` via MQTT  
            - Payload example: ``{"command": "COOLING_ON"}``  
    - **SW-1.1.2.2**: The system maintains cooling until target temperature (22°C) is reached  
    - **ARCH**:  
        - The logic engine continues monitoring temperature When the value of 22°C is reached, it publishes a ``COOLING_OFF`` command to ``baby/actuator/fan/cmd`` via MQTT.  
            - Payload example: ``{"command": "COOLING_OFF"}``  
- **SW-1.1.3**: Automatic heating cycle  
    - **SW-1.1.3.1**: The system initiates heating when temperature drops below 18°C  
    - **ARCH**:  
        - Temperature values are queried from ``baby/sensor/temp``  
        - If temperature falls below 18°C, it publishes ``HEATER_ON`` to ``baby/actuator/heater/cmd``  
            - Payload example: ``{"command": "HEATER_ON"}``  
    - **SW-1.1.3.2**: The system maintains heating until target temperature (22°C) is reached  
    - **ARCH**:  
        - The logic engine continues monitoring temperature. When the value of 21°C is reached, it publishes a ``HEATER_OFF`` command to ``baby/actuator/heater/cmd`` via MQTT.  
            - Payload example: ``{"command": "HEATER_OFF"}``  

### **SW-1.2**: Parent notification and error handling  
- **SW-1.2.1**: Critical temperature alert  
    - **SW-1.2.1.1**: The system notifies parents if unsafe temperature persists  
    - **ARCH**:  
        - A ``Safety_Timer`` is started when either heating or cooling cycle is activated. If the target temperature is not reached within 10 minutes, the system publishes payload to ``baby/parent/notifications``  
            - Payload example: `{"type": "ALERT", "code": "TEMP_STUCK", "priority": "HIGH"}`      
- **SW-1.2.2**: Sensor failure detection  
    - **SW-1.2.2.1**: The system detects missing sensor data  
    - **ARCH**:  
        - A watchdog timer monitors incoming messages on ``baby/sensor/temp``  
        - If no data is received within 30 seconds, the system publishes a payload on topic ``baby/alerts/system``  
            - Payload example: ``{"type": "ERROR", "code": "SENSOR_OFFLINE”}``  
- **SW-1.2.3**: Communication reliability  
    - **SW-1.2.3.1**: The system ensures delivery of critical alerts  
    - **ARCH**:  
        - Use QoS 1 for:  
			`baby/parent/notifications`  
			`baby/alerts/system`  
        - Use QoS 0 for:  
			`baby/sensor/#`  

### **SW-1.3**: Mutual exclusion of heating and cooling  
- **SW-1.3.1**: The system prevents simultaneous operation  
- **ARCH**:  
    - The logic engine maintains an internal FSM:  
    - States:  
        `IDLE`  
        `HEATING`  
        `COOLING`  
    - Rules:  
        - If state = `COOLING` &rarr; block `HEATER_ON` commands  
        - If state = `HEATING` &rarr; block `COOLING_ON` commands  

### **SW-1.4**: Sensor data validation  
- **SW-1.4.1**: The system rejects invalid readings  
- **ARCH**:  
    - Incoming data from topic ``baby/sensor/temp`` is validated against realistic bounds (0°C to 50°C)  
        - Valid values &rarr; processed normally  
        - Invalid values &rarr; discarded  
    - In case of invalid input, a warning is published to topic ``baby/alerts/system``  
        - Payload example: `{"type": "WARNING", "code": "INVALID_TEMP”}`  

### **SW-1.5**: Granular notification system  
- **SW-1.5.1**: The system provides detailed alerts  
- **ARCH**:  
    - Notifications are routed depending on type and recipient:  
    - Notifications are published to `baby/parent/notifications`  
        - Payload examples:    
            ``{"type": "ALERT", "code": "TEMP_HIGH”}``    
            ``{"type": "ALERT", "code": "TEMP_LOW”}``    
            ``{"type": "ALERT", "code": "TEMP_STUCK”}``  

## SW-2: Audio monitoring & Cry Detection
Detect infant crying and notify parents while enabling automatic soothing actions  

### **SW-2.1**: Cry detection system  
- **SW-2.1.1**: The system detects baby crying using microphone input  
    - **SW-2.1.1.1**: The system continuously monitors audio  
    - **ARCH**:  
        - Microphone (MIC_Sim) continuously captures audio and publishes data to topic baby/sensor/audio  
            - Payload example: ``{"amplitude": 0.78, "frequency": 450, "unit": "Hz"}``  
        - The logic engine subscribes to ``baby/sensor/#`` and processes incoming audio data in real time
    - **SW-2.1.1.2**: Cry pattern recognition  
    - **ARCH**:  
        - The logic engine applies basic DSP techniques:  
            - Amplitude thresholding  
            - Frequency range filtering (typical baby cry range ~300–600 Hz)  
            - Optional FFT analysis  
        - Simulation uses prerecorded audio files:  
            - crying.wav  
            - silence.wav  
        - If signal exceeds defined thresholds and matches crying pattern &rarr; CRY_DETECTED event is generated  
    - **SW-2.1.1.3**: Cry persistence validation  
    - **ARCH**:  
        - To avoid false triggers, crying must persist for a defined duration (e.g., 3 seconds)  
        - A `Cry_Timer` is started when threshold is exceeded:  
            - If signal remains above threshold for ≥ 3 seconds &rarr; valid cry event  
            - Otherwise → discard event  
### **SW-2.2**: Parent notification  
- **SW-2.2.1**: The system notifies parents when it detects crying  
    - **SW-2.2.1.1**: The system sends a high-priority alert  
    - **ARCH**:  
        - Microphone (MIC_Sim) continuously captures audio and publishes data to topic baby/sensor/audio  
            - Payload example: ``{"amplitude": 0.78, "frequency": 450, "unit": "Hz"}``  
