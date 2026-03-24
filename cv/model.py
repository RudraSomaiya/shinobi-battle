"""
CNN Model — lightweight convolutional neural network for hand sign classification.

15 classes: 11 jutsu signs + Ram + Scrap + Shadow Clone + Unknown
Input: 128x128x3 skeleton image
Target: < 500K parameters
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

NUM_CLASSES = 15

CLASS_NAMES = sorted([
    "bird", "boar", "dog", "dragon", "hare",
    "horse", "monkey", "ox", "rat", "serpent",
    "tiger", "ram", "scrap", "shadow_clone", "unknown",
])


class ConvBlock(nn.Module):
    """Conv2d → BatchNorm → ReLU → MaxPool"""

    def __init__(self, in_ch: int, out_ch: int, pool: bool = True):
        super().__init__()
        layers = [
            nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_ch),
            nn.ReLU(inplace=True),
        ]
        if pool:
            layers.append(nn.MaxPool2d(2))
        self.block = nn.Sequential(*layers)

    def forward(self, x):
        return self.block(x)


class NarutoCNN(nn.Module):
    """
    Lightweight CNN for hand sign classification.

    Architecture:
        Conv(3→32) + Pool → Conv(32→64) + Pool → Conv(64→128) + Pool
        → AdaptiveAvgPool → FC(128→64) → FC(64→15)

    Input: (B, 3, 128, 128)
    Output: (B, 15)
    """

    def __init__(self, num_classes: int = NUM_CLASSES):
        super().__init__()
        self.features = nn.Sequential(
            ConvBlock(3, 32),    # 128→64
            ConvBlock(32, 64),   # 64→32
            ConvBlock(64, 128),  # 32→16
        )
        self.pool = nn.AdaptiveAvgPool2d(4)  # → (B, 128, 4, 4)
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(128 * 4 * 4, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.2),
            nn.Linear(64, num_classes),
        )

    def forward(self, x):
        x = self.features(x)
        x = self.pool(x)
        x = self.classifier(x)
        return x


def count_parameters(model: nn.Module) -> int:
    """Count total trainable parameters."""
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


if __name__ == "__main__":
    model = NarutoCNN()
    print(f"Total parameters: {count_parameters(model):,}")
    x = torch.randn(1, 3, 128, 128)
    out = model(x)
    print(f"Input:  {x.shape}")
    print(f"Output: {out.shape}")
    print(f"Classes: {CLASS_NAMES}")
