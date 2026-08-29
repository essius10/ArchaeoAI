"""Privacy-bounded Random-Forest inference utilities for E001 Phase 2F."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import pickle
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from archaeoai.dataset import BACKGROUND_LABEL, POSITIVE_LABEL, read_dataset_index
from archaeoai.model_data import mean_pool_4x4, validate_frozen_primary_config
from archaeoai.modelling import build_estimator
from archaeoai.terrain.full_dataset import (
    load_processed_archive,
    terrain_content_digest,
    validate_representations,
)
from archaeoai.terrain.privacy import (
    assert_coordinate_safe_mapping,
    ensure_private_output,
    verify_git_ignored,
)
from archaeoai.terrain.representations import terrain_representations
from archaeoai.terrain.validation import evaluate_patch

EXPECTED_PRIMARY_CONFIG_SHA256 = "20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"
REPRESENTATION_CHANNELS = (
    "elevation_normalized",
    "slope_degrees",
    "hillshade_315_45",
    "local_relief_r16m",
)
PATCH_SIZE_PIXELS = 128
PATCH_SIZE_M = 128
STRIDE_PIXELS = 64
STRIDE_M = 64
FEATURE_COUNT = 4096
MODEL_SEED = 20260829
DOMAIN_SIZE_PIXELS = 5000
HIGH_PERCENTILE = 0.99
MEDIUM_PERCENTILE_RANGE = (0.45, 0.55)
QUEUE_LIMIT = 25
DEDUPLICATION_DISTANCE_M = 128.0
DEDUPLICATION_IOU = 0.25
REVIEW_SAMPLE_SEED = 20260829


@dataclass(frozen=True, slots=True)
class PixelWindow:
    """A private raster-relative window; it is never a tracked public record."""

    private_token: str
    row_offset: int
    column_offset: int
    size_pixels: int = PATCH_SIZE_PIXELS

    @property
    def centre(self) -> tuple[float, float]:
        half = self.size_pixels / 2
        return self.column_offset + half, self.row_offset + half


@dataclass(frozen=True, slots=True)
class PrivateScoredWindow:
    """A score joined to a private raster-relative window."""

    window: PixelWindow
    model_score: float


@dataclass(frozen=True, slots=True)
class FullTrainingData:
    features: np.ndarray
    labels: np.ndarray
    modelling_index_sha256: str
    terrain_inventory_sha256: str


@dataclass(frozen=True, slots=True)
class QueueSelection:
    high: tuple[PrivateScoredWindow, ...]
    medium: tuple[PrivateScoredWindow, ...]
    reference: tuple[PrivateScoredWindow, ...]


def protocol_hash(payload: dict[str, Any]) -> str:
    content = {key: value for key, value in payload.items() if key != "protocol_sha256"}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def validate_inference_protocol(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = payload.get("protocol_sha256")
    if not isinstance(expected, str) or protocol_hash(payload) != expected:
        raise ValueError("Phase 2F-A protocol hash mismatch")
    if payload.get("frozen") is not True:
        raise ValueError("Phase 2F-A protocol is not frozen")
    if payload.get("created_before_new_terrain_scoring") is not True:
        raise ValueError("Phase 2F-A protocol was not frozen before inference")
    if payload.get("primary_config_sha256") != EXPECTED_PRIMARY_CONFIG_SHA256:
        raise ValueError("Phase 2F-A protocol does not bind the frozen Random Forest")
    execution = payload.get("execution_state", {})
    if execution.get("real_candidate_scan_completed") is not False:
        raise ValueError("Phase 2F-A setup protocol must precede real candidate scanning")
    return payload


def generate_patch_grid(
    raster_shape: tuple[int, int],
    *,
    private_domain_salt: str,
    patch_size_pixels: int = PATCH_SIZE_PIXELS,
    stride_pixels: int = STRIDE_PIXELS,
) -> tuple[PixelWindow, ...]:
    """Generate a deterministic row-major grid using only private raster-relative offsets."""
    if len(private_domain_salt) < 16:
        raise ValueError("private domain salt must contain at least 16 characters")
    if len(raster_shape) != 2 or min(raster_shape) < patch_size_pixels:
        raise ValueError("raster is smaller than the frozen patch size")
    if patch_size_pixels != PATCH_SIZE_PIXELS or stride_pixels != STRIDE_PIXELS:
        raise ValueError("patch size and stride are frozen for Phase 2F-A")
    rows = range(0, raster_shape[0] - patch_size_pixels + 1, stride_pixels)
    columns = range(0, raster_shape[1] - patch_size_pixels + 1, stride_pixels)
    windows = []
    for row in rows:
        for column in columns:
            token = hashlib.sha256(
                f"{private_domain_salt}:{row}:{column}:{patch_size_pixels}".encode()
            ).hexdigest()
            windows.append(PixelWindow(token, row, column, patch_size_pixels))
    return tuple(windows)


def features_from_representations(representations: dict[str, np.ndarray]) -> np.ndarray:
    """Use the exact Phase 2D channel order and 4×4 pooling implementation."""
    if set(representations) != set(REPRESENTATION_CHANNELS):
        raise ValueError("inference requires exactly the four frozen terrain representations")
    features = np.concatenate(
        [mean_pool_4x4(representations[channel]) for channel in REPRESENTATION_CHANNELS]
    ).astype(np.float32, copy=False)
    if features.shape != (FEATURE_COUNT,) or not np.isfinite(features).all():
        raise ValueError("inference features do not match the frozen finite 4,096-feature design")
    return features


def features_from_elevation(
    elevation: np.ndarray,
    mask: np.ndarray,
    *,
    resolution_m: float = 1.0,
) -> np.ndarray:
    """Run E001 terrain QA, four representations, and pooling for one inference patch."""
    values = np.asarray(elevation, dtype=np.float32)
    invalid = np.asarray(mask, dtype=bool) | ~np.isfinite(values)
    qa = evaluate_patch(
        values,
        invalid,
        expected_shape=(PATCH_SIZE_PIXELS, PATCH_SIZE_PIXELS),
        max_nodata_fraction=0.2,
    )
    if not qa.passed:
        raise ValueError(f"inference patch failed frozen terrain QA: {qa.reasons}")
    representations = terrain_representations(
        values,
        resolution_m=resolution_m,
        mask=invalid,
        local_relief_radius_m=16.0,
        hillshade_azimuth_deg=315.0,
        hillshade_altitude_deg=45.0,
    )
    representation_qa = validate_representations(representations, source_mask=invalid)
    if not representation_qa.passed:
        raise ValueError(
            "inference representations failed frozen QA: " + ", ".join(representation_qa.reasons)
        )
    return features_from_representations(representations)


def _private_training_archive(root: Path, sample_id: str, class_label: str) -> Path:
    if class_label == POSITIVE_LABEL:
        subdirectory = "terrain/processed"
    elif class_label == BACKGROUND_LABEL:
        subdirectory = "backgrounds/processed"
    else:
        raise ValueError("training labels must come from the frozen modelling index")
    return root / "data/private/e001" / subdirectory / f"{sample_id}.npz"


def load_full_training_data(project_root: Path) -> FullTrainingData:
    """Load all 522 curated observations without using metadata as model features."""
    root = project_root.resolve()
    index_path = root / "outputs/dataset/e001_modelling_index.csv"
    records = sorted(read_dataset_index(index_path), key=lambda row: row.sample_id)
    if len(records) != 522:
        raise ValueError("Phase 2F full fit requires exactly 522 frozen observations")
    features = []
    labels = []
    inventory = hashlib.sha256()
    for record in records:
        archive_path = _private_training_archive(root, record.sample_id, record.class_label)
        elevation, mask, representations = load_processed_archive(archive_path)
        observed_digest = terrain_content_digest(elevation, mask)
        if observed_digest != record.patch_sha256:
            raise ValueError("training terrain content differs from the frozen modelling index")
        features.append(features_from_representations(representations))
        labels.append(1 if record.class_label == POSITIVE_LABEL else 0)
        inventory.update(f"{record.sample_id}:{observed_digest}\n".encode())
    matrix = np.asarray(features, dtype=np.float32)
    target = np.asarray(labels, dtype=np.int8)
    if matrix.shape != (522, FEATURE_COUNT):
        raise ValueError("Phase 2F training matrix does not match the frozen design")
    if np.bincount(target, minlength=2).tolist() != [261, 261]:
        raise ValueError("Phase 2F training labels must remain exactly balanced")
    return FullTrainingData(
        matrix,
        target,
        hashlib.sha256(index_path.read_bytes()).hexdigest(),
        inventory.hexdigest(),
    )


def fit_frozen_random_forest(
    project_root: Path,
) -> tuple[RandomForestClassifier, FullTrainingData]:
    config = validate_frozen_primary_config(
        project_root / "outputs/modelling/e001_primary_baseline_config.json"
    )
    if config.get("config_sha256") != EXPECTED_PRIMARY_CONFIG_SHA256:
        raise ValueError("unexpected frozen primary configuration")
    training = load_full_training_data(project_root)
    estimator = build_estimator("random_forest")
    estimator.fit(training.features, training.labels)
    if estimator.get_params(deep=False) != {
        "bootstrap": True,
        "ccp_alpha": 0.0,
        "class_weight": None,
        "criterion": "gini",
        "max_depth": 8,
        "max_features": "sqrt",
        "max_leaf_nodes": None,
        "max_samples": None,
        "min_impurity_decrease": 0.0,
        "min_samples_leaf": 5,
        "min_samples_split": 2,
        "min_weight_fraction_leaf": 0.0,
        "monotonic_cst": None,
        "n_estimators": 300,
        "n_jobs": 1,
        "oob_score": False,
        "random_state": MODEL_SEED,
        "verbose": 0,
        "warm_start": False,
    }:
        raise ValueError("fitted estimator differs from the frozen Random Forest")
    return estimator, training


def model_state_sha256(estimator: RandomForestClassifier) -> str:
    """Hash learned tree state without sample identifiers or serialization metadata."""
    if not hasattr(estimator, "estimators_") or len(estimator.estimators_) != 300:
        raise ValueError("Random Forest must be fitted with all 300 frozen trees")
    digest = hashlib.sha256()
    parameters = {
        key: value
        for key, value in estimator.get_params(deep=False).items()
        if key in {"n_estimators", "max_depth", "min_samples_leaf", "max_features", "random_state"}
    }
    digest.update(json.dumps(parameters, sort_keys=True, separators=(",", ":")).encode())
    for name, value in (
        ("classes", estimator.classes_),
        ("n_classes", np.atleast_1d(estimator.n_classes_)),
        ("n_features_in", np.atleast_1d(estimator.n_features_in_)),
        ("n_outputs", np.atleast_1d(estimator.n_outputs_)),
    ):
        array = np.ascontiguousarray(value)
        digest.update(name.encode())
        digest.update(str(array.dtype).encode())
        digest.update(str(array.shape).encode())
        digest.update(array.tobytes())
    for index, tree in enumerate(estimator.estimators_):
        digest.update(f"tree:{index}".encode())
        state = tree.tree_.__getstate__()
        for name in sorted(state):
            value = state[name]
            digest.update(name.encode())
            if isinstance(value, np.ndarray):
                array = np.ascontiguousarray(value)
                digest.update(str(array.dtype).encode())
                digest.update(str(array.shape).encode())
                digest.update(array.tobytes())
            else:
                digest.update(str(value).encode())
    return digest.hexdigest()


def write_private_model(
    project_root: Path,
    estimator: RandomForestClassifier,
    *,
    destination: str | Path,
) -> tuple[Path, str]:
    path = ensure_private_output(project_root, destination)
    verify_git_ignored(project_root, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = pickle.dumps(estimator, protocol=5)
    path.write_bytes(payload)
    return path, hashlib.sha256(payload).hexdigest()


def load_private_model(
    project_root: Path,
    source: str | Path,
    *,
    expected_artifact_sha256: str,
    expected_state_sha256: str,
) -> RandomForestClassifier:
    path = ensure_private_output(project_root, source)
    verify_git_ignored(project_root, path)
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != expected_artifact_sha256:
        raise ValueError("private model artifact checksum mismatch")
    estimator = pickle.loads(payload)  # noqa: S301 - private hash-bound project artifact only
    if not isinstance(estimator, RandomForestClassifier):
        raise ValueError("private model artifact is not a Random Forest")
    if model_state_sha256(estimator) != expected_state_sha256:
        raise ValueError("private model state checksum mismatch")
    return estimator


def score_feature_matrix(estimator: RandomForestClassifier, features: np.ndarray) -> np.ndarray:
    matrix = np.asarray(features, dtype=np.float32)
    if matrix.ndim != 2 or matrix.shape[1] != FEATURE_COUNT or not np.isfinite(matrix).all():
        raise ValueError("score input must be a finite matrix of frozen terrain-only features")
    scores = np.asarray(estimator.predict_proba(matrix)[:, 1], dtype=np.float64)
    if not np.isfinite(scores).all() or np.any((scores < 0) | (scores > 1)):
        raise ValueError("Random Forest produced invalid model scores")
    return scores


def rank_windows(windows: tuple[PrivateScoredWindow, ...]) -> tuple[PrivateScoredWindow, ...]:
    if any(not 0 <= item.model_score <= 1 for item in windows):
        raise ValueError("model scores must lie within [0, 1]")
    return tuple(sorted(windows, key=lambda item: (-item.model_score, item.window.private_token)))


def _intersection_over_union(first: PixelWindow, second: PixelWindow) -> float:
    overlap_width = max(
        0,
        min(first.column_offset + first.size_pixels, second.column_offset + second.size_pixels)
        - max(first.column_offset, second.column_offset),
    )
    overlap_height = max(
        0,
        min(first.row_offset + first.size_pixels, second.row_offset + second.size_pixels)
        - max(first.row_offset, second.row_offset),
    )
    intersection = overlap_width * overlap_height
    union = first.size_pixels**2 + second.size_pixels**2 - intersection
    return intersection / union


def deduplicate_ranked(
    ranked: tuple[PrivateScoredWindow, ...],
) -> tuple[PrivateScoredWindow, ...]:
    """Deterministic non-maximum suppression using frozen distance and overlap rules."""
    retained: list[PrivateScoredWindow] = []
    for candidate in rank_windows(ranked):
        x, y = candidate.window.centre
        duplicate = False
        for representative in retained:
            other_x, other_y = representative.window.centre
            distance = math.hypot(x - other_x, y - other_y)
            if (
                distance < DEDUPLICATION_DISTANCE_M
                or _intersection_over_union(candidate.window, representative.window)
                > DEDUPLICATION_IOU
            ):
                duplicate = True
                break
        if not duplicate:
            retained.append(candidate)
    return tuple(retained)


def _hash_rank(item: PrivateScoredWindow) -> str:
    return hashlib.sha256(f"{REVIEW_SAMPLE_SEED}:{item.window.private_token}".encode()).hexdigest()


def select_review_queues(
    representatives: tuple[PrivateScoredWindow, ...],
) -> QueueSelection:
    """Select frozen high, medium, and score-blinded reference review queues."""
    if not representatives:
        raise ValueError("review queues require at least one deduplicated window")
    ranked = rank_windows(representatives)
    values = np.asarray([item.model_score for item in ranked])
    high_cutoff = float(np.quantile(values, HIGH_PERCENTILE, method="linear"))
    medium_lower, medium_upper = np.quantile(values, MEDIUM_PERCENTILE_RANGE, method="linear")
    high = tuple(item for item in ranked if item.model_score >= high_cutoff)[:QUEUE_LIMIT]
    high_tokens = {item.window.private_token for item in high}
    medium_pool = [
        item
        for item in ranked
        if float(medium_lower) <= item.model_score <= float(medium_upper)
        and item.window.private_token not in high_tokens
    ]
    medium = tuple(sorted(medium_pool, key=_hash_rank)[:QUEUE_LIMIT])
    excluded = high_tokens | {item.window.private_token for item in medium}
    reference = tuple(
        sorted(
            (item for item in ranked if item.window.private_token not in excluded),
            key=_hash_rank,
        )[:QUEUE_LIMIT]
    )
    return QueueSelection(high, medium, reference)


def safe_public_summary(
    *,
    total_windows: int,
    valid_scores: np.ndarray,
    rejected_windows: int,
    no_data_windows: int,
    representative_count: int,
    queues: QueueSelection,
    model_state_checksum: str,
) -> dict[str, Any]:
    values = np.asarray(valid_scores, dtype=np.float64)
    if total_windows < 0 or rejected_windows < 0 or no_data_windows < 0:
        raise ValueError("window counts cannot be negative")
    if values.ndim != 1 or not np.isfinite(values).all():
        raise ValueError("public summary requires finite aggregate score values")
    payload: dict[str, Any] = {
        "semantics": "terrain_similarity_model_score_not_archaeological_probability",
        "total_windows": total_windows,
        "valid_windows": int(values.size),
        "rejected_windows": rejected_windows,
        "no_data_windows": no_data_windows,
        "deduplicated_representatives": representative_count,
        "score_distribution": {
            "minimum": float(values.min()) if values.size else None,
            "q25": float(np.quantile(values, 0.25)) if values.size else None,
            "median": float(np.quantile(values, 0.5)) if values.size else None,
            "q75": float(np.quantile(values, 0.75)) if values.size else None,
            "maximum": float(values.max()) if values.size else None,
        },
        "review_queue_counts": {
            "highest_score": len(queues.high),
            "medium_score_diagnostic": len(queues.medium),
            "random_reference": len(queues.reference),
        },
        "model_state_sha256": model_state_checksum,
        "privacy": {
            "aggregate_only": True,
            "exact_locations_written": False,
            "candidate_identifiers_written": False,
            "georeferenced_outputs_written": False,
        },
    }
    assert_coordinate_safe_mapping(payload)
    return payload


def write_private_candidate_receipt(
    project_root: Path, destination: str | Path, payload: dict[str, Any]
) -> Path:
    path = ensure_private_output(project_root, destination)
    verify_git_ignored(project_root, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def read_modelling_index_labels(path: Path) -> tuple[int, ...]:
    """Small auditable label-only reader used by synthetic and source-boundary tests."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    labels = []
    for row in rows:
        if row["class_label"] == POSITIVE_LABEL:
            labels.append(1)
        elif row["class_label"] == BACKGROUND_LABEL:
            labels.append(0)
        else:
            raise ValueError("unsupported modelling-index label")
    return tuple(labels)


def private_scored_window_payload(item: PrivateScoredWindow) -> dict[str, Any]:
    """Serialize one score only for an ignored private receipt."""
    return {"window": asdict(item.window), "model_score": item.model_score}
