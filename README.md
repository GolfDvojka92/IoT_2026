# IoT Simulation System Workflow


## Setup environment

```bash
make setup
source venv/bin/activate
```

This creates a virtual environment and installs all required dependencies including MQTT, audio processing libraries, dataset tools, and PyTorch (CPU version).

---

## MQTT Broker

Start broker:

```bash
make broker
```

Stop broker:

```bash
make stop-broker
```

Broker runs on port 1883 and must be active before starting sensors or actuators.

---

## Dataset download (for ML model training)

```bash
make download-dataset-train
make download-dataset-validation
make download-dataset-test
```

Downloads and prepares datasets inside the `model/` directory.

---

## Run individual components

Controller:

```bash
python3 controller.py
```

Parent controller:

```bash
python3 -m parent.parent
```

Sensors:

```bash
make sensor-temperature
make sensor-light
make sensor-microphone
```

Actuators:

```bash
make fan
make heater
make lamp
make speaker
make toy
```

---
## Run full system

```bash
make run-all
```

This launches:

* all actuators
* all sensors
* parent controller
* main controller

Each component opens in a separate gnome-terminal window. Execution order is:
actuators -> sensors -> parent -> controller (after short delay)

---

## Stop full system

```bash
make stop-all
```

This kills all running sensor, actuator, parent, and controller processes.

---

## Clean project

```bash
make clean
```

Removes Python cache files (**pycache**) from the project.

---

## Notes

* Designed for Linux systems using systemd and gnome-terminal
