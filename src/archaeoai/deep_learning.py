"""Privacy-safe, deterministic Phase 2E-B compact-CNN setup utilities.

This module defines data and model infrastructure only.  It deliberately contains no
real-data training or evaluation runner.
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import torch
from torch import Tensor, nn
from torch.utils.data import Dataset

from archaeoai.dataset import BACKGROUND_LABEL, POSITIVE_LABEL
from archaeoai.robustness import FOLD_COUNT, fold_assignment_hash
from archaeoai.terrain.full_dataset import load_processed_archive, terrain_content_digest

CNN_CHANNELS = (
    "elevation_normalized",
    "slope_degrees",
    "hillshade_315_45",
    "local_relief_r16m",
)
CNN_INPUT_SHAPE = (4, 128, 128)
CNN_SEEDS = (20260829, 20260830, 20260831)
EXPECTED_FOLD_SHA256 = "825eb1088a53f764f991bf6bb22f2c9fe6eeb868916a5abab92012eed85d90ab"
INTERNAL_VALIDATION_FRACTION = 0.2
INTERNAL_VALIDATION_SALT = "e001-cnn-internal-validation-v1"


@dataclass(frozen=True, slots=True)
class CNNRecord:
    """Minimum private lookup state; every value originates in the safe modelling index."""

    sample_id: str
    class_label: str
    geographic_block_id: str
    observation_group_id: str
    overlap_component_id: str
    patch_sha256: str
    qa_status: str

    @property
    def related_unit_id(self) -> str:
        return self.overlap_component_id or self.observation_group_id


@dataclass(frozen=True, slots=True)
class FoldPartitions:
    """One outer-fold setup with an internal validation split isolated from the holdout."""

    internal_train: tuple[CNNRecord, ...]
    internal_validation: tuple[CNNRecord, ...]
    held_out: tuple[CNNRecord, ...]
    internal_validation_groups: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChannelNormalization:
    """Per-channel moments fitted exclusively from an internal-training partition."""

    mean: tuple[float, float, float, float]
    std: tuple[float, float, float, float]
    fitted_on: Literal["internal_train"] = "internal_train"

    def apply(self, image: np.ndarray) -> np.ndarray:
        array = np.asarray(image, dtype=np.float32)
        if array.shape != CNN_INPUT_SHAPE:
            raise ValueError("CNN normalization requires a 4x128x128 image")
        mean = np.asarray(self.mean, dtype=np.float32)[:, None, None]
        std = np.asarray(self.std, dtype=np.float32)[:, None, None]
        return (array - mean) / std


def read_fold_assignments(path: Path) -> dict[str, int]:
    """Read the already-frozen Phase 2E-A fold file without regenerating assignments."""
    assignments: dict[str, int] = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            group = row["geographic_block_id"]
            fold_text = row["fold"]
            if group in assignments or not fold_text.startswith("fold_"):
                raise ValueError("invalid or duplicate frozen fold assignment")
            assignments[group] = int(fold_text.removeprefix("fold_")) - 1
    if set(assignments.values()) != set(range(FOLD_COUNT)):
        raise ValueError("frozen CNN folds must contain fold_1 through fold_5")
    if fold_assignment_hash(assignments) != EXPECTED_FOLD_SHA256:
        raise ValueError("Phase 2E-A fold assignment hash changed")
    return assignments


def read_cnn_records(path: Path, *, enforce_e001_counts: bool = True) -> tuple[CNNRecord, ...]:
    """Read CNN labels and linkage fields only from the frozen modelling index."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    records = tuple(
        CNNRecord(
            sample_id=row["sample_id"],
            class_label=row["class_label"],
            geographic_block_id=row["geographic_block_id"],
            observation_group_id=row["observation_group_id"],
            overlap_component_id=row["overlap_component_id"],
            patch_sha256=row["patch_sha256"],
            qa_status=row["qa_status"],
        )
        for row in rows
    )
    if len({record.sample_id for record in records}) != len(records):
        raise ValueError("CNN modelling index contains duplicate sample IDs")
    allowed_labels = {POSITIVE_LABEL, BACKGROUND_LABEL}
    if any(record.class_label not in allowed_labels for record in records):
        raise ValueError("CNN label must come from the frozen modelling index vocabulary")
    if any(record.qa_status != "pass" for record in records):
        raise ValueError("CNN setup accepts only QA-passed observations")
    if enforce_e001_counts and (
        len(records) != 522
        or Counter(record.class_label for record in records)
        != Counter({POSITIVE_LABEL: 261, BACKGROUND_LABEL: 261})
    ):
        raise ValueError("frozen E001 CNN dataset counts changed")
    return records


