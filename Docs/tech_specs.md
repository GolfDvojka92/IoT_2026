# Smart Baby Monitoring Room  
## HLR: IoT implementation of a smart baby room designed for automatic parameter regulation and monitoring  
### MQTT Topic Structure Template  
- Sensors publish &rarr; ``baby/sensor/<type>`` 
- Logic engine subscribes &rarr; ``baby/sensor/#`` 
- Actuator commands &rarr; ``baby/actuator/<device>/cmd`` 
- Actuator state feedback &rarr; ``baby/actuator/<device>/state`` 
- Parent control commands &rarr; ``baby/parent/control``  
- Parent state feedback &rarr; ``baby/parent/control/state`` 
- Parent notifications &rarr; ``baby/parent/notifications`` 
- Parent alerts &rarr; ``baby/parent/alerts`` 

## SW-0: Network Discovery & Device Registration

Enable automatic discovery, authorization, registration and availability tracking of IoT devices within the local network before operational communication is established.

### **SW-0.1**: Device advertisement

- **SW-0.1.1**: Automatic presence announcement
    - **SW-0.1.1.1**: Device startup advertisement
    - **ARCH**:
        - Upon startup, every sensor and actuator joins the SSDP multicast group.
        - Each device periodically broadcasts an SSDP `NOTIFY (ssdp:alive)` message.
        - Announcement includes:
            - unique device identifier (USN)
            - device type (NT)
            - location information
            - advertisement lifetime (`max-age`)
        - This allows automatic discovery of devices currently present on the network.

- **SW-0.1.2**: Periodic availability refresh
    - **SW-0.1.2.1**: Continuous presence advertisement
    - **ARCH**:
        - Devices periodically retransmit `NOTIFY (ssdp:alive)` messages.
        - Continuous advertisements refresh availability information maintained by the controller.
        - Missing advertisements may indicate device or network failure.

- **SW-0.1.3**: Departure announcement
    - **SW-0.1.3.1**: Device announces shutdown before disconnecting
    - **ARCH**:
        - Before leaving the network, the device multicasts `NOTIFY (ssdp:byebye)`.
        - This informs the controller that the device is no longer available.

### **SW-0.2**: Controller discovery procedure

- **SW-0.2.1**: Active device search
    - **SW-0.2.1.1**: Controller actively searches for available devices on the network
    - **ARCH**:
        - During startup, the controller multicasts an SSDP `M-SEARCH` request.
        - The search target is `ssdp:all`.
        - Devices matching the search criteria respond with discovery information.
        - The controller uses these responses to identify devices already present on the network before operational communication begins.

- **SW-0.2.2**: Passive discovery monitoring
    - **SW-0.2.2.1**: Controller continuously listens for SSDP announcements
    - **ARCH**:
        - Controller monitors SSDP multicast traffic.
        - Newly advertised devices are detected dynamically through `ssdp:alive` messages.
        - Device shutdown announcements are detected through `ssdp:byebye` messages.
        - This enables runtime discovery without requiring controller restart.

### **SW-0.3**: Device authorization and registration

- **SW-0.3.1**: Authorized device validation
    - **SW-0.3.1.1**: Verification of supported device types
    - **ARCH**:
        - The controller maintains a whitelist of supported device types.
        - Only devices whose SSDP `NT` field matches a supported device type are accepted.
        - Unsupported devices are ignored and not registered.

- **SW-0.3.2**: Registration of discovered devices
    - **SW-0.3.2.1**: Controller stores information about available devices
    - **ARCH**:
        - After discovery, the controller registers:
            - device identifier (USN)
            - device type (NT)
            - device availability state
            - last seen timestamp
        - Registered devices become available for system coordination and monitoring.

