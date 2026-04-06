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

### **SW-1.1**: Temperature threshold management (18°C < ``current_temp`` < 26°C, ``target_temp`` = 22°C)  
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
        - The logic engine continues monitoring temperature When the value of 22°C is reached, it publishes a ``COOLING_OFF`` command to ``baby/actuator/fan/cmd`` via MQTT  
            - Payload example: ``{"command": "COOLING_OFF"}``  
- **SW-1.1.3**: Automatic heating cycle  
    - **SW-1.1.3.1**: The system initiates heating when temperature drops below 18°C  
    - **ARCH**:  
        - Temperature values are queried from ``baby/sensor/temp``  
        - If temperature falls below 18°C, it publishes ``HEATER_ON`` to ``baby/actuator/heater/cmd``  
            - Payload example: ``{"command": "HEATER_ON"}``  
    - **SW-1.1.3.2**: The system maintains heating until target temperature (22°C) is reached  
    - **ARCH**:  
        - The logic engine continues monitoring temperature. When the value of 21°C is reached, it publishes a ``HEATER_OFF`` command to ``baby/actuator/heater/cmd`` via MQTT  
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
            - Payload example: ``{"type": "ERROR", "code": "SENSOR_OFFLINE"}``  
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
        - Payload example: `{"type": "WARNING", "code": "INVALID_TEMP"}`  

### **SW-1.5**: Granular notification system  
- **SW-1.5.1**: The system provides detailed alerts  
- **ARCH**:  
    - Notifications are routed depending on type and recipient:  
    - Notifications are published to `baby/parent/notifications`  
        - Payload examples:    
            ``{"type": "ALERT", "code": "TEMP_HIGH"}``    
            ``{"type": "ALERT", "code": "TEMP_LOW"}``    
            ``{"type": "ALERT", "code": "TEMP_STUCK"}``  

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
        - When a valid cry is detected, system publishes to ``baby/parent/notifications``  
            - Payload example: ``{"type": "ALERT", "code": "BABY_CRYING", "priority": "HIGH"}``  
    - **SW-2.2.2**: Notification throttling  
    - **SW-2.2.2.1**: Prevent notification spam  
    - **ARCH**:  
        - After sending a cry alert, a cooldown timer (e.g., 30 seconds) is activated  
        - During this period, new alerts are suppressed unless crying stops and reoccurs  

### **SW-2.3**: Automatic soothing response  
- **SW-2.3.1**: Trigger soothing mechanisms  
    - **SW-2.3.1.1**: Activate motor (rocking mechanism)  
    - **ARCH**:  
        - Logic engine publishes command to ``baby/actuator/motor/cmd``  
            - Payload example: ``{"command": "MOTOR_ON"}``  
    - **SW-2.3.1.2**: Play soothing sound/music  
    - **ARCH**:  
        - Logic engine publishes command to ``baby/actuator/speaker/cmd``  
            - Payload example: ``{"command": "MUSIC_ON"}``  
    - **SW-2.3.1.3**: Define soothing duration  
    - **ARCH**:  
        - Soothing actions run for a predefined duration (e.g., 2 minutes)  
        - After timeout, system publishes:  
            ``{"command": "MUSIC_OFF"}``  
            ``{"command": "MOTOR_OFF"}``  

### **SW-2.4**: False positive reduction  
- **SW-2.4.1**: Avoid triggering on environmental noise  
    - **SW-2.4.1.1**: Noise filtering  
    - **ARCH**:  
        - Ignore signals outside expected frequency range (e.g., <300 Hz or >600 Hz)  
    - **SW-2.4.1.2**: Multi-condition validation  
    - **ARCH**:  
        - Cry detection requires:  
            - Amplitude threshold exceeded  
            - Frequency in valid range  
            - Persistence ≥ 3 seconds  
        - All conditions must be satisfied to trigger event  

