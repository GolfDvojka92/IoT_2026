"""
infer.py
--------
Inference and evaluation for the BabyCryCNN model.

Usage
-----
1. Single audio file:
      python model/infer.py --audio path/to/audio.wav

2. Evaluate the entire test set:
      python model/infer.py --eval

3. Evaluation with a custom threshold:
      python model/infer.py --eval --threshold 0.6
"""

import argparse
import logging
import os

import numpy as np
import torch
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)

from model.model import build_model
from model.preprocess import (
    SAMPLE_RATE,
    SEGMENT_DURATION,
    HOP_LENGTH,
    extract_features,
    pad_or_trim,
    LABEL_MAP,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)

log = logging.getLogger(__name__)

CHECKPOINT    = "model/baby_cry_detector_model.pt"
TEST_FEATURES = "dataset/test/features.npz"

CLASS_NAMES = ["Other", "BabyCry"]


# ── Model Loading ─────────────────────────────────────────────────────────────
def load_model(checkpoint_path: str, device: torch.device) -> tuple:
    ckpt = torch.load(checkpoint_path, map_location=device)

    model = build_model(
        n_features=ckpt.get("n_features", 104),
        n_frames=ckpt.get("n_frames", 44),
    )

    model.load_state_dict(ckpt["model_state_dict"])

    model.to(device).eval()

    log.info(
        "Model loaded from %s (training epoch %d, val_f1=%.4f)",
        checkpoint_path,
        ckpt.get("epoch", -1),
        ckpt.get("val_f1", float("nan")),
    )

    return model, ckpt


# ── Single File Inference ─────────────────────────────────────────────────────

def predict_file(
    model: torch.nn.Module,
    wav_path: str,
    device: torch.device,
    n_frames: int = 44,
    threshold: float = 0.5,
) -> dict:
    """
    Loads a WAV file, splits it into windows of SEGMENT_DURATION seconds,
    classifies each window, and returns an aggregated prediction.
    """

    try:
        import librosa

        y_audio, _ = librosa.load(
            wav_path,
            sr=SAMPLE_RATE,
            mono=True,
        )

    except Exception as exc:
        log.error("Cannot load %s: %s", wav_path, exc)
        return {}

    seg_len = int(SEGMENT_DURATION * SAMPLE_RATE)

    hop = seg_len // 2  # 50% overlap between windows

    probas = []

    for start in range(0, len(y_audio), hop):

        chunk = y_audio[start: start + seg_len]

        if len(chunk) < seg_len // 4:
            break

        feat = extract_features(chunk, SAMPLE_RATE)

        feat = pad_or_trim(feat, n_frames)

        tensor = (
            torch.tensor(feat, dtype=torch.float32)
            .unsqueeze(0)
            .unsqueeze(0)
            .to(device)
        )

        with torch.no_grad():
            proba = model.predict_proba(tensor)[0].cpu().numpy()

        probas.append(proba)

    if not probas:
        return {
            "prediction": "Unknown",
            "confidence": 0.0,
        }

    mean_proba = np.stack(probas).mean(axis=0)

    baby_prob = float(mean_proba[1])

    label = (
        CLASS_NAMES[1]
        if baby_prob >= threshold
        else CLASS_NAMES[0]
    )

    return {
        "prediction": label,
        "baby_cry_prob": round(baby_prob, 4),
        "other_prob": round(float(mean_proba[0]), 4),
        "n_windows": len(probas),
    }


# ── Test Set Evaluation ───────────────────────────────────────────────────────

def evaluate(
    model: torch.nn.Module,
    device: torch.device,
    threshold: float = 0.5,
):

    if not os.path.exists(TEST_FEATURES):

        log.error(
            "Test features not found: %s",
            TEST_FEATURES,
        )

        log.error(
            "Run preprocess.py before evaluation."
        )

        return

    data = np.load(TEST_FEATURES)

    X = (
        torch.tensor(data["X"], dtype=torch.float32)
        .unsqueeze(1)
        .to(device)
    )

    y_true = data["y"]

    log.info(
        "Test samples: %d | BabyCry: %d | Other: %d",
        len(y_true),
        int(y_true.sum()),
        int((y_true == 0).sum()),
    )

    batch_size = 128

    all_probas = []

    with torch.no_grad():

        for i in range(0, len(X), batch_size):

            batch = X[i: i + batch_size]

            proba = model.predict_proba(batch).cpu().numpy()

            all_probas.append(proba)

    probas = np.concatenate(all_probas, axis=0)

    y_pred = (probas[:, 1] >= threshold).astype(int)

    print("\n" + "=" * 60)
    print(f"EVALUATION (threshold = {threshold:.2f})")
    print("=" * 60)

    print(
        classification_report(
            y_true,
            y_pred,
            target_names=CLASS_NAMES,
            digits=4,
        )
    )

    cm = confusion_matrix(y_true, y_pred)

    print("Confusion Matrix:")

    print(
        f"              Predicted Other  Predicted BabyCry"
    )

    print(
        f"Actual Other       {cm[0,0]:6d}              {cm[0,1]:6d}"
    )

    print(
        f"Actual BabyCry     {cm[1,0]:6d}              {cm[1,1]:6d}"
    )

    try:
        auc = roc_auc_score(y_true, probas[:, 1])

        print(f"\nROC-AUC: {auc:.4f}")

    except Exception:
        pass

    f1 = f1_score(
        y_true,
        y_pred,
        average="binary",
        pos_label=1,
        zero_division=0,
    )

    print(f"F1 (BabyCry): {f1:.4f}")

    print("=" * 60)


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():

    p = argparse.ArgumentParser(
        description="BabyCry inference and evaluation"
    )

    p.add_argument(
        "--audio",
        type=str,
        default=None,
        help="Path to WAV file for classification",
    )

    p.add_argument(
        "--eval",
        action="store_true",
        help="Evaluate on the test set",
    )

    p.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Threshold for BabyCry class (default: 0.5)",
    )

    p.add_argument(
        "--checkpoint",
        type=str,
        default=CHECKPOINT,
    )

    return p.parse_args()


def main():

    args = parse_args()

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    log.info("Device: %s", device)

    if not os.path.exists(args.checkpoint):

        log.error(
            "Checkpoint not found: %s",
            args.checkpoint,
        )

        log.error(
            "Run train_model.py before inference."
        )

        return

    model, ckpt = load_model(args.checkpoint, device)

    n_frames = ckpt.get("n_frames", 44)

    if args.audio:

        result = predict_file(
            model,
            args.audio,
            device,
            n_frames,
            args.threshold,
        )

        print("\n── Result ─────────────────────────────────")

        print(f"  File              : {args.audio}")

        for k, v in result.items():
            print(f"  {k:<18}: {v}")

        print("──────────────────────────────────────────")

    if args.eval:
        evaluate(
            model,
            device,
            threshold=args.threshold,
        )

    if not args.audio and not args.eval:

        log.info(
            "Provide --audio <wav> for classification "
            "or --eval for test evaluation."
        )


if __name__ == "__main__":
    main()