def build_fold_partitions(
    records: tuple[CNNRecord, ...],
    assignments: dict[str, int],
    *,
    held_out_fold: int,
) -> FoldPartitions:
    """Split outer-training groups into deterministic internal train/validation groups."""
    if held_out_fold not in range(FOLD_COUNT):
        raise ValueError("held-out fold must be in the frozen five-fold range")
    record_groups = {record.geographic_block_id for record in records}
    if not record_groups <= set(assignments):
        raise ValueError("CNN records include a group absent from the frozen assignments")
    eligible_groups = sorted(
        group for group in record_groups if assignments[group] != held_out_fold
    )
    held_groups = {group for group in record_groups if assignments[group] == held_out_fold}
    if not held_groups or len(eligible_groups) < 2:
        raise ValueError("outer fold does not leave enough groups for internal validation")
    validation_count = max(1, round(len(eligible_groups) * INTERNAL_VALIDATION_FRACTION))
    ranked = sorted(
        eligible_groups,
        key=lambda group: hashlib.sha256(
            f"{INTERNAL_VALIDATION_SALT}:{held_out_fold}:{group}".encode()
        ).hexdigest(),
    )
    validation_groups = frozenset(ranked[:validation_count])
    train = tuple(
        record
        for record in records
        if record.geographic_block_id not in held_groups | validation_groups
    )
    validation = tuple(
        record for record in records if record.geographic_block_id in validation_groups
    )
    held = tuple(record for record in records if record.geographic_block_id in held_groups)
    related_partitions: dict[str, set[str]] = {}
    for name, partition in (
        ("internal_train", train),
        ("internal_validation", validation),
        ("held_out", held),
    ):
        for record in partition:
            related_partitions.setdefault(record.related_unit_id, set()).add(name)
    if any(len(parts) != 1 for parts in related_partitions.values()):
        raise ValueError("matched or overlap units cross CNN partitions")
    return FoldPartitions(
        internal_train=train,
        internal_validation=validation,
        held_out=held,
        internal_validation_groups=tuple(sorted(validation_groups)),
    )


class E001TerrainDataset(Dataset[tuple[Tensor, Tensor]]):
    """Load only four terrain arrays and an index-derived binary label."""

    def __init__(
        self,
        records: tuple[CNNRecord, ...],
        *,
        private_root: Path,
        role: Literal["internal_train", "internal_validation", "held_out"],
        normalization: ChannelNormalization | None = None,
    ) -> None:
        self._records = records
        self._private_root = private_root.resolve()
        self.role = role
        self.normalization = normalization

    def __len__(self) -> int:
        return len(self._records)

    def _archive_path(self, record: CNNRecord) -> Path:
        if record.class_label == POSITIVE_LABEL:
            relative = Path("terrain/processed") / f"{record.sample_id}.npz"
        elif record.class_label == BACKGROUND_LABEL:
            relative = Path("backgrounds/processed") / f"{record.sample_id}.npz"
        else:
            raise ValueError("CNN label did not originate in the modelling index")
        path = (self._private_root / relative).resolve()
        if self._private_root not in path.parents:
            raise ValueError("CNN archive path escaped the private data root")
        return path

    def raw_image(self, index: int) -> np.ndarray:
        record = self._records[index]
        elevation, mask, representations = load_processed_archive(self._archive_path(record))
        if terrain_content_digest(elevation, mask) != record.patch_sha256:
            raise ValueError("CNN terrain content checksum mismatch")
        image = np.stack([representations[name] for name in CNN_CHANNELS]).astype(np.float32)
        if image.shape != CNN_INPUT_SHAPE or not np.isfinite(image).all():
            raise ValueError("CNN terrain input must be finite and shaped 4x128x128")
        return image

    def __getitem__(self, index: int) -> tuple[Tensor, Tensor]:
        record = self._records[index]
        image = self.raw_image(index)
        if self.normalization is not None:
            image = self.normalization.apply(image)
        label = 1.0 if record.class_label == POSITIVE_LABEL else 0.0
        return torch.from_numpy(np.ascontiguousarray(image)), torch.tensor(
            label, dtype=torch.float32
        )


