"""
PIPELINE OVERVIEW:

1. Loads TSV annotation files (metadata about audio segments)
2. Reads corresponding WAV audio files from dataset folders
3. Cuts audio into segments using onset/offset timestamps
4. Extracts features:
   - Mel spectrogram (frequency + time representation of sound)
   - MFCC (compact representation of audio characteristics)
5. Saves everything as NumPy arrays (.npz files) for ML training

Expected dataset structure:
dataset/train/
dataset/validation/
dataset/test/
development set/train.tsv
development set/validation.tsv
evaluation set/test.tsv
"""

# ── Standard libraries ────────────────────────────────────────────────────────
import os                      # used for file paths and checking file existence
import numpy as np             # used for numerical arrays and ML tensors
import pandas as pd            # used to read TSV annotation files (tables)
import librosa                 # main library for audio processing
import logging                 # used for printing progress and debugging info
from pathlib import Path       # modern way to handle file paths (not heavily used here)

# ── Logging setup ──────────────────────────────────────────────────────────────
# This defines how logs will look in the terminal
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ── AUDIO CONFIGURATION ────────────────────────────────────────────────────────
# Sampling rate = how many audio samples per second we keep
# Higher = more detail, but more computation
SAMPLE_RATE = 22050

# We force every audio sample to be around 1 second long
SEGMENT_DURATION = 1.0

# Number of Mel frequency bands (controls frequency resolution)
# Think of this as dividing sound into 64 frequency “bins”
N_MELS = 64

# Number of MFCC coefficients (compressed representation of sound)
# MFCC = compact "fingerprint" of sound that describes its tone and frequency pattern.
# Used to represent audio in a small number of meaningful features for ML models.
N_MFCC = 40

# Hop length = how far we move each step when analyzing audio
# Smaller = more detailed time resolution
HOP_LENGTH = 512

# FFT window size = how big each analysis window is in samples
# Controls frequency resolution of spectrogram
N_FFT = 1024

# ── DATASET SPLITS CONFIGURATION ──────────────────────────────────────────────
# Each split has:
# (TSV annotation file, folder with WAV audio files)
SPLITS = {
    "train":      ("development set/train.tsv",      "dataset/train"),
    "validation": ("development set/validation.tsv", "dataset/validation"),
    "test":       ("evaluation set/test.tsv",        "dataset/test"),
}

# ── LABEL ENCODING ─────────────────────────────────────────────────────────────
# Machine learning models cannot use text labels, so we convert them to numbers:
# BabyCry - 1 (positive class we want to detect)
# Other   - 0 (everything else)
LABEL_MAP = {"BabyCry": 1, "Other": 0}

# ── FEATURE EXTRACTION FUNCTION ───────────────────────────────────────────────
def extract_features(y: np.ndarray, sr: int) -> np.ndarray:
    """
    Converts raw audio signal into ML-ready numerical features.

    Input:
        y  → raw audio waveform (array of sound samples)
        sr → sampling rate

    Output:
        2D feature matrix of shape:
        (N_MELS + N_MFCC, time_frames)
    """

    # ── MEL SPECTROGRAM ───────────────────────────────────────────────────────
    # Converts audio into a "visual representation" of sound energy
    # Rows = frequencies, columns = time
    mel = librosa.feature.melspectrogram(
        y=y,
        sr=sr,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        n_mels=N_MELS
    )

    # Convert power values to decibels (log scale)
    # This makes values more similar to how humans perceive sound
    log_mel = librosa.power_to_db(mel, ref=np.max)

    # ── MFCC FEATURES ──────────────────────────────────────────────────────────
    # MFCC = compact summary of audio shape and tone
    # Often used in speech/audio classification tasks
    mfcc = librosa.feature.mfcc(
        y=y,
        sr=sr,
        n_mfcc=N_MFCC,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH
    )

    # ── COMBINE FEATURES ───────────────────────────────────────────────────────
    # We stack Mel spectrogram + MFCC vertically
    # Final shape = (64 + 40 = 104, time_frames)
    combined = np.concatenate([log_mel, mfcc], axis=0)

    return combined


