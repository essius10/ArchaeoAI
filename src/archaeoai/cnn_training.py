"""Frozen Phase 2E-B CNN training and coordinate-safe aggregation utilities."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from torch import Tensor, nn
from torch.optim import AdamW
from torch.utils.data import DataLoader, TensorDataset

from archaeoai.deep_learning import (
    CNN_SEEDS,
    ChannelNormalization,
    CompactTerrainCNN,
    E001TerrainDataset,
    configure_determinism,
    private_checkpoint_payload,
)
from archaeoai.terrain.full_dataset import sha256_path
from archaeoai.terrain.privacy import verify_git_ignored

CLASSIFICATION_THRESHOLD = 0.5
LEARNING_RATE = 0.001
WEIGHT_DECAY = 0.0001
ADAM_BETAS = (0.9, 0.999)
ADAM_EPSILON = 1e-8
BATCH_SIZE = 16
MAX_EPOCHS = 100
EARLY_STOPPING_PATIENCE = 12
EARLY_STOPPING_MIN_DELTA = 0.0


@dataclass(frozen=True, slots=True)
class EpochHistory:
    epoch: int
    training_loss: float
    internal_validation_loss: float
    improved: bool


@dataclass(frozen=True, slots=True)
class TrainingOutcome:
    seed: int
    state_dict: dict[str, Tensor]
    epochs_trained: int
    best_epoch: int
    best_internal_validation_loss: float
    training_seconds: float
    peak_gpu_memory_bytes: int
    state_sha256: str
    checkpoint_sha256: str
    checkpoint_size_bytes: int
    history: tuple[EpochHistory, ...]


@dataclass(frozen=True, slots=True)
class EvaluationOutcome:
    metrics: dict[str, float]
    confusion: dict[str, int]
    predictions: np.ndarray
    scores: np.ndarray
    inference_seconds: float
    inference_ms_per_patch: float


def validate_training_contract(protocol: dict[str, object]) -> None:
    """Bind executable constants to the already-frozen protocol before training."""
    if protocol.get("status") != "READY_NOT_TRAINED":
        raise ValueError("CNN training requires the frozen READY_NOT_TRAINED protocol")
    optimizer = protocol.get("optimizer")
    expected_optimizer = {
        "name": "AdamW",
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "betas": list(ADAM_BETAS),
        "epsilon": ADAM_EPSILON,
    }
    if optimizer != expected_optimizer:
        raise ValueError("CNN optimizer constants disagree with the frozen protocol")
    if protocol.get("batch_size") != BATCH_SIZE or protocol.get("max_epochs") != MAX_EPOCHS:
        raise ValueError("CNN batch size or epoch limit disagrees with the frozen protocol")
    if protocol.get("loss") != "BCEWithLogitsLoss" or protocol.get("augmentation") != "none":
        raise ValueError("CNN loss or augmentation policy disagrees with the frozen protocol")
    if protocol.get("seeds") != list(CNN_SEEDS):
        raise ValueError("CNN seeds disagree with the frozen protocol")
    early_stopping = protocol.get("early_stopping")
    if not isinstance(early_stopping, dict) or (
        early_stopping.get("monitor") != "internal_validation_bce_loss"
        or early_stopping.get("patience_epochs") != EARLY_STOPPING_PATIENCE
        or early_stopping.get("minimum_delta") != EARLY_STOPPING_MIN_DELTA
        or early_stopping.get("restore_best_weights") is not True
        or early_stopping.get("held_out_geographic_fold_used") is not False
    ):
        raise ValueError("CNN early stopping disagrees with the frozen protocol")


def materialize_dataset(dataset: E001TerrainDataset) -> TensorDataset:
    """Load a partition once after its normalization boundary is fixed."""
    if len(dataset) == 0:
        raise ValueError("cannot materialize an empty CNN dataset")
    items = [dataset[index] for index in range(len(dataset))]
    images = torch.stack([item[0] for item in items])
    labels = torch.stack([item[1] for item in items])
    return TensorDataset(images, labels)


def _loader(dataset: TensorDataset, *, shuffle: bool, seed: int) -> DataLoader:
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=shuffle,
        drop_last=False,
        num_workers=0,
        generator=generator,
    )


def model_state_sha256(state_dict: dict[str, Tensor]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state_dict):
        value = state_dict[name].detach().cpu().contiguous()
        digest.update(name.encode())
        digest.update(str(value.dtype).encode())
        digest.update(str(tuple(value.shape)).encode())
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def _mean_loss(
    model: nn.Module, loader: DataLoader, loss_function: nn.Module, device: str
) -> float:
    model.eval()
    total = 0.0
    count = 0
    with torch.inference_mode():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)
            loss = loss_function(model(images), labels)
            total += float(loss.item()) * len(labels)
            count += len(labels)
    return total / count


def train_frozen_cnn(
    training: TensorDataset,
    internal_validation: TensorDataset,
    *,
    seed: int,
    device: str,
    checkpoint_path: Path,
    project_root: Path,
    protocol_sha256: str,
) -> TrainingOutcome:
    """Train one frozen seed without any access to an outer held-out fold."""
    configure_determinism(seed)
    model = CompactTerrainCNN().to(device)
    optimizer = AdamW(
        model.parameters(),
        lr=LEARNING_RATE,
        weight_decay=WEIGHT_DECAY,
        betas=ADAM_BETAS,
        eps=ADAM_EPSILON,
    )
    loss_function = nn.BCEWithLogitsLoss()
    train_loader = _loader(training, shuffle=True, seed=seed)
    validation_loader = _loader(internal_validation, shuffle=False, seed=seed)
    best_loss = float("inf")
    best_epoch = 0
    best_state: dict[str, Tensor] | None = None
    no_improvement = 0
    history: list[EpochHistory] = []
    if device == "cuda":
        torch.cuda.reset_peak_memory_stats()
        torch.cuda.synchronize()
    started = time.perf_counter()
    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()
        training_total = 0.0
        training_count = 0
        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(model(images), labels)
            loss.backward()
            optimizer.step()
            training_total += float(loss.item()) * len(labels)
            training_count += len(labels)
        training_loss = training_total / training_count
        validation_loss = _mean_loss(model, validation_loader, loss_function, device)
        improved = validation_loss < best_loss - EARLY_STOPPING_MIN_DELTA
        if improved:
            best_loss = validation_loss
            best_epoch = epoch
            best_state = {
                name: value.detach().cpu().clone() for name, value in model.state_dict().items()
            }
            no_improvement = 0
        else:
            no_improvement += 1
        history.append(EpochHistory(epoch, training_loss, validation_loss, improved))
        if no_improvement >= EARLY_STOPPING_PATIENCE:
            break
    if device == "cuda":
        torch.cuda.synchronize()
    training_seconds = time.perf_counter() - started
    peak_memory = torch.cuda.max_memory_allocated() if device == "cuda" else 0
    if best_state is None or best_epoch == 0:
        raise RuntimeError("CNN training did not produce an internal-validation checkpoint")
    model.load_state_dict(best_state)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    verify_git_ignored(project_root, checkpoint_path)
    torch.save(
        private_checkpoint_payload(model, protocol_sha256=protocol_sha256, epoch=best_epoch),
        checkpoint_path,
    )
    return TrainingOutcome(
        seed=seed,
        state_dict=best_state,
        epochs_trained=len(history),
        best_epoch=best_epoch,
        best_internal_validation_loss=best_loss,
        training_seconds=training_seconds,
        peak_gpu_memory_bytes=peak_memory,
        state_sha256=model_state_sha256(best_state),
        checkpoint_sha256=sha256_path(checkpoint_path),
        checkpoint_size_bytes=checkpoint_path.stat().st_size,
        history=tuple(history),
    )


def binary_metrics(
    labels: np.ndarray, predictions: np.ndarray, scores: np.ndarray
) -> dict[str, float]:
    return {
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "accuracy": float(accuracy_score(labels, predictions)),
        "precision": float(precision_score(labels, predictions, zero_division=0)),
        "recall": float(recall_score(labels, predictions, zero_division=0)),
        "f1": float(f1_score(labels, predictions, zero_division=0)),
        "roc_auc": float(roc_auc_score(labels, scores)),
        "average_precision": float(average_precision_score(labels, scores)),
    }


def evaluate_frozen_cnn(
    state_dict: dict[str, Tensor],
    held_out: TensorDataset,
    *,
    device: str,
    seed: int,
) -> EvaluationOutcome:
    """Evaluate one restored checkpoint exactly once on its outer held-out fold."""
    configure_determinism(seed)
    model = CompactTerrainCNN().to(device)
    model.load_state_dict(state_dict)
    model.eval()
    loader = _loader(held_out, shuffle=False, seed=seed)
    logits: list[Tensor] = []
    labels: list[Tensor] = []
    if device == "cuda":
        torch.cuda.synchronize()
    started = time.perf_counter()
    with torch.inference_mode():
        for images, batch_labels in loader:
            logits.append(model(images.to(device)).cpu())
            labels.append(batch_labels.cpu())
    if device == "cuda":
        torch.cuda.synchronize()
    inference_seconds = time.perf_counter() - started
    label_array = torch.cat(labels).numpy().astype(np.int8)
    score_array = torch.sigmoid(torch.cat(logits)).numpy()
    prediction_array = (score_array >= CLASSIFICATION_THRESHOLD).astype(np.int8)
    tn, fp, fn, tp = confusion_matrix(label_array, prediction_array, labels=[0, 1]).ravel()
    return EvaluationOutcome(
        metrics=binary_metrics(label_array, prediction_array, score_array),
        confusion={"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        predictions=prediction_array,
        scores=score_array,
        inference_seconds=inference_seconds,
        inference_ms_per_patch=1000 * inference_seconds / len(label_array),
    )


def normalization_mapping(normalization: ChannelNormalization) -> dict[str, list[float] | str]:
    return {
        "mean": list(normalization.mean),
        "std": list(normalization.std),
        "fitted_on": normalization.fitted_on,
    }


def synthetic_cpu_inference_ms_per_patch(
    state_dict: dict[str, Tensor], *, repeats: int = 20
) -> float:
    """Benchmark model compute on synthetic input without re-evaluating held-out data."""
    model = CompactTerrainCNN().cpu().eval()
    model.load_state_dict(state_dict)
    inputs = torch.zeros((BATCH_SIZE, 4, 128, 128), dtype=torch.float32)
    with torch.inference_mode():
        model(inputs)
        started = time.perf_counter()
        for _ in range(repeats):
            model(inputs)
    return 1000 * (time.perf_counter() - started) / (repeats * BATCH_SIZE)