def fit_training_normalization(dataset: E001TerrainDataset) -> ChannelNormalization:
    """Fit channel statistics while fail-closing against validation/holdout data."""
    if dataset.role != "internal_train":
        raise ValueError("channel normalization may be fitted only on internal training data")
    if len(dataset) == 0:
        raise ValueError("cannot fit channel normalization on an empty dataset")
    sums = np.zeros(4, dtype=np.float64)
    squared_sums = np.zeros(4, dtype=np.float64)
    count = 0
    for index in range(len(dataset)):
        image = dataset.raw_image(index).astype(np.float64)
        sums += image.sum(axis=(1, 2))
        squared_sums += np.square(image).sum(axis=(1, 2))
        count += image.shape[1] * image.shape[2]
    mean = sums / count
    variance = np.maximum(squared_sums / count - np.square(mean), 0.0)
    std = np.sqrt(variance)
    if np.any(std <= 1e-8) or not np.isfinite(mean).all() or not np.isfinite(std).all():
        raise ValueError("CNN training normalization has a degenerate channel")
    return ChannelNormalization(tuple(mean.tolist()), tuple(std.tolist()))


class CompactTerrainCNN(nn.Module):
    """Frozen compact three-block CNN producing one binary logit."""

    def __init__(self) -> None:
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(4, 24, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(24, 48, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(48, 96, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.AdaptiveAvgPool2d((1, 1)),
        )
        self.head = nn.Sequential(nn.Flatten(), nn.Linear(96, 64), nn.ReLU(), nn.Linear(64, 1))

    def forward(self, inputs: Tensor) -> Tensor:
        if inputs.ndim != 4 or tuple(inputs.shape[1:]) != CNN_INPUT_SHAPE:
            raise ValueError("CompactTerrainCNN requires N x 4 x 128 x 128 input")
        return self.head(self.features(inputs)).squeeze(1)


def trainable_parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)


def configure_determinism(seed: int) -> None:
    """Apply the frozen deterministic policy to Python, NumPy, CPU, and CUDA."""
    if seed not in CNN_SEEDS:
        raise ValueError("CNN seed was not pre-registered")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def private_checkpoint_payload(
    model: nn.Module, *, protocol_sha256: str, epoch: int
) -> dict[str, object]:
    """Build a weights-only checkpoint without observations or identifying metadata."""
    if len(protocol_sha256) != 64 or epoch < 0:
        raise ValueError("invalid private checkpoint metadata")
    return {
        "state_dict": {name: value.detach().cpu() for name, value in model.state_dict().items()},
        "protocol_sha256": protocol_sha256,
        "epoch": epoch,
    }


def cnn_protocol_hash(payload: dict[str, object]) -> str:
    content = {key: value for key, value in payload.items() if key != "protocol_sha256"}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_cnn_protocol(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "READY_NOT_TRAINED":
        raise ValueError("CNN protocol status must remain READY_NOT_TRAINED")
    if payload.get("fold_assignment_sha256") != EXPECTED_FOLD_SHA256:
        raise ValueError("CNN protocol is not bound to the frozen Phase 2E-A folds")
    expected = payload.get("protocol_sha256")
    if not isinstance(expected, str) or cnn_protocol_hash(payload) != expected:
        raise ValueError("CNN protocol SHA-256 mismatch")
    if payload.get("parameter_count") != trainable_parameter_count(CompactTerrainCNN()):
        raise ValueError("CNN protocol parameter count does not match the architecture")
    if payload.get("seeds") != list(CNN_SEEDS):
        raise ValueError("CNN protocol seeds changed")
    return payload
