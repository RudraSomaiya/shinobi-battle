"""
Training Script — train the Naruto hand sign CNN.

Usage:
    python train.py --data ../data --epochs 30 --batch 32
"""

import os
import sys
import argparse

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
from torchvision import transforms, datasets
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import NarutoCNN, CLASS_NAMES, NUM_CLASSES, count_parameters


def get_transforms():
    """Data augmentation + normalization transforms."""
    train_transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.RandomRotation(15),
        transforms.RandomHorizontalFlip(p=0.3),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.RandomAffine(degrees=0, translate=(0.1, 0.1)),
        transforms.ToTensor(),
    ])

    val_transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
    ])

    return train_transform, val_transform


def train(data_dir: str, output_dir: str, epochs: int = 30,
          batch_size: int = 32, lr: float = 1e-3, val_split: float = 0.2):
    """Train the CNN model."""
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    # --- Load dataset ---
    train_tf, val_tf = get_transforms()
    full_dataset = datasets.ImageFolder(data_dir, transform=train_tf)

    # Verify classes match expected
    print(f"Found classes: {full_dataset.classes}")
    print(f"Expected:      {CLASS_NAMES}")

    # Train/Val split
    n_val = int(len(full_dataset) * val_split)
    n_train = len(full_dataset) - n_val
    train_set, val_set = random_split(full_dataset, [n_train, n_val])

    # Override transforms for val set
    val_set.dataset = datasets.ImageFolder(data_dir, transform=val_tf)

    train_loader = DataLoader(train_set, batch_size=batch_size, shuffle=True, num_workers=2)
    val_loader = DataLoader(val_set, batch_size=batch_size, shuffle=False, num_workers=2)

    print(f"Training samples: {n_train}")
    print(f"Validation samples: {n_val}")

    # --- Model ---
    model = NarutoCNN(NUM_CLASSES).to(device)
    print(f"Model parameters: {count_parameters(model):,}")

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    # --- Training Loop ---
    best_val_acc = 0.0
    train_losses, val_losses = [], []
    train_accs, val_accs = [], []

    os.makedirs(output_dir, exist_ok=True)

    for epoch in range(1, epochs + 1):
        # Train
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0

        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()

        train_loss = running_loss / total
        train_acc = correct / total
        train_losses.append(train_loss)
        train_accs.append(train_acc)

        # Validate
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0

        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                val_loss += loss.item() * images.size(0)
                _, predicted = torch.max(outputs, 1)
                val_total += labels.size(0)
                val_correct += (predicted == labels).sum().item()

        val_loss = val_loss / max(val_total, 1)
        val_acc = val_correct / max(val_total, 1)
        val_losses.append(val_loss)
        val_accs.append(val_acc)

        scheduler.step(val_loss)

        print(f"Epoch {epoch:>3}/{epochs}  "
              f"Train Loss: {train_loss:.4f}  Acc: {train_acc:.1%}  "
              f"Val Loss: {val_loss:.4f}  Acc: {val_acc:.1%}")

        # Save best
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_path = os.path.join(output_dir, "naruto_cnn.pth")
            torch.save(model.state_dict(), best_path)
            print(f"  → Saved best model (val_acc={val_acc:.1%})")

    # --- Plot metrics ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    ax1.plot(train_losses, label="Train")
    ax1.plot(val_losses, label="Val")
    ax1.set_title("Loss")
    ax1.legend()
    ax1.set_xlabel("Epoch")

    ax2.plot(train_accs, label="Train")
    ax2.plot(val_accs, label="Val")
    ax2.set_title("Accuracy")
    ax2.legend()
    ax2.set_xlabel("Epoch")

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "training_curves.png"))
    print(f"\nTraining complete. Best val accuracy: {best_val_acc:.1%}")
    print(f"Model saved to: {os.path.join(output_dir, 'naruto_cnn.pth')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Naruto Hand Sign CNN")
    parser.add_argument("--data", type=str,
                        default=os.path.join(os.path.dirname(__file__), "..", "data"),
                        help="Path to data directory (with class subdirs)")
    parser.add_argument("--output", type=str,
                        default=os.path.join(os.path.dirname(__file__), "..", "models"),
                        help="Output directory for model weights")
    parser.add_argument("--epochs", type=int, default=30)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    train(args.data, args.output, args.epochs, args.batch, args.lr)