### **SW-2.5**: Sensor failure and error handling  
- **SW-2.5.1**: Detect missing audio data  
    - **SW-2.5.1.1**: Audio stream watchdog  
    - **ARCH**:  
        - If no data is received on ``baby/sensor/audio`` within 30 seconds &rarr; publish to ``baby/alerts/system``  
            - Payload example: ``{"type": "ERROR", "code": "AUDIO_SENSOR_OFFLINE"}``  

### **SW-2.6**: Communication reliability  
- **SW-2.6.1**: Ensure delivery of critical alerts  
- **ARCH**:  
    - Use QoS levels:  
        - QoS 1 for:  
			`baby/parent/notifications`  
			`baby/alerts/system`  
        - QoS 0 for:  
			`baby/sensor/audio`  

### **SW-2.7**: System state management  
- **SW-2.7.1**: Prevent repeated triggering  
- **ARCH**:  
    - Logic engine maintains internal FSM:  
    - States:  
        `IDLE`  
        `CRY_DETECTED`  
        `SOOTHING`  
    - Rules:  
        - If state = `SOOTHING` &rarr; ignore new cry triggers  
        - Transition to `IDLE` after soothing completes  

## SW-3: Motorized Soothing System
Provide physical soothing through controlled motion  

### **SW-3.1**: Motor control  
- **SW-3.1.1**: Activate motor on demand or cry detection  
    - **SW-3.1.1.1**: Automatic activation (cry detection)  
    - **ARCH**:  
        - Upon receiving CRY_DETECTED event from audio module, logic engine publishes command to ``baby/actuator/motor/cmd``  
            - Payload example: ``{"command": "MOTOR_ON", "source": "AUTO"}``  
    - **SW-3.1.1.2**: Manual activation (parent control)  
    - **ARCH**:  
        - Parent application publishes command to ``baby/control/motor``  
            - Payload example: ``{"command": "MOTOR_ON", "duration": 300}``  
        - Logic engine subscribes to ``baby/control/motor`` and forwards validated commands to ``baby/actuator/motor/cmd``  
    - **SW-3.1.1.3**: Manual deactivation  
    - **ARCH**:  
        - Parent can stop motor at any time by publishing ``{"command": "MOTOR_OFF"}`` to ``baby/control/motor``  
- **SW-3.1.2**: Safe operation duration  
    - **SW-3.1.2.1**: Timed motor operation  
    - **ARCH**:  
        - When motor is activated, a ``Motor_Timer`` is started (default: 5 minutes)  
        - After timeout, logic engine publishes ``{"command": "MOTOR_OFF"}`` to ``baby/actuator/motor/cmd``  
    - **SW-3.1.2.2**: Configurable duration  
    - **ARCH**:  
        - If duration is provided via parent command, system overrides default timer  
        - Constraints:  
            - Minimum: 30 seconds  
            - Maximum: 10 minutes  
        - Invalid values are rejected  

### **SW-3.2**: Safety constraints  
- **SW-3.2.1**: Prevent continuous operation  
    - **SW-3.2.1.1**: Cooldown enforcement  
    - **ARCH**:  
        - After motor stops, a cooldown timer (e.g., 2 minutes) is activated  
        - During cooldown:  
            - All MOTOR_ON commands are ignored  
            - Warning can be published if command is attempted  
        - Payload example: ``{"type": "WARNING", "code": "MOTOR_COOLDOWN_ACTIVE"}``  
- **SW-3.2.2**: Limit excessive usage  
    - **SW-3.2.2.1**: Maximum activation frequency  
    - **ARCH**:  
        - System limits number of activations (e.g., max 5 cycles per hour)  
        - If exceeded &rarr; publish to ``baby/alerts/system``:  
            ``{"type": "ALERT", "code": "MOTOR_OVERUSE"}``  

### **SW-3.3**: State management  
- **SW-3.3.1**: Maintain motor state machine  
- **ARCH**:  
    - Logic engine maintains FSM:  
    - States:  
        `IDLE`  
        `RUNNING`  
        `COOLDOWN`  
    - Transitions:  
        - `IDLE` &rarr; `RUNNING` (on MOTOR_ON)  
        - `RUNNING` &rarr; `COOLDOWN` (after timer expires or MOTOR_OFF)  
        - `COOLDOWN` &rarr; `IDLE` (after cooldown timer)  
    - Rules:  
        - If state = `RUNNING` &rarr; ignore additional MOTOR_ON  
        - If state = `COOLDOWN` &rarr; block activation  

