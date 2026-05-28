"""
Data preprocessing pipeline for baby cry detection model.
 
OVERVIEW OF THE PIPELINE:
=========================
This script:
1. Reads annotation files (TSV format) that describe when/where baby cries occur
2. Loads corresponding WAV audio files from disk
3. Extracts the relevant audio segments using timestamps
4. Converts audio waveforms into numerical features using signal processing
5. Saves features as NumPy arrays (.npz files) for fast ML training
 

WHY PREPROCESSING?
===================
Raw audio waveforms are huge and raw. Machine learning models work better with
processed features that highlight important characteristics. We use:
- Mel Spectrogram: visual representation showing which frequencies are loud at each moment
- MFCC: compact summary of how the audio "sounds" (similar to how humans perceive sound)
 
EXPECTED DIRECTORY STRUCTURE:
=============================
dataset/
├── train/              # Training samples (audio + features)
├── validation/         # Validation samples for hyperparameter tuning
└── test/              # Test samples for final evaluation
 
development set/
├── train.tsv          # Annotations: filename, label, start_time, end_time
└── validation.tsv
 
evaluation set/
└── test.tsv           # Test annotations
"""


# ── Standard libraries ────────────────────────────────────────────────────────
import os                      # used for file paths and checking file existence
import numpy as np             # used for numerical arrays and ML tensors
import pandas as pd            # used to read TSV annotation files (tables)
import librosa                 # main library for audio processing
import logging                 # used for printing progress and debugging info
from pathlib import Path       # modern way to handle file paths (not heavily used here)

# ── CONFIGURE LOGGING ────────────────────────────────────────────────────────
# Logging helps us track what the script is doing:
# - INFO level: general progress messages
# - WARNING level: something went wrong but we continue
# - ERROR level: serious problems
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger(__name__)

# ── AUDIO CONFIGURATION ────────────────────────────────────────────────────────
# Sampling rate = how many audio samples per second we keep
# Higher = more detail, but more computation
SAMPLE_RATE = 22050

# We force every audio sample to be around 1 second long
SEGMENT_DURATION = 1.0

# Number of Mel frequency bands (controls frequency resolution)
# Mel scale = human perception of pitch (not linear frequency)
# We divide the audio spectrum into 64 bands following human hearing
# Each band represents different frequencies of interest
N_MELS = 64

# Number of MFCC (Mel Frequency Cepstral Coefficient) features
# MFCC = compact representation of audio characteristics
# Like a "fingerprint" that captures:
#   - Frequency content
#   - Harmonic structure
#   - Formants (peaks in frequency response)
# Used in speech/cry recognition because it mimics human perception

N_MFCC = 40

# Hop length: how far we move the analysis window when processing audio
# Smaller hop = more time resolution (more frames) but slower processing
# hop_length=512 at 22050 Hz = move every ~23 milliseconds
HOP_LENGTH = 512

# FFT window size: size of each analysis window
# Larger = better frequency resolution, worse time resolution
# Smaller = better time resolution, worse frequency resolution
# 1024 is a good compromise for detecting baby cries
N_FFT = 1024

# ── DATASET SPLITS CONFIGURATION ──────────────────────────────────────────────
# Define the three splits (train/validation/test) and their locations
# Each tuple contains:
#   - Path to TSV annotation file (describes when baby cries occur)
#   - Path to folder with corresponding WAV audio files
SPLITS = {
    "train":      ("development set/train.tsv",      "dataset/train"),
    "validation": ("development set/validation.tsv", "dataset/validation"),
    "test":       ("evaluation set/test.tsv",        "dataset/test"),
}

# ── LABEL ENCODING ─────────────────────────────────────────────────────────────
# Machine learning models need numerical inputs, not text.
# We convert text labels to integers:
#   "BabyCry" → 1  (positive class: what we want to detect)
#   "Other"   → 0  (negative class: everything else)
LABEL_MAP = {"BabyCry": 1, "Other": 0}

