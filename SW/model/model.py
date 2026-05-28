"""
model.py
--------
Defines a CNN (Convolutional Neural Network) architecture for binary audio 
classification: detecting whether audio contains a baby cry or other sounds.
 
Input shape:  (batch_size, 1, n_features, T)
  - batch_size: number of samples processed together
  - 1: single channel (we treat spectrogram as grayscale image)
  - n_features: frequency dimension (64 Mel bands + 40 MFCC = 104 total)
  - T: time dimension (number of frames/timesteps)
 
Output shape: (batch_size, 2)
  - 2 logits: scores for [Other, BabyCry] classes
  - We later apply softmax to convert these into probabilities
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class ConvBlock(nn.Module):
    """
    Operations in order:
        1. Conv2d (2D convolution): learns patterns in the spectrogram
        2. BatchNorm2d: normalizes outputs to stabilize training
        3. ReLU activation: introduces non-linearity (allows learning complex patterns)
        4. Conv2d (second layer): deeper pattern learning
        5. BatchNorm2d: another normalization
        6. ReLU activation: more non-linearity
        7. MaxPool2d: reduces spatial dimensions, keeps strongest features
        8. Dropout2d: randomly deactivates some channels during training to prevent overfitting
    """

    def __init__(self, in_ch: int, out_ch: int, pool: tuple = (2, 2), dropout: float = 0.25):
        super().__init__()
        
        self.block = nn.Sequential(
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),

            nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),

            nn.MaxPool2d(pool),
            nn.Dropout2d(dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.block(x)


class BabyCryCNN(nn.Module):
    """
    Complete CNN model for baby cry detection.
    
    Architecture:
    1. Three convolutional blocks that gradually:
       - Increase the number of learned features (32 -> 64 -> 128 channels)
       - Reduce spatial dimensions through pooling
       - Extract hierarchical patterns (simple edges -> complex sounds)
    
    2. Global Average Pooling:
       - Reduces feature maps to a single value per channel
       - Makes the model invariant to input size variations
    
    3. Fully Connected Classifier:
       - Takes the 128 average-pooled features
       - Passes through hidden layer (256 units) with ReLU
       - Applies dropout for regularization
       - Outputs 2 logits (one per class)
    
    Why this architecture?
    - Convolutions: learn spatial patterns in spectrograms
    - Pooling: focus on important features, ignore noise
    - BatchNorm: stabilize training, allow higher learning rates
    - Dropout: prevent overfitting to training data
    - Global pooling: handle variable-length audio
    
    Parameters
    n_features : int
        Number of frequency features (typically 104 = 64 Mel + 40 MFCC)
        This is the HEIGHT of input spectrograms
    n_frames : int
        Number of time frames per segment (typically 44)
        This is the WIDTH of input spectrograms
        Note: We use AdaptiveAvgPool at the end, so this doesn't constrain the model
    num_classes : int
        Number of output classes (always 2: Other, BabyCry)
    dropout_fc : float
        Dropout rate for fully connected layers (0.5 = drop 50%)
        Higher dropout = more regularization = less overfitting
    """

    def __init__(
        self,
        n_features: int = 104,
        n_frames: int = 44,
        num_classes: int = 2,
        dropout_fc: float = 0.5,
    ):
        super().__init__()

        # ── Convolutional blocks ─────────────────────────────────────────────
        self.conv1 = ConvBlock(1, 32,  pool=(2, 2), dropout=0.25)
        self.conv2 = ConvBlock(32, 64, pool=(2, 2), dropout=0.25)
        self.conv3 = ConvBlock(64, 128, pool=(2, 2), dropout=0.25)

        # ── Global average pooling → input-size invariant ───────────────────
        self.gap = nn.AdaptiveAvgPool2d(1)

        # ── Fully-connected classifier head ─────────────────────────────────
        self.classifier = nn.Sequential(
            nn.Flatten(),

            nn.Linear(128, 256),
            nn.ReLU(inplace=True),
            nn.Dropout(dropout_fc),

            nn.Linear(256, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        x : (B, 1, n_features, T)

        Returns logits of shape (B, num_classes).
        """
        x = self.conv1(x)
        x = self.conv2(x)
        x = self.conv3(x)

        x = self.gap(x)  # (B, 128, 1, 1)

        return self.classifier(x)

    def predict_proba(self, x: torch.Tensor) -> torch.Tensor:
        """
        Get probability predictions instead of raw logits.
        
        Softmax converts logits to probabilities:
        - Ensures outputs sum to 1
        - Exponent emphasizes larger logits
        - Output[i] = probability of class i
        
        Args:
            x: Input tensor of shape (batch, 1, n_features, T)
        
        Returns:
            proba: Tensor of shape (batch, 2)
                   proba[:, 0] = probability of "Other" class
                   proba[:, 1] = probability of "BabyCry" class
        """
        return F.softmax(self.forward(x), dim=-1)


# ── Helper function ───────────────────────────────────────────────────────────

def build_model(n_features: int = 104, n_frames: int = 44) -> BabyCryCNN:
    """
    Factory function to create and initialize a new BabyCryCNN model.
    
    This is a convenience function that handles model instantiation.
    Called by train_model.py and infer.py to create models.
    
    Args:
        n_features: Number of frequency features (default 104)
        n_frames: Number of time frames (default 44)
    
    Returns:
        model: A BabyCryCNN instance ready for training or inference
    
    Example:
        >>> model = build_model(n_features=104, n_frames=44)
        >>> print(sum(p.numel() for p in model.parameters()))
        # Prints total number of trainable parameters
    """
    return BabyCryCNN(n_features=n_features, n_frames=n_frames)


if __name__ == "__main__":
    # Quick shape consistency test
    model = build_model()

    dummy = torch.randn(8, 1, 104, 44)  # batch=8

    out = model(dummy)
    print(f"Output shape: {out.shape}")  # should be (8, 2)

    proba = model.predict_proba(dummy)
    print(f"Probabilities (first sample): {proba[0].detach().numpy()}")

    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total parameters: {total_params:,}")