### **SW-3.4**: Feedback and monitoring  
- **SW-3.4.1**: Motor state reporting  
    - **SW-3.4.1.1**: Publish motor state  
    - **ARCH**:  
        - Motor device publishes status to ``baby/actuator/motor/state``  
            - Payload examples:  
                ``{"state": "RUNNING"}``  
                ``{"state": "IDLE"}``  
                ``{"state": "COOLDOWN"}``  
- **SW-3.4.2**: Failure detection  
    - **SW-3.4.2.1**: Detect motor malfunction  
    - **ARCH**:  
        - If MOTOR_ON command is issued but no state feedback is received within 5 seconds &rarr; publish error:  
            ``{"type": "ERROR", "code": "MOTOR_NO_RESPONSE"}``  

### **SW-3.5**: Data validation  
- **SW-3.5.1**: Validate incoming commands  
- **ARCH**:  
    - Commands received on ``baby/control/motor`` are validated:  
        - Allowed commands: MOTOR_ON, MOTOR_OFF  
        - Duration must be within valid bounds  
    - Invalid commands &rarr; discarded and reported:  
        ``{"type": "WARNING", "code": "INVALID_MOTOR_COMMAND"}``  

### **SW-3.6**: Communication reliability  
- **SW-3.6.1**: Ensure delivery of critical commands  
- **ARCH**:  
    - Use QoS levels:  
        - QoS 1 for:  
			`baby/actuator/motor/cmd`  
			`baby/alerts/system`  
        - QoS 0 for:  
			`baby/control/motor`  

## SW-4: Audio Playback System
Provide calming audio to assist infant sleep  

### **SW-4.1**: Music playback control  
- **SW-4.1.1**: Play music during soothing  
    - **SW-4.1.1.1**: Automatic playback activation  
    - **ARCH**:  
        - When motor enters RUNNING state (from Motorized Soothing System), logic engine publishes command to ``baby/actuator/speaker/cmd``  
            - Payload example: ``{"command": "MUSIC_ON", "source": "AUTO"}``  
    - **SW-4.1.1.2**: Manual playback control  
    - **ARCH**:  
        - Parent application can control playback via topic ``baby/control/speaker``  
            - Payload examples:  
                ``{"command": "MUSIC_ON"}``  
                ``{"command": "MUSIC_OFF"}``  
        - Logic engine validates and forwards commands to ``baby/actuator/speaker/cmd``  
- **SW-4.1.2**: Stop music when soothing ends  
    - **SW-4.1.2.1**: Automatic playback stop  
    - **ARCH**:  
        - When motor transitions to IDLE or COOLDOWN state, system publishes ``{"command": "MUSIC_OFF"}`` to ``baby/actuator/speaker/cmd``  
    - **SW-4.1.2.2**: Timeout-based stop  
    - **ARCH**:  
        - If music is playing independently (manual mode), a ``Music_Timer`` (e.g., 10 minutes) ensures automatic stop:  
            ``{"command": "MUSIC_OFF"}``  

### **SW-4.2**: Volume control  
- **SW-4.2.1**: Maintain safe audio levels  
    - **SW-4.2.1.1**: Enforce volume threshold  
    - **ARCH**:  
        - System limits volume to safe level (<50 dB equivalent)  
        - Any command exceeding threshold is automatically clamped to maximum allowed value  
    - **SW-4.2.1.2**: Volume adjustment via parent control  
    - **ARCH**:  
        - Parent can set volume via ``baby/control/speaker``  
            - Payload example: ``{"command": "SET_VOLUME", "value": 40}``  
        - Constraints:  
            - Minimum: 10 dB  
            - Maximum: 50 dB  
        - Invalid values are rejected  