# ── FEATURE EXTRACTION FUNCTION ───────────────────────────────────────────────
def extract_features(y: np.ndarray, sr: int) -> np.ndarray:
    """
    Convert raw audio signal into machine learning features.
    
    This is the core of feature engineering. We transform the raw waveform
    into representations that highlight relevant audio characteristics.
    
    INPUT:
    ------
    y  : np.ndarray
        Raw audio waveform (1D array of audio samples)
        Example: [0.001, -0.002, 0.003, ...] representing sound pressure
    sr : int
        Sample rate (samples per second)
        We assume sr = SAMPLE_RATE (22050)
    
    OUTPUT:
    -------
    combined : np.ndarray of shape (104, time_frames)
        Feature matrix combining Mel spectrogram + MFCC
        - Rows: 104 features (64 Mel + 40 MFCC)
        - Columns: time frames (~44 for 1-second audio)
    
    WHY THESE FEATURES?
    -------------------
    1. Mel Spectrogram:
       - Shows frequency content over time (like a waterfall plot)
       - Mel scale mimics human hearing (we hear pitch logarithmically)
       - Baby cries have distinctive frequency patterns we want to detect
    
    2. MFCC:
       - Compresses the spectrogram into 40 key numbers
       - Captures the "shape" and "quality" of the sound
       - Similar to cepstral analysis used in speech recognition
       - Much more compact than raw spectrogram (64 vs 40 features)
    """

    # ── STEP 1: COMPUTE MEL SPECTROGRAM ──────────────────────────────────────
    # Librosa's melspectrogram does:
    # 1. Divide audio into overlapping windows (using FFT)
    # 2. Compute power spectrum for each window
    # 3. Map frequencies to Mel scale (human perception)
    # 4. Produce a 2D "image" where:
    #    - Rows = frequency bands
    #    - Columns = time frames

    mel = librosa.feature.melspectrogram(
        y=y,
        sr=sr,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH,
        n_mels=N_MELS
    )

    # Convert power values to decibels (dB)
    # dB = 10 * log10(power)
    # Why? Because:
    # - Human hearing is logarithmic (we perceive volume logarithmically)
    # - Decibels compress the range of values (easier for ML models)
    # - Makes quiet and loud sounds more comparable in scale
    # ref=np.max means: 0 dB = loudest point in the signal
    log_mel = librosa.power_to_db(mel, ref=np.max)
    
    # Now log_mel has shape (64, time_frames) with values roughly -80 to 0 dB

    # ── STEP 2: COMPUTE MFCC FEATURES ────────────────────────────────────────
    # MFCC = Mel Frequency Cepstral Coefficients
    # These are derived from the Mel spectrogram through cepstral analysis
    # Think of it as "compressed" information about the spectrogram shape
    mfcc = librosa.feature.mfcc(
        y=y,
        sr=sr,
        n_mfcc=N_MFCC,
        n_fft=N_FFT,
        hop_length=HOP_LENGTH
    )

    # Now mfcc has shape (40, time_frames)
    # Each row is a different MFCC coefficient:
    # - mfcc[0] ≈ overall "loudness"
    # - mfcc[1:] ≈ spectral "shape" and "quality"


    # ── STEP 3: COMBINE FEATURES ─────────────────────────────────────────────
    # Stack Mel spectrogram and MFCC vertically
    # This creates a single feature matrix with both representations
    combined = np.concatenate([log_mel, mfcc], axis=0)

    # Result shape: (64 + 40, time_frames) = (104, time_frames)
    # Each column is a complete feature vector for one moment in time


    return combined


# ── FIXING INPUT LENGTH ───────────────────────────────────────────────────────
def pad_or_trim(feat: np.ndarray, target_frames: int) -> np.ndarray:
    """
    Ensure all feature matrices have exactly the same time dimension.
    
    WHY IS THIS NECESSARY?
    ======================
    Machine learning models require fixed-size inputs. Audio clips might be
    slightly shorter or longer than expected, so we need to standardize:
    - Too short? Add zeros (silence padding)
    - Too long? Cut extra frames (trim)
    
    PARAMETERS:
    -----------
    feat : np.ndarray of shape (104, T)
        Feature matrix with 104 features and T time frames
    target_frames : int
        Desired number of time frames
        Typically ~44 for 1-second audio at our settings
    
    RETURNS:
    --------
    feat : np.ndarray of shape (104, target_frames)
        Feature matrix resized to exactly target_frames
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
    Process one complete dataset split (train/validation/test).
    
    This is the main workhorse function that:
    1. Reads which audio files contain baby cries (from TSV)
    2. Loads those audio files
    3. Extracts relevant time segments
    4. Converts to features
    5. Returns organized data for ML
    
    PARAMETERS:
    -----------
    tsv_path : str
        Path to TSV annotation file
        Format: filename | event_label | onset | offset
        Example:
          baby_001.wav | BabyCry | 1.5 | 2.8
          baby_002.wav | Other   | 0.0 | 1.0
    
    audio_dir : str
        Directory where audio WAV files are stored
        Example: "dataset/train/"
    
    RETURNS:
    --------
    X : np.ndarray of shape (num_samples, 104, target_frames)
        Features for all samples in this split
    y : np.ndarray of shape (num_samples,)
        Labels: 1 for BabyCry, 0 for Other
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
    """
    Execute the complete preprocessing pipeline.
    
    This function:
    1. Loops through each dataset split (train/validation/test)
    2. Calls process_split() to convert audio → features
    3. Saves results as .npz files for fast loading during training
    
    .npz Format:
    ============
    NumPy's compressed archive format. Stores multiple arrays in one file:
    - Compressed: reduces file size to ~20-30% of original
    - Fast loading: loads entire dataset into memory quickly
    - Portable: works across different systems/Python versions
    """

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