- **SW-0.3.3**: Unauthorized device detection
    - **SW-0.3.3.1**: Monitoring of unsupported devices
    - **ARCH**:
        - Unauthorized SSDP announcements are logged.
        - The controller maintains a counter of unauthorized discovery attempts.
        - Repeated unauthorized announcements trigger an alert event for the parent subsystem published to ``baby/parent/alerts``.

### **SW-0.4**: Dynamic availability management

- **SW-0.4.1**: Online state management
    - **SW-0.4.1.1**: Detection of active devices
    - **ARCH**:
        - Devices announced with `ssdp:alive` are marked as active (`ONLINE`).
        - The controller updates the corresponding last seen timestamp.

- **SW-0.4.2**: Offline state management
    - **SW-0.4.2.1**: Detection of graceful device departure
    - **ARCH**:
        - Devices announcing `ssdp:byebye` are marked as inactive (`OFFLINE`) and the controller publishes an alert to ``baby/parent/alerts``.

- **SW-0.4.3**: Unavailable device detection
    - **SW-0.4.3.1**: Detection of unexpected communication loss
    - **ARCH**:
        - The controller periodically checks the activity of registered devices.
        - If no valid SSDP or MQTT activity is received within the configured timeout period, the device is marked as `UNAVAILABLE` and the controller published an alert to ``baby/parent/alerts``.
        - This mechanism detects unexpected device failures and network disconnections.

### **SW-0.5**: Operational communication bootstrap

- **SW-0.5.1**: Transition to MQTT communication
    - **SW-0.5.1.1**: Establishment of operational communication channels
    - **ARCH**:
        - SSDP is used only for:
            - device discovery
            - authorization
            - registration
            - availability tracking
        - After successful discovery, devices establish operational communication using MQTT.
        - MQTT channels are used for:
            - sensor telemetry
            - actuator commands
            - state reporting
            - alerts and notifications
        - MQTT messages originating from devices that are not currently marked as `ONLINE` are ignored by the controller.


  
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
          
### **SW-1.2**: Parent notification system
- **SW-1.2.1**: Critical temperature alert
  - **SW-1.2.1.1**: The system notifies parents if unsafe temperatures are reached.
  - **ARCH**:
    - Temperature values above 30°C generate notification:
       `Temperature too high!`
    - Temperature values below 15°C generate notification:
       `Temperature too low!`
    - Notifications are published to:
       `baby/parent/notifications`
- **SW-1.2.2**: Communication reliability
  - **SW-1.2.2.1**: The system ensures delivery of critical alerts
  - **ARCH**:
    - Use QoS 1 for:
       `baby/parent/notifications`
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
    - In case of invalid input, a warning is published to topic ``baby/parent/notifications``  
        - Payload example: `{"type": "WARNING", "code": "INVALID_TEMP"}`
      
### **SW-1.5**: Granular notification system
- **SW-1.5.1**: The system provides detailed alerts
- **ARCH**:
  - Notifications are published to `baby/parent/notifications`
  - Notification examples:
     `Temperature too high!`
     `Temperature too low!`

## SW-2: Audio monitoring & Cry Detection
Detect infant crying using machine learning (trained CNN model) instead of only simple signal rules.

### SW-2.1: Cry detection system 
- **SW-2.1.1**: Audio acquisition
    - The system continuously monitors audio input from the microphone.
    - **ARCH**:
        - Microphone (MIC_Sim) captures raw audio waveform continuously.
        - Instead of analyzing only amplitude/frequency manually,
          audio is forwarded to the logic engine as a WAV-like signal.
        - Example internal flow:
            audio stream → windowing → feature extraction → ML model → prediction
- **SW-2.1.2**: Machine learning-based cry detection
    - **ARCH**:
        - The system uses a trained deep learning model (BabyCryCNN) to detect crying.
        - Model input:
            - Mel-spectrogram + MFCC features extracted from audio segment
        - Model output:
            - probability of "BabyCry" vs "Other"
        - Decision rule:
            If P(BabyCry) ≥ threshold (e.g. 0.5)
            → CRY_DETECTED event is triggered
              
