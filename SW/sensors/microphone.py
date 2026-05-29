import random
import librosa
import sounddevice as sd
import time
import os
import torch 
from shared.base_sensor import BaseSensor
from model.infer import load_model, predict_file

TOPIC_READING    = "baby/sensor/microphone"
TOPIC_STATE = "baby/sensor/microphone/state"

DEVICE_ID        = "microphone_01"
PUBLISH_INTERVAL = 10
DEVICE_TYPE      = "urn:babymonitor:device:Uknwon:1"
DEVICE_LOCATION  = "http://192.168.1.10:8080/description.xml"

CHECKPOINT       = "model/baby_cry_detector_model.pt"
AUDIO_DIR        = "model/dataset/validation"
CRY_THRESHHOLD   = 0.5

class Microphone(BaseSensor):

    DEVICE_ID        = DEVICE_ID
    DEVICE_TYPE      = DEVICE_TYPE
    DEVICE_LOCATION  = DEVICE_LOCATION
    TOPIC_READING    = TOPIC_READING
    PUBLISH_INTERVAL = PUBLISH_INTERVAL
    TOPIC_STATE      = TOPIC_STATE

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._model, self._ckpt = load_model(CHECKPOINT, self._device)
        self._n_frames = self._ckpt.get("n_frames", 44)
        self._wav_files = [
            os.path.join(AUDIO_DIR, f)
            for f in os.listdir(AUDIO_DIR) if f.endswith(".wav")
        ]

    def _read(self):
        if not self._wav_files:
            return "Other"
        
        _wav_path = random.choice(self._wav_files)
        
        result = predict_file(
            model = self._model,
            wav_path = _wav_path,
            device = self._device,
            n_frames = self._n_frames,
            threshold = CRY_THRESHHOLD
        )

        audio, sr = librosa.load(_wav_path, sr=None, mono=True)
        try:
            sd.play(audio, sr)
            sd.wait()
        finally:
            sd.stop()
        
        if not result or result.get("prediction") == "Uknown":
            return "Other"

        return result["prediction"]     # "BabyCry" or "Other"

    def _build_payload(self, value):
        return {
            "usn":       self.usn,   
            "device_id": self.DEVICE_ID,
            "sound":     value,
            "timestamp": time.time()
        }

if __name__ == "__main__":
    sensor = Microphone()
    try:
        sensor.start()
    except KeyboardInterrupt:
        sensor.stop()