# ── FIXING INPUT LENGTH ───────────────────────────────────────────────────────
def pad_or_trim(feat: np.ndarray, target_frames: int) -> np.ndarray:
    """
    Ensures all feature matrices have the same time dimension.

    Why?
    Machine learning models require fixed-size inputs.

    If too short → we add zeros (silence padding)
    If too long  → we cut extra frames (trim)
    """

    T = feat.shape[1]  # number of time frames in this sample

    # ── CASE 1: too short ─────────────────────────────────────────────────────
    if T < target_frames:
        # Create empty (silent) frames
        pad = np.zeros((feat.shape[0], target_frames - T), dtype=feat.dtype)

        # Append padding to original features
        feat = np.concatenate([feat, pad], axis=1)

    # ── CASE 2: too long ───────────────────────────────────────────────────────
    else:
        # Cut extra frames to match target size
        feat = feat[:, :target_frames]

    return feat


# ── PROCESS ONE DATA SPLIT ───────────────────────────────────────────────────
def process_split(tsv_path: str, audio_dir: str) -> tuple:
    """
    Processes one dataset split (train / validation / test).

    Steps:
    - Read annotation file (TSV)
    - Load audio files
    - Extract labeled segments
    - Convert audio → features
    - Return ML-ready dataset (X, y)
    """

    # Read TSV file into a table (DataFrame)
    df = pd.read_csv(tsv_path, sep="\t")

    # Remove useless column if it exists
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])

    # Compute how many time frames each sample should have
    target_frames = int(np.ceil(
        SEGMENT_DURATION * SAMPLE_RATE / HOP_LENGTH
    )) + 1

    # Lists to store results
    X_list = []  # feature matrices
    y_list = []  # labels

    # Counters for debugging
    missing = 0  # missing audio files
    errors = 0   # corrupted or failed samples

    # ── LOOP THROUGH EACH ROW IN TSV ─────────────────────────────────────────
    for _, row in df.iterrows():

        # Build full path to WAV file
        wav_path = os.path.join(audio_dir, row["filename"])

        # If file does not exist - skip it
        if not os.path.exists(wav_path):
            missing += 1
            continue

        # Convert text label - number (0 or 1)
        label = LABEL_MAP.get(row["event_label"])

        # Skip unknown labels
        if label is None:
            continue

        try:
            # Get start and end time of event in seconds
            onset = float(row["onset"])
            offset = float(row["offset"])

            # Ensure minimum segment length
            duration = max(offset - onset, SEGMENT_DURATION)

            # Load ONLY the required part of audio
            # librosa cuts audio starting from onset for given duration
            y_audio, _ = librosa.load(
                wav_path,
                sr=SAMPLE_RATE,
                offset=onset,
                duration=duration,
                mono=True
            )

            # Convert raw audio → features
            feat = extract_features(y_audio, SAMPLE_RATE)

            # Make all samples same size
            feat = pad_or_trim(feat, target_frames)

            # Store results
            X_list.append(feat)
            y_list.append(label)

        except Exception as exc:
            # If anything fails, skip sample but continue processing
            log.warning("Error processing %s: %s", wav_path, exc)
            errors += 1

    # ── DEBUG INFO ─────────────────────────────────────────────────────────────
    if missing:
        log.warning("%d WAV files not found in %s", missing, audio_dir)

    if errors:
        log.warning("%d segments skipped due to errors", errors)

    # Convert Python lists → NumPy arrays (ML format)
    X = np.stack(X_list).astype(np.float32) if X_list else np.empty((0,))
    y = np.array(y_list, dtype=np.int64)

    return X, y

# ── MAIN FUNCTION (RUNS EVERYTHING) ──────────────────────────────────────────
def main():

    # Loop over train / validation / test
    for split_name, (tsv_path, audio_dir) in SPLITS.items():

        log.info("Processing split: %s", split_name)

        # Check if annotation file exists
        if not os.path.exists(tsv_path):
            log.error("TSV file not found: %s", tsv_path)
            continue

        # Process dataset split → get features + labels
        X, y = process_split(tsv_path, audio_dir)

        # Print dataset statistics
        log.info(
            "Samples: %d | BabyCry: %d | Other: %d",
            len(y),
            int(y.sum()),
            int((y == 0).sum())
        )

        # Save output folder (same as audio folder)
        out_dir = audio_dir
        os.makedirs(out_dir, exist_ok=True)

        # Save compressed dataset file
        out_path = os.path.join(out_dir, "features.npz")
        np.savez_compressed(out_path, X=X, y=y)

        log.info("Saved: %s (shape X=%s)", out_path, X.shape)

    log.info("Preprocessing finished successfully.")


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    main()