### **SW-2.2**: Parent notification
- **SW-2.2.1**: Cry detection notification
  - **SW-2.2.1.1**: The system notifies parents when crying is detected.
  - **ARCH**:
    - When the ML model classifies audio as `BabyCry`, the controller publishes:
       `Baby is crying!`
    - Notifications are published to:
       `baby/parent/notifications`
- **SW-2.2.2**: Cry stop notification
  - **SW-2.2.2.1**: The system notifies parents when crying stops.
  - **ARCH**:
    - When the ML model no longer classifies audio as `BabyCry`, the controller publishes:
       `Baby stopped crying.`
    - Notifications are published to:
       `baby/parent/notifications`


### **SW-2.3**: Automatic soothing response
- **SW-2.3.1**: Trigger soothing mechanisms
  - **SW-2.3.1.1**: Activate toy
  - **ARCH**:
    - Logic engine publishes command to `baby/actuator/toy/cmd`
      - Payload example: `{"command": "TOY_ON"}`
  - **SW-2.3.1.2**: Play soothing sound/music
  - **ARCH**:
    - Logic engine publishes command to `baby/actuator/speaker/cmd`
      - Payload example: `{"command": "MUSIC_ON"}`
  - **SW-2.3.1.3**: Stop soothing mechanisms
  - **ARCH**:
    - When crying is no longer detected:
       `{"command": "TOY_OFF"}`
       `{"command": "MUSIC_OFF"}`   

### **SW-2.4**: Communication reliability  
- **SW-2.4.1**: Ensure delivery of critical alerts  
- **ARCH**:  
    - Use QoS levels:  
        - QoS 1 for:  
			`baby/parent/notifications`  
        - QoS 0 for:  
			`baby/sensor/audio`   

## SW-3: Toy Soothing System
Provide physical soothing through controlled motion  

### **SW-3.1**: Toy control
- **SW-3.1.1**: Activate toy on demand or cry detection
  - **SW-3.1.1.1**: Automatic activation (cry detection)
  - **ARCH**:
    - Upon receiving CRY_DETECTED event from audio module, logic engine publishes command to `baby/actuator/toy/cmd`
      - Payload example: `{"command": "TOY_ON", "source": "AUTO"}`
  - **SW-3.1.1.2**: Manual activation (parent control)
  - **ARCH**:
    - Parent application publishes command to `baby/parent/control`
      - Payload example: `{"cmd": "TOY_ON"}`
    - Logic engine subscribes to `baby/parent/control` and forwards validated commands to `baby/actuator/toy/cmd`
  - **SW-3.1.1.3**: Manual deactivation
  - **ARCH**:
    - Parent can stop toy at any time by publishing `{"cmd": "TOY_OFF"}` to `baby/parent/control`

### **SW-3.2**: Feedback and monitoring
- **SW-3.2.1**: Toy state reporting
  - **SW-3.2.1.1**: Publish toy state
  - **ARCH**:
    - Toy device publishes status to `baby/actuator/toy/state`
      - Payload examples:
         `{"state": "ON"}`
         `{"state": "OFF"}`

### **SW-3.3**: Data validation
- **SW-3.3.1**: Validate incoming commands
- **ARCH**:
  - Commands received on `baby/parent/control` are validated:
    - Allowed commands:
       `TOY_ON`
       `TOY_OFF`
  - Invalid commands are discarded

### **SW-3.4**: Communication reliability  
- **SW-3.4.1**: Ensure delivery of critical commands  
- **ARCH**:  
    - Use QoS levels:  
        - QoS 1 for:  
			`baby/actuator/toy/cmd`  
        - QoS 0 for:  
			`baby/parent/control`  

## SW-4: Audio Playback System
Provide calming audio to assist infant sleep  

### **SW-4.1**: Music playback control
- **SW-4.1.1**: Play music during soothing
  - **SW-4.1.1.1**: Automatic playback activation
  - **ARCH**:
    - When crying is detected, logic engine publishes command to `baby/actuator/speaker/cmd`
      - Payload example: `{"command": "MUSIC_ON", "source": "AUTO"}`
  - **SW-4.1.1.2**: Manual playback control
  - **ARCH**:
    - Parent application can control playback via topic `baby/parent/control`
      - Payload examples:
        `{"cmd": "MUSIC_ON"}`
        `{"cmd": "MUSIC_OFF"}`
    - Logic engine validates and forwards commands to `baby/actuator/speaker/cmd`
- **SW-4.1.2**: Stop music when soothing ends
  - **SW-4.1.2.1**: Automatic playback stop
  - **ARCH**:
    - When crying is no longer detected, system publishes:
      `{"command": "MUSIC_OFF"}`

### **SW-4.2**: Feedback and monitoring
- **SW-4.2.1**: Speaker state reporting
  - **SW-4.2.1.1**: Publish playback status
  - **ARCH**:
    - Speaker publishes state to `baby/actuator/speaker/state`
      - Payload examples:
        `{"state": "ON"}`
        `{"state": "OFF"}`

### **SW-4.3**: Data validation
- **SW-4.3.1**: Validate incoming commands
- **ARCH**:
  - Commands from `baby/parent/control` are validated:
    - Allowed commands:
       `MUSIC_ON`
       `MUSIC_OFF`
  - Invalid commands are discarded


### **SW-4.4**: Communication reliability  
- **SW-4.4.1**: Ensure delivery of critical commands  
- **ARCH**:  
    - Use QoS levels:  
        - QoS 1 for:  
			`baby/actuator/speaker/cmd`   
        - QoS 0 for:  
			`baby/parent/control`  

## SW-5: Light Monitoring & Ambient Lighting Control
Maintain appropriate lighting conditions based on ambient light levels  

### **SW-5.1**: Light sensing  
- **SW-5.1.1**: Detect ambient light level  
    - **SW-5.1.1.1**: Continuous light monitoring  
    - **ARCH**:  
        - Light sensor (LDR_Sim) continuously measures ambient light and publishes data to ``baby/sensor/light``  
        - Logic engine subscribes to ``baby/sensor/#`` and processes incoming light data in real time  
    - **SW-5.1.1.2**: Data validation  
    - **ARCH**:  
        - Incoming light values are validated:  
            - Valid range: 0–900 lux  
            - Invalid values &rarr; discarded  

### **SW-5.2**: Automatic brightness regulation
- **SW-5.2.1**: Adjust lamp brightness according to ambient light level
  - **SW-5.2.1.1**: Brightness calculation
  - **ARCH**:
    - Logic engine calculates lamp brightness based on measured lux value.
    - Lower ambient light results in higher lamp brightness.
    - Higher ambient light results in lower lamp brightness.
    - Brightness range:
      * 0% – 100%
  - **SW-5.2.1.2**: Automatic lamp control
  - **ARCH**:
    - If calculated brightness is greater than 0%, system publishes:
      `{"command": "LIGHT_ON"}`
    - If calculated brightness reaches 0%, system publishes:
      `{"command": "LIGHT_OFF"}`
  - **SW-5.2.1.3**: Brightness update
  - **ARCH**:
    - Logic engine publishes:
      `{"command": "SET_BRIGHTNESS", "value": brightness}`
    - Brightness is continuously updated according to sensor readings.

### **SW-5.3**: Smooth transitions
- **SW-5.3.1**: Avoid abrupt lighting changes
  - **SW-5.3.1.1**: Gradual brightness adjustment
  - **ARCH**:
    - Light sensor simulation changes lux values gradually.
    - Lamp brightness is updated incrementally to provide smooth lighting transitions.