### **SW-4.3**: Playback configuration  
- **SW-4.3.1**: Select audio content  
    - **SW-4.3.1.1**: Predefined audio tracks  
    - **ARCH**:  
        - System supports predefined tracks:  
            - lullaby_1  
            - white_noise  
            - nature_sounds  
        - Parent selects track via:  
            ``{"command": "SET_TRACK", "track": "lullaby_1"}``  
- **SW-4.3.2**: Loop playback  
    - **SW-4.3.2.1**: Continuous playback mode  
    - **ARCH**:  
        - If enabled, selected audio track loops until stop condition is triggered  

### **SW-4.4**: State management  
- **SW-4.4.1**: Maintain speaker state machine  
- **ARCH**:  
    - Logic engine maintains FSM:  
    - States:  
        `IDLE`  
        `PLAYING`  
        `PAUSED`  
    - Transitions:  
        - `IDLE` &rarr; `PLAYING` (on MUSIC_ON)  
        - `PLAYING` &rarr; `IDLE` (on MUSIC_OFF)  
        - `PLAYING` &rarr; `PAUSED` (optional)  
    - Rules:  
        - If state = `PLAYING` &rarr; ignore duplicate MUSIC_ON  
        - If state = `IDLE` &rarr; ignore MUSIC_OFF  

### **SW-4.5**: Feedback and monitoring  
- **SW-4.5.1**: Speaker state reporting  
    - **SW-4.5.1.1**: Publish playback status  
    - **ARCH**:  
        - Speaker publishes state to ``baby/actuator/speaker/state``  
            - Payload examples:  
                ``{"state": "PLAYING", "track": "lullaby_1"}``  
                ``{"state": "IDLE"}``  
- **SW-4.5.2**: Failure detection  
    - **SW-4.5.2.1**: Detect playback failure  
    - **ARCH**:  
        - If MUSIC_ON is issued but no state feedback is received within 5 seconds &rarr; publish:  
            ``{"type": "ERROR", "code": "SPEAKER_NO_RESPONSE"}``  

### **SW-4.6**: Data validation  
- **SW-4.6.1**: Validate incoming commands  
- **ARCH**:  
    - Commands from ``baby/control/speaker`` are validated:  
        - Allowed commands: MUSIC_ON, MUSIC_OFF, SET_VOLUME, SET_TRACK  
        - Parameters must be within valid bounds  
    - Invalid commands &rarr; rejected and logged:  
        ``{"type": "WARNING", "code": "INVALID_SPEAKER_COMMAND"}``  

### **SW-4.7**: Communication reliability  
- **SW-4.7.1**: Ensure delivery of critical commands  
- **ARCH**:  
    - Use QoS levels:  
        - QoS 1 for:  
			`baby/actuator/speaker/cmd`  
			`baby/alerts/system`  
        - QoS 0 for:  
			`baby/control/speaker`  

## SW-5: Light Monitoring & Ambient Lighting Control
Maintain appropriate lighting conditions based on ambient light levels  

### **SW-5.1**: Light sensing  
- **SW-5.1.1**: Detect ambient light level  
    - **SW-5.1.1.1**: Continuous light monitoring  
    - **ARCH**:  
        - Light sensor (LDR_Sim) continuously measures ambient light and publishes data to ``baby/sensor/light``  
            - Payload example: ``{"value": 120, "unit": "lux"}``  
        - Logic engine subscribes to ``baby/sensor/#`` and processes incoming light data in real time  
    - **SW-5.1.1.2**: Data validation  
    - **ARCH**:  
        - Incoming light values are validated:  
            - Valid range: 0–1000 lux  
            - Invalid values &rarr; discarded  
        - On invalid input, publish warning ``{"type": "WARNING", "code": "INVALID_LIGHT_VALUE"}`` to ``baby/alerts/system``  

### **SW-5.2**: Night lighting control  
- **SW-5.2.1**: Turn on lamp in low light conditions  
    - **SW-5.2.1.1**: Night detection threshold  
    - **ARCH**:  
        - If light level falls below threshold (e.g., <100 lux), system detects NIGHT state and publishes ``{"command": "LIGHT_ON"}`` to ``baby/actuator/lamp/cmd``  
    - **SW-5.2.1.2**: Low-intensity lighting mode  
    - **ARCH**:  
        - Lamp operates at reduced intensity using PWM:  
            ``{"command": "SET_BRIGHTNESS", "value": 20}``  
        - (20% brightness for night mode)  
- **SW-5.2.2**: Avoid complete darkness  
    - **SW-5.2.2.1**: Minimum brightness enforcement  
    - **ARCH**:  
        - System ensures brightness never drops below minimum threshold (e.g., 10%) during NIGHT state  

### **SW-5.3**: Daylight adaptation  
- **SW-5.3.1**: Gradual light reduction at sunrise  
    - **SW-5.3.1.1**: Detect increasing light levels  
    - **ARCH**:  
        - If ambient light rises above threshold (e.g., >150 lux), system transitions to DAY state  
    - **SW-5.3.1.2**: Gradual lamp dimming  
    - **ARCH**:  
        - Brightness is gradually reduced using PWM steps (e.g., every 5 seconds decrease by 5%)  
    - **SW-5.3.1.3**: Turn off lamp in daylight  
    - **ARCH**:  
        - When brightness reaches 0%, publish ``{"command": "LIGHT_OFF"}`` to ``baby/actuator/lamp/cmd``  

### **SW-5.4**: Smooth transitions  
- **SW-5.4.1**: Avoid abrupt lighting changes  
    - **SW-5.4.1.1**: PWM ramp control  
    - **ARCH**:  
        - All brightness transitions (increase/decrease) are implemented gradually over time using PWM ramping (e.g., 1–2 seconds per step)  

### **SW-5.5**: Manual control  
- **SW-5.5.1**: Parent override  
    - **SW-5.5.1.1**: Manual ON/OFF control  
    - **ARCH**:  
        - Parent can control lamp via ``baby/control/lamp``  
            - Payload examples:  
                ``{"command": "LIGHT_ON"}``  
                ``{"command": "LIGHT_OFF"}``  
    - **SW-5.5.1.2**: Manual brightness adjustment  
    - **ARCH**:  
        - Parent can set brightness:  
            ``{"command": "SET_BRIGHTNESS", "value": 50}``  
        - Constraints:  
            - Minimum: 0%  
            - Maximum: 100%  

### **SW-5.6**: State management  
- **SW-5.6.1**: Maintain lighting state machine  
- **ARCH**:  
    - Logic engine maintains FSM:  
    - States:  
        `DAY`  
        `NIGHT`  
        `TRANSITION`  
    - Transitions:  
        - `DAY` &rarr; `NIGHT` (low light detected)  
        - `NIGHT` &rarr; `DAY` (high light detected)  
        - `TRANSITION` (during gradual changes)  
    - Rules:  
        - Prevent rapid toggling (hysteresis between thresholds, e.g., 100 lux vs 150 lux)  
        - Ignore redundant commands in same state  

### **SW-5.7**: Feedback and monitoring  
- **SW-5.7.1**: Lamp state reporting  
    - **SW-5.7.1.1**: Publish lamp status  
    - **ARCH**:  
        - Lamp publishes state to ``baby/actuator/lamp/state``  
            - Payload examples:  
                ``{"state": "ON", "brightness": 20}``  
                ``{"state": "OFF"}``  
                ``{"state": "TRANSITION"}``  
- **SW-5.7.2**: Failure detection  
    - **SW-5.7.2.1**: Detect lamp malfunction  
    - **ARCH**:  
        - If LIGHT_ON command is issued but no response is received within 5 seconds &rarr; publish:  
            ``{"type": "ERROR", "code": "LAMP_NO_RESPONSE"}``  

### **SW-5.8**: Communication reliability  
- **SW-5.8.1**: Ensure delivery of commands  
- **ARCH**:  
    - Use QoS levels:  
        - QoS 1 for:  
			`baby/actuator/lamp/cmd`  
			`baby/alerts/system`  
        - QoS 0 for:  
			`baby/sensor/light`  
			`baby/control/lamp`  

