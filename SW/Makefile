# =============================
# IoT Simulation Makefile
# =============================

VENV = venv
PY = $(VENV)/bin/python3

# =============================
# ENVIRONMENT SETUP 
# =============================
setup:
	python3 -m venv venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install paho-mqtt librosa pandas sounddevice tqdm yt-dlp
	$(PY) -m pip install torch --index-url https://download.pytorch.org/whl/cpu
	
# =============================
# MQTT BROKER
# =============================
broker:
	@echo "Using system Mosquitto broker (port 1883)"
	@echo "Start it with: sudo systemctl start mosquitto"
	
# =============================
# DATASET DOWNLOAD
# =============================
download-dataset-train:
	$(PY) model/download_audioset_baby_cry_dataset.py \
		--workspace model \
		--data_type train

download-dataset-validation:
	$(PY) model/download_audioset_baby_cry_dataset.py \
		--workspace model \
		--data_type validation

download-dataset-test:
	$(PY) model/download_audioset_baby_cry_dataset.py \
		--workspace model \
		--data_type test

# =============================
# CONTROLLER
# =============================
controller:
	$(PY) controller.py
	
# =============================
# PARENT CONTROLLER
# =============================
parent:
	$(PY) -m parent.parent


# =============================
# SENSORS
# =============================
sensor-temperature:
	$(PY) -m sensors.temperature_sensor

sensor-light:
	$(PY) -m sensors.light_sensor

sensor-microphone:
	$(PY) -m sensors.microphone

# =============================
# ACTUATORS
# =============================
fan:
	$(PY) -m actuators.fan

heater:
	$(PY) -m actuators.heater

lamp:
	$(PY) -m actuators.lamp

speaker:
	$(PY) -m actuators.speaker

toy:
	$(PY) -m actuators.toy

# =============================
# RUN COMPLETE SYSTEM
# =============================
run-all:
	@echo "Starting IoT simulation..."

	gnome-terminal -- bash -c "$(PY) -m actuators.fan; exec bash"
	gnome-terminal -- bash -c "$(PY) -m actuators.heater; exec bash"
	gnome-terminal -- bash -c "$(PY) -m actuators.lamp; exec bash"
	gnome-terminal -- bash -c "$(PY) -m actuators.speaker; exec bash"
	gnome-terminal -- bash -c "$(PY) -m actuators.toy; exec bash"

	gnome-terminal -- bash -c "$(PY) -m sensors.temperature_sensor; exec bash"
	gnome-terminal -- bash -c "$(PY) -m sensors.light_sensor; exec bash"
	gnome-terminal -- bash -c "$(PY) -m sensors.microphone; exec bash"

	gnome-terminal -- bash -c "$(PY) -m parent.parent; exec bash"

	sleep 3
	gnome-terminal -- bash -c "$(PY) controller.py; exec bash"

# =============================
# STOP COMPLETE SYSTEM 
# =============================
stop-all:
	@echo "Stopping all IoT processes..."
	# Kill all background execution scripts mapping modules or main scripts
	pkill -9 -f "sensors\." || true
	pkill -9 -f "actuators\." || true
	pkill -9 -f "parent\." || true
	pkill -9 -f "controller.py" || true
	@echo "All processes stopped."

# =============================
# CLEAN PROJECT
# =============================
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +