"""
train_model.py
==============
Training script for the BabyCryCNN model.

This script trains a CNN to detect baby cries from audio features that were
pre-computed by preprocess.py.

USAGE EXAMPLES:
===============
# Train with default settings (30 epochs, batch size 64, learning rate 0.001)
python train_model.py

# Train with custom hyperparameters
python train_model.py --epochs 50 --batch-size 32 --lr 5e-4

# Train on GPU (automatic if CUDA is available)
# Train on CPU (automatic fallback if GPU unavailable)

WHAT GETS SAVED:
================
model/best_model.pt     - Best model checkpoint (uses validation F1 score)
model/training_log.csv  - Training metrics for each epoch
"""

import argparse             # Command-line argument parsing
import logging             # Progress and debugging logging
import os                  # File operations
import time                # Timing epochs
from pathlib import Path   # Modern file path handling

import numpy as np         # Numerical arrays
import pandas as pd        # Data tables and CSV
import torch               # Deep learning framework
import torch.nn as nn      # Neural network modules
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
from sklearn.metrics import f1_score, classification_report, confusion_matrix

from model import build_model  # Import the CNN architecture

# ── CONFIGURE LOGGING ────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                          PATH DEFINITIONS                                 ║
# ╚════════════════════════════════════════════════════════════════════════════╝

# Dictionary specifying where the pre-computed feature files are located
# These files were created by preprocess.py
FEATURES = {
    "train":      "dataset/train/features.npz",      # Training data
    "validation": "dataset/validation/features.npz", # Validation data (used during training)
}

# Where to save the best model checkpoint
# We save the model with the highest validation F1 score
CHECKPOINT = "model/best_model.pt"

# Where to save training metrics (loss, accuracy, F1 for each epoch)
LOG_CSV = "model/training_log.csv"


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                         DATA LOADING FUNCTIONS                            ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def load_split(path: str):
    """
    Load pre-computed features from a .npz file.
    
    .npz files are NumPy's compressed archive format containing multiple arrays.
    They were created by preprocess.py and contain:
    - X: Feature matrices (spectrograms + MFCC)
    - y: Labels (0=Other, 1=BabyCry)
    
    PARAMETERS:
    -----------
    path : str
        Path to the .npz file
        Example: "dataset/train/features.npz"
    
    RETURNS:
    --------
    X : torch.Tensor of shape (num_samples, 1, 104, 44)
        Feature tensor (unsqueezed to add channel dimension for CNN)
        - num_samples: number of audio segments
        - 1: single channel (grayscale spectrogram, like a single-channel image)
        - 104: frequency features (64 Mel + 40 MFCC)
        - 44: time frames (~1 second of audio)
    
    y : torch.Tensor of shape (num_samples,)
        Label tensor: 0 (Other) or 1 (BabyCry)
    
    WHY UNSQUEEZE?
    ==============
    Numpy saves (num_samples, 104, 44).
    CNNs expect (num_samples, channels, height, width).
    We add a channel dimension: (num_samples, 1, 104, 44)
    This makes it compatible with Conv2d layers.
    """
    
    # Load the .npz file
    data = np.load(path)
    
    # Extract features: shape (num_samples, 104, 44)
    X = data["X"]
    
    # Extract labels: shape (num_samples,)
    y = data["y"]
    
    # Convert NumPy arrays to PyTorch tensors
    # dtype=torch.float32: standard precision for neural networks
    X = torch.tensor(X, dtype=torch.float32)
    
    # unsqueeze(1) adds a dimension at position 1
    # (num_samples, 104, 44) → (num_samples, 1, 104, 44)
    # Position 1 becomes the channel dimension (like RGB in images)
    X = X.unsqueeze(1)
    
    # Convert labels to torch.long (integer type required by loss functions)
    y = torch.tensor(y, dtype=torch.long)
    
    return X, y


def make_loader(X: torch.Tensor, y: torch.Tensor,
                batch_size: int, shuffle: bool = False,
                balanced: bool = False) -> DataLoader:
    """
    Create a DataLoader for efficient batch training.
    
    DataLoaders handle:
    - Batching: grouping samples into batches
    - Shuffling: randomizing sample order each epoch
    - Sampling: handling class imbalance with weighted sampling
    - Multi-threading: prefetching data in background
    
    PARAMETERS:
    -----------
    X : torch.Tensor
        Feature tensor of shape (num_samples, 1, 104, 44)
    y : torch.Tensor
        Label tensor of shape (num_samples,)
    batch_size : int
        How many samples per batch (larger = faster but more memory)
        Typical: 32, 64, 128
    shuffle : bool
        Randomize sample order each epoch (good for training, False for validation)
    balanced : bool
        Use weighted sampling to handle class imbalance
        Important: if dataset has 80% "Other" and 20% "BabyCry",
        weighted sampling ensures balanced batches during training
    
    RETURNS:
    --------
    loader : torch.utils.data.DataLoader
        Iterable that yields (X_batch, y_batch) tuples
    """
    
    # Create a TensorDataset: pairs (X[i], y[i]) for all i
    dataset = TensorDataset(X, y)
    
    # Initialize sampler as None (will use default sampling)
    sampler = None
    
    # ── HANDLE CLASS IMBALANCE IF REQUESTED ────────────────────────────────
    if balanced:
        # Count how many samples of each class
        counts = torch.bincount(y)  # [num_class_0, num_class_1]
        
        # Compute weights: classes with fewer samples get higher weights
        # Weight = 1 / count (inverse frequency)
        # If class 1 has 100 samples and class 0 has 900:
        #   weight_0 = 1/900 ≈ 0.0011
        #   weight_1 = 1/100 = 0.01
        # So class 1 is sampled ~9x more often (per-sample basis)
        weights = 1.0 / counts.float()
        
        # Assign a weight to each sample based on its class
        # Creates array: [weight_of_y[0], weight_of_y[1], ...]
        sample_weights = weights[y]
        
        # Create a sampler that samples according to weights
        # This ensures roughly equal class distribution in each batch
        sampler = WeightedRandomSampler(sample_weights, len(sample_weights))
        
        # Note: sampler and shuffle can't both be True
        # Sampler already handles randomization
        shuffle = False
    
    # Create and return the DataLoader
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=shuffle,           # Shuffle when no sampler (sampler does it automatically)
        sampler=sampler,           # Use weighted sampler if balanced=True
        num_workers=0,             # Number of background processes (0 = main thread)
        pin_memory=torch.cuda.is_available(),  # Pin memory if GPU available (faster transfer)
    )


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                           TRAINING LOOP                                   ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def run_epoch(model, loader, criterion, optimizer, device, train: bool):
    """
    Run one epoch of training or validation.
    
    An epoch = one pass through all data
    - Training epoch: forward pass, compute loss, backprop, update weights
    - Validation epoch: forward pass, compute metrics, no weight updates
    
    PARAMETERS:
    -----------
    model : torch.nn.Module
        The CNN model
    loader : torch.utils.data.DataLoader
        Yields (X_batch, y_batch) for this epoch
    criterion : torch.nn.Module
        Loss function (e.g., CrossEntropyLoss)
    optimizer : torch.optim.Optimizer
        Optimizer for updating weights (e.g., AdamW)
        None for validation (no weight updates)
    device : torch.device
        cuda or cpu
    train : bool
        If True: training mode (updates weights, uses dropout)
        If False: evaluation mode (no updates, no dropout)
    
    RETURNS:
    --------
    avg_loss : float
        Average loss over the epoch
    acc : float
        Accuracy: percentage of correct predictions
    f1 : float
        F1 score for binary classification (focuses on hard cases)
    
    WHY F1 SCORE?
    =============
    With imbalanced data (many "Other", few "BabyCry"):
    - Accuracy is misleading: 90% accuracy if we predict "Other" for everything!
    - F1 score balances precision and recall: catches both false positives and false negatives
    - Used to select best model during training
    """
    
    # ── SET MODEL MODE ──────────────────────────────────────────────────────
    if train:
        # Training mode: enable dropout, batch norm uses running stats
        model.train()
    else:
        # Evaluation mode: disable dropout, batch norm uses batch stats
        model.eval()
    
    # Initialize accumulators for metrics
    total_loss = 0.0       # Sum of losses (will divide by number of samples)
    all_preds = []         # Collect predictions to compute metrics
    all_labels = []        # Collect ground truth labels
    
    # ── CHOOSE GRADIENT CONTEXT ──────────────────────────────────────────────
    # torch.enable_grad(): compute gradients (for backprop during training)
    # torch.no_grad(): don't compute gradients (faster, less memory during validation)
    ctx = torch.enable_grad() if train else torch.no_grad()
    
    # ── PROCESS BATCHES ──────────────────────────────────────────────────────
    with ctx:
        # loader yields (X_batch, y_batch) for each batch
        for X_batch, y_batch in loader:
            # Move data to device (GPU or CPU)
            X_batch = X_batch.to(device)
            y_batch = y_batch.to(device)
            
            # ── FORWARD PASS ────────────────────────────────────────────────
            # Model predicts logits for each sample
            # logits shape: (batch_size, 2)
            # logits[:, 0] = score for "Other" class
            # logits[:, 1] = score for "BabyCry" class
            logits = model(X_batch)
            
            # ── COMPUTE LOSS ────────────────────────────────────────────────
            # CrossEntropyLoss:
            # 1. Applies softmax to convert logits to probabilities
            # 2. Takes negative log of correct class probability
            # 3. Returns scalar loss value
            # Weighted by class_weights: penalizes minority class more
            loss = criterion(logits, y_batch)
            
            # ── BACKPROPAGATION (only during training) ──────────────────────
            if train:
                # Zero gradients from previous iteration
                # Without this, gradients accumulate (usually not desired)
                optimizer.zero_grad()
                
                # Backpropagation: compute gradients
                # loss.backward() computes dL/dw for all parameters w
                loss.backward()
                
                # Gradient clipping: prevent exploding gradients
                # If any gradient has norm > 5.0, scale all gradients down
                # This helps with training stability
                nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
                
                # Update parameters
                # optimizer.step() applies: w = w - lr * dL/dw
                optimizer.step()
            
            # ── ACCUMULATE METRICS ──────────────────────────────────────────
            # Add batch loss to total (weight by batch size)
            total_loss += loss.item() * len(y_batch)
            
            # Get predictions: argmax gives class with highest score
            # logits shape: (batch_size, 2)
            # argmax(dim=1) gives index (0 or 1) of max value per sample
            # argmax() returns (batch_size,) with values in {0, 1}
            preds = logits.argmax(dim=1).cpu().numpy()
            
            # Move predictions and labels to CPU and collect
            all_preds.extend(preds)
            all_labels.extend(y_batch.cpu().numpy())
    
    # ── COMPUTE EPOCH METRICS ────────────────────────────────────────────────
    # Average loss: total loss / number of samples
    n = len(all_labels)
    avg_loss = total_loss / n
    
    # F1 score: balances precision and recall
    # average="binary": specialized for binary classification
    # pos_label=1: treat "BabyCry" (class 1) as the positive class
    # zero_division=0: if TP+FP=0 or TP+FN=0, return 0 instead of warning
    f1 = f1_score(all_labels, all_preds, average="binary", pos_label=1, zero_division=0)
    
    # Accuracy: percentage of correct predictions
    # Convert to NumPy for element-wise comparison
    acc = float(np.mean(np.array(all_preds) == np.array(all_labels)))
    
    return avg_loss, acc, f1


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                           MAIN TRAINING FUNCTION                          ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def train(args):
    """
    Main training loop: train model for multiple epochs with validation.
    
    TRAINING PROCEDURE:
    ===================
    For each epoch:
    1. Run one training epoch (update weights using training data)
    2. Run one validation epoch (evaluate on unseen validation data)
    3. Compare validation F1 score to best so far
    4. Save checkpoint if this is the best F1 yet
    5. Adjust learning rate (scheduler)
    
    PARAMETERS:
    -----------
    args : argparse.Namespace
        args.epochs: number of training epochs
        args.batch_size: samples per batch
        args.lr: learning rate
    """
    
    # ── DEVICE SELECTION ────────────────────────────────────────────────────
    # Use GPU if available, fallback to CPU
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info("Device: %s", device)
    
    # ── LOAD DATA ───────────────────────────────────────────────────────────
    log.info("Loading features...")
    
    # Load training data
    X_tr, y_tr = load_split(FEATURES["train"])
    
    # Load validation data
    X_va, y_va = load_split(FEATURES["validation"])
    
    log.info("Train: %s  |  Val: %s", tuple(X_tr.shape), tuple(X_va.shape))
    
    # Extract feature dimensions for model initialization
    # n_features = 104 (64 Mel + 40 MFCC)
    # n_frames = 44 (time frames for ~1 second audio)
    n_features, n_frames = X_tr.shape[2], X_tr.shape[3]
    log.info("n_features=%d  n_frames=%d", n_features, n_frames)
    
    # ── CREATE DATA LOADERS ─────────────────────────────────────────────────
    # Training loader: shuffle and balance classes
    train_loader = make_loader(X_tr, y_tr, args.batch_size, balanced=True)
    
    # Validation loader: no shuffle, no balancing (evaluate on natural distribution)
    val_loader = make_loader(X_va, y_va, args.batch_size, shuffle=False)
    
    # ── INITIALIZE MODEL ────────────────────────────────────────────────────
    log.info("Building model...")
    
    # Create model with correct input dimensions
    model = build_model(n_features, n_frames).to(device)
    
    # Count total parameters
    total_params = sum(p.numel() for p in model.parameters())
    log.info("Parameters: %s", f"{total_params:,}")
    
    # ── SETUP LOSS FUNCTION ─────────────────────────────────────────────────
    # Compute class weights to handle imbalance
    # If "BabyCry" is rare, give it higher weight in the loss
    counts = torch.bincount(y_tr)  # [num_other, num_babycry]
    
    # Weight inverse to class frequency
    # Rare class: higher weight (loss term contributes more)
    # Common class: lower weight (loss term contributes less)
    class_weights = (1.0 / counts.float()).to(device)
    
    # CrossEntropyLoss with class weights
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    
    # ── SETUP OPTIMIZER ────────────────────────────────────────────────────
    # AdamW: variant of Adam with decoupled weight decay
    # lr: learning rate (step size for weight updates)
    # weight_decay: L2 regularization (penalizes large weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    
    # ── SETUP LEARNING RATE SCHEDULER ──────────────────────────────────────
    # Cosine annealing: learning rate decreases following cosine curve
    # Starts high (fast learning) → gradually decreases (fine-tuning)
    # T_max: number of epochs for full cycle
    # This helps: fast convergence → fine-tuning → avoiding local minima
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)
    
    # ── TRAINING LOOP ──────────────────────────────────────────────────────
    best_val_f1 = -1.0  # Track best validation F1 score
    records = []        # Store metrics for each epoch
    
    log.info("Starting training (%d epochs)...", args.epochs)
    
    # Loop over epochs
    for epoch in range(1, args.epochs + 1):
        # Start timer for this epoch
        t0 = time.time()
        
        # ── TRAINING EPOCH ──────────────────────────────────────────────────
        # train=True: update weights, use dropout, etc.
        tr_loss, tr_acc, tr_f1 = run_epoch(
            model, train_loader, criterion, optimizer, device, train=True
        )
        
        # ── VALIDATION EPOCH ────────────────────────────────────────────────
        # train=False: no weight updates, no dropout
        # optimizer=None: not used during validation
        va_loss, va_acc, va_f1 = run_epoch(
            model, val_loader, criterion, None, device, train=False
        )
        
        # ── LEARNING RATE SCHEDULING ───────────────────────────────────────
        # Update learning rate for next epoch
        scheduler.step()
        
        # Calculate elapsed time for this epoch
        elapsed = time.time() - t0
        
        # ── LOG METRICS ─────────────────────────────────────────────────────
        log.info(
            "Epoch %3d/%d | tr_loss=%.4f tr_acc=%.3f tr_f1=%.3f "
            "| val_loss=%.4f val_acc=%.3f val_f1=%.3f | %.1fs",
            epoch, args.epochs,
            tr_loss, tr_acc, tr_f1,
            va_loss, va_acc, va_f1,
            elapsed,
        )
        
        # Store metrics in record for CSV export
        records.append({
            "epoch": epoch,
            "tr_loss": tr_loss, "tr_acc": tr_acc, "tr_f1": tr_f1,
            "val_loss": va_loss, "val_acc": va_acc, "val_f1": va_f1,
        })
        
        # ── CHECKPOINT BEST MODEL ──────────────────────────────────────────
        # Save model if validation F1 improved
        if va_f1 > best_val_f1:
            best_val_f1 = va_f1
            
            # Create model directory if needed
            os.makedirs("model", exist_ok=True)
            
            # Save checkpoint containing:
            # - Model weights (state_dict)
            # - Epoch number
            # - Best F1 score
            # - Feature dimensions (for loading later)
            torch.save({
                "epoch": epoch,
                "model_state_dict": model.state_dict(),
                "val_f1": va_f1,
                "n_features": n_features,
                "n_frames": n_frames,
            }, CHECKPOINT)
            
            log.info("  ✓ New best model saved (val_f1=%.4f)", va_f1)
    
    # ── SAVE TRAINING LOG ──────────────────────────────────────────────────
    # Convert records list to DataFrame and save as CSV
    pd.DataFrame(records).to_csv(LOG_CSV, index=False)
    log.info("Training completed. Best val F1: %.4f", best_val_f1)
    log.info("Checkpoint: %s  |  Log: %s", CHECKPOINT, LOG_CSV)


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                         COMMAND-LINE INTERFACE                            ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def parse_args():
    """
    Parse command-line arguments.
    
    USAGE:
    ------
    python train_model.py --epochs 50 --batch-size 32 --lr 5e-4
    
    If you don't specify arguments, defaults are used.
    """
    p = argparse.ArgumentParser(description="Train BabyCry CNN")
    
    # Argument 1: number of training epochs
    p.add_argument(
        "--epochs",
        type=int,
        default=30,
        help="Number of training epochs (default: 30)"
    )
    
    # Argument 2: batch size
    p.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Batch size for training (default: 64)"
    )
    
    # Argument 3: learning rate
    p.add_argument(
        "--lr",
        type=float,
        default=1e-3,
        help="Learning rate (default: 0.001)"
    )
    
    return p.parse_args()


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                         ENTRY POINT                                       ║
# ╚════════════════════════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    # Parse command-line arguments
    args = parse_args()
    
    # Run training
    train(args)
    
    # After training:
    # - Best model saved to: model/best_model.pt
    # - Training log saved to: model/training_log.csv
    # Next step: run infer.py for evaluation or inference