### **SW-5.4**: Manual control
- **SW-5.4.1**: Parent override
  - **SW-5.4.1.1**: Manual ON/OFF control
  - **ARCH**:
    - Parent can control lamp via `baby/parent/control`
      - Payload examples:
        `{"cmd": "LIGHT_ON"}`
        `{"cmd": "LIGHT_OFF"}`
  - **SW-5.4.1.2**: Manual brightness adjustment
  - **ARCH**:
    - Parent can set brightness:
      `{"cmd": "SET_BRIGHTNESS", "value": 50}`
    - Constraints:
      - Minimum: 0%
      - Maximum: 100%
  - **SW-5.4.1.3**: Return to automatic mode
  - **ARCH**:
    - Parent can disable override mode by publishing:
      `{"cmd": "AUTO"}`
    - Automatic brightness regulation is then restored.  

### **SW-5.5**: Feedback and monitoring
- **SW-5.5.1**: Lamp state reporting
  - **SW-5.5.1.1**: Publish lamp status
  - **ARCH**:
    - Lamp publishes state to `baby/actuator/lamp/state`
      - Payload examples:
        `{"state": "ON", "brightness": 75}`
        `{"state": "OFF", "brightness": 0}`
- **SW-5.5.2**: Parent notifications
  - **SW-5.5.2.1**: Lighting status notifications
  - **ARCH**:
    - When brightness exceeds 80%, system publishes:
      `Night mode active, lamp is bright.`
    - When brightness reaches 0%, system publishes:
      `Daylight detected, lamp is off.`
    - Notifications are published to:
      `baby/parent/notifications`

### **SW-5.6**: Communication reliability  
- **SW-5.6.1**: Ensure delivery of commands  
- **ARCH**:  
    - Use QoS levels:  
        - QoS 1 for:  
			`baby/actuator/lamp/cmd`  
        - QoS 0 for:  
			`baby/sensor/light`  
			`baby/parent/control`  

## SW-6: System Integration & Coordination
Ensure coordinated operation between all subsystems  

### **SW-6.1**: Event-based coordination  
- **SW-6.1.1**: Synchronize actuators  
    - **SW-6.1.1.1**: Cry response coordination
	  - **ARCH**:
	    - When CRY_DETECTED event is received from audio module:
	      - Publish TOY_ON → `baby/actuator/toy/cmd`
	      - Publish MUSIC_ON → `baby/actuator/speaker/cmd`
	    - Payload examples:
	      `{"command": "TOY_ON", "source": "AUTO"}`
	      `{"command": "MUSIC_ON", "source": "AUTO"}` 
    - **SW-6.1.1.2**: Ambient lighting coordination
	  - **ARCH**:
	    - When new light sensor data is received:
	      - Calculate lamp brightness according to ambient light level
	      - Publish LIGHT_ON / LIGHT_OFF as required
	      - Publish SET_BRIGHTNESS command to lamp
    - **SW-6.1.1.3**: Temperature safety coordination  
    - **ARCH**:  
        - If TEMP_HIGH or TEMP_LOW event triggers heating/cooling &rarr;  
            - Coordinate temperature regulation and soothing actions
            - Publish relevant parent notifications  

### **SW-6.2**: Central logic engine  
- **SW-6.2.1**: Unified decision-making  
    - **SW-6.2.1.1**: Subscribe to all sensor topics  
    - **ARCH**:  
        - Logic engine subscribes to:  
             ``baby/sensor/temp``  
             ``baby/sensor/microphone``  
             ``baby/sensor/light``  
             other relevant sensors  
        - It continuously monitors all events in real-time  
    - **SW-6.2.1.2**: Publish coordinated actuator commands  
    - **ARCH**:  
        - Based on event rules, publishes commands to:  
             ``baby/actuator/toy/cmd``  
             ``baby/actuator/speaker/cmd``  
             ``baby/actuator/lamp/cmd``  
             ``baby/actuator/heater/cmd`` / ``baby/actuator/fan/cmd``  
        - All commands are validated and rate-limited as needed  