## SW-6: System Integration & Coordination
Ensure coordinated operation between all subsystems  

### **SW-6.1**: Event-based coordination  
- **SW-6.1.1**: Synchronize actuators  
    - **SW-6.1.1.1**: Cry response coordination  
    - **ARCH**:  
        - When CRY_DETECTED event received from audio module:  
            - Publish MOTOR_ON &rarr; ``baby/actuator/motor/cmd``  
            - Publish MUSIC_ON &rarr; ``baby/actuator/speaker/cmd``  
        - Payload examples:  
            ``{"command": "MOTOR_ON", "source": "AUTO"}``  
            ``{"command": "MUSIC_ON", "source": "AUTO"}``  
    - **SW-6.1.1.2**: Night lighting coordination  
    - **ARCH**:  
        - When NIGHT state detected (ambient light low):  
            - Publish LIGHT_ON &rarr; ``baby/actuator/lamp/cmd``  
            - Set brightness according to night mode  
    - **SW-6.1.1.3**: Temperature safety coordination  
    - **ARCH**:  
        - If TEMP_HIGH or TEMP_LOW event triggers heating/cooling &rarr;  
            - Block simultaneous motor soothing if safety rules require  
            - Publish relevant parent notifications  

### **SW-6.2**: Central logic engine  
- **SW-6.2.1**: Unified decision-making  
    - **SW-6.2.1.1**: Subscribe to all sensor topics  
    - **ARCH**:  
        - Logic engine subscribes to:  
            - ``baby/sensor/temp``  
            - ``baby/sensor/audio``  
            - ``baby/sensor/light``  
            - other relevant sensors  
        - It continuously monitors all events in real-time  
    - **SW-6.2.1.2**: Publish coordinated actuator commands  
    - **ARCH**:  
        - Based on event rules, publishes commands to:  
            - ``baby/actuator/motor/cmd``  
            - ``baby/actuator/speaker/cmd``  
            - ``baby/actuator/lamp/cmd``  
            - ``baby/actuator/heater/cmd`` / ``baby/actuator/fan/cmd``  
        - All commands are validated and rate-limited as needed  
- **SW-6.2.2**: Conflict detection  
- **ARCH**:  
    - Logic engine detects conflicting commands (e.g., heating + cooling, motor during safety lock) and resolves according to priority rules  
    - If conflict cannot be resolved &rarr; publish alert:  
        ``{"type": "ERROR", "code": "CONFLICT_DETECTED"}``  

### **SW-6.3**: Priority handling  
- **SW-6.3.1**: Event prioritization  
    - **SW-6.3.1.1**: Priority order definition  
    - **ARCH**:  
        - Events are handled in order of importance:  
            1. Safety &rarr; temperature extremes, sensor failures  
            2. Cry detection &rarr; soothing actions (motor + music)  
            3. Comfort &rarr; lighting adjustments, optional music  
        - Logic engine ensures higher-priority events preempt lower-priority ones  
- **SW-6.3.2**: Emergency preemption  
    - **SW-6.3.2.1**: Interrupt ongoing actions if safety is triggered  
    - **ARCH**:  
        - If a safety-critical event occurs while comfort/soothing actions are active:  
            - Immediately stop conflicting actuators (e.g., MOTOR_OFF, MUSIC_OFF)  
            - Activate safety actuators (HEATER_ON / FAN_ON)  
            - Publish alert to ``baby/parent/notifications``  

### **SW-6.4**: Monitoring and logging  
- **SW-6.4.1**: System-wide event logging  
- **ARCH**:  
    - All sensor readings, actuator commands, and detected conflicts are logged to a central store for monitoring and debugging  
- **SW-6.4.2**: Feedback reporting  
- **ARCH**:  
    - Current state of all actuators published periodically:  
        - ``baby/actuator/motor/state``  
        - ``baby/actuator/speaker/state``  
        - ``baby/actuator/lamp/state``  
        - ``baby/actuator/fan/state``  
        - ``baby/actuator/heater/state``  