### **SW-6.3**: Priority handling  
- **SW-6.3.1**: Event prioritization  
    - **SW-6.3.1.1**: Priority order definition  
    - **ARCH**:  
        - Events are handled in order of importance:  
            1. Safety &rarr; temperature extremes, sensor failures  
            2. Cry detection &rarr; soothing actions (toy + music)  
            3. Comfort &rarr; lighting adjustments, optional music  
        - Logic engine ensures higher-priority events preempt lower-priority ones  

### **SW-6.4**: Monitoring and logging  
- **SW-6.4.1**: System-wide event logging
- **ARCH**:
  - Sensor readings, actuator commands and important system events are logged through controller and device console output for monitoring and debugging purposes.
- **SW-6.4.2**: Feedback reporting  
- **ARCH**:  
    - Current state of all actuators published periodically:  
         ``baby/actuator/toy/state``  
         ``baby/actuator/speaker/state``  
         ``baby/actuator/lamp/state``  
         ``baby/actuator/fan/state``  
         ``baby/actuator/heater/state``

## SW-7: Parent Monitoring Application
Provide remote monitoring and control of the Smart Baby Room system.

### **SW-7.1**: Parent interface
- **SW-7.1.1**: Mobile application
  - **SW-7.1.1.1**: Android-based parent interface
  - **ARCH**:
    - The system provides an Android application for monitoring and controlling the baby room.
    - The application communicates with the system through MQTT.

### **SW-7.2**: Temperature monitoring and control
- **SW-7.2.1**: Temperature status display
  - **SW-7.2.1.1**: Display current temperature and actuator states
  - **ARCH**:
    - The application displays:
      - current room temperature
      - heater state
      - fan state
- **SW-7.2.2**: Manual temperature control
  - **SW-7.2.2.1**: Parent override
  - **ARCH**:
    - Parent can manually activate:
      - HEATER_ON
      - FAN_ON
    - Commands are published to:
      - `baby/parent/control`

### **SW-7.3**: Toy and music control
- **SW-7.3.1**: Soothing device monitoring
  - **SW-7.3.1.1**: Display current toy and speaker state
  - **ARCH**:
    - The application displays:
      - toy state
      - music state
- **SW-7.3.2**: Manual control
  - **SW-7.3.2.1**: Parent override
  - **ARCH**:
    - Parent can manually activate or deactivate:
      - TOY_ON
      - TOY_OFF
      - MUSIC_ON
      - MUSIC_OFF
    - Commands are published to:
       `baby/parent/control`

### **SW-7.4**: Lighting control
- **SW-7.4.1**: Lighting status display
  - **SW-7.4.1.1**: Display lamp information
  - **ARCH**:
    - The application displays:
      - lamp state
      - current brightness value
- **SW-7.4.2**: Manual brightness adjustment
  - **SW-7.4.2.1**: Parent override
  - **ARCH**:
    - Parent can adjust brightness using a slider.
    - Brightness values range from:
      - 0% to 100%
    - Commands are published to:
       `baby/parent/control`

### **SW-7.5**: Automatic mode restoration
- **SW-7.5.1**: Return control to controller
  - **SW-7.5.1.1**: Disable parent override
  - **ARCH**:
    - Parent can restore automatic system behavior by sending:
       `AUTO`
    - The controller resumes autonomous decision making.

### **SW-7.6**: Notifications and alerts
- **SW-7.6.1**: Notification display
  - **SW-7.6.1.1**: Display informational messages
  - **ARCH**:
    - The application subscribes to:
       `baby/parent/notifications`
    - Payload example:
       `Baby is crying!`
    
- **SW-7.6.2**: Alert display
  - **SW-7.6.2.1**: Display critical events
  - **ARCH**:
    - The application subscribes to:
       `baby/parent/alerts`
    - Payload example:
       `TemperatureSensor went offline.`

