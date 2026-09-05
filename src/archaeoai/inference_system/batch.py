"""Bounded, deterministic, no-retention batch feature orchestration."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path, PurePosixPath

from archaeoai.inference import FEATURE_COUNT, REPRESENTATION_CHANNELS
from archaeoai.inference_system.geotiff import (
    GeoTIFFValidationError,
    load_canonical_geotiff,
)

BATCH_MANIFEST_SCHEMA_VERSION = "archaeoai-batch-manifest-v1"
BATCH_RESULT_SCHEMA_VERSION = "archaeoai-batch-result-v1"
MAX_BATCH_ITEMS = 64
MAX_MANIFEST_BYTES = 64 * 1024
MAX_SINGLE_FILE_BYTES = 2 * 1024 * 1024
MAX_CUMULATIVE_INPUT_BYTES = 16 * 1024 * 1024
MAX_TERRAIN_REFERENCE_CHARS = 256
ITEM_ID_PATTERN = re.compile(r"item-[0-9]{4}\Z")

BATCH_PUBLIC_FIELDS = frozenset(
    {
        "schema_version",
        "command",
        "status",
        "manifest_label",
        "processing_order",
        "total_items",
        "accepted_items",
        "invalid_items",
        "feature_preparation_succeeded",
        "processing_failures",
        "feature_count",
        "feature_dtype",
        "representation_order",
        "model_execution",
        "retention_policy",
        "temporary_artifacts_retained",
        "item_results",
    }
)
BATCH_ITEM_PUBLIC_FIELDS = frozenset(
    {
        "item_id",
        "status",
        "feature_preparation",
        "model_execution",
        "error_code",
    }
)


class BatchManifestErrorCode(StrEnum):
    """Stable admission failures with no caller-controlled text."""

    MANIFEST_UNAVAILABLE = "MANIFEST_UNAVAILABLE"
    MANIFEST_TOO_LARGE = "MANIFEST_TOO_LARGE"
    MALFORMED_MANIFEST = "MALFORMED_MANIFEST"
    MANIFEST_SCHEMA_MISMATCH = "MANIFEST_SCHEMA_MISMATCH"
    ITEM_LIMIT_EXCEEDED = "ITEM_LIMIT_EXCEEDED"
    INVALID_ITEM = "INVALID_ITEM"
    DUPLICATE_ITEM_ID = "DUPLICATE_ITEM_ID"
    DUPLICATE_FILE_REFERENCE = "DUPLICATE_FILE_REFERENCE"
    DUPLICATE_FILE_CONTENT = "DUPLICATE_FILE_CONTENT"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    CUMULATIVE_SIZE_EXCEEDED = "CUMULATIVE_SIZE_EXCEEDED"
    PATH_ESCAPE = "PATH_ESCAPE"
    SYMLINK_NOT_ALLOWED = "SYMLINK_NOT_ALLOWED"


class BatchManifestError(ValueError):
    """A controlled manifest failure that never embeds private input values."""

    def __init__(self, code: BatchManifestErrorCode):
        self.code = code
        super().__init__(code.value)


class BatchProcessingError(RuntimeError):
    """An unexpected item-processing failure with private details suppressed."""


@dataclass(frozen=True, slots=True)
class BatchManifestItem:
    """One admitted private input bound to an opaque item ID and content digest."""

    item_id: str
    terrain_path: Path = field(repr=False)
    size_bytes: int = field(repr=False)
    content_sha256: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class BatchManifest:
    """An admitted batch in deterministic item-ID order."""

    input_root: Path = field(repr=False)
    items: tuple[BatchManifestItem, ...]


@dataclass(frozen=True, slots=True)
class BatchItemResult:
    """Bounded per-item operational state; no path, feature, or score is retained."""

    item_id: str
    status: str
    feature_preparation: str
    model_execution: str
    error_code: str

    def to_public_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "item_id": self.item_id,
            "status": self.status,
            "feature_preparation": self.feature_preparation,
            "model_execution": self.model_execution,
            "error_code": self.error_code,
        }
        if set(payload) != BATCH_ITEM_PUBLIC_FIELDS:
            raise RuntimeError("batch item public-field contract changed")
        return payload


@dataclass(frozen=True, slots=True)
class BatchRunResult:
    """Aggregate batch state with bounded opaque per-item statuses."""

    items: tuple[BatchItemResult, ...]

    @property
    def accepted_items(self) -> int:
        return sum(item.status == "FEATURES_READY" for item in self.items)

    @property
    def invalid_items(self) -> int:
        return sum(item.status == "INVALID_INPUT" for item in self.items)

    def to_public_dict(self) -> dict[str, object]:
        invalid = self.invalid_items
        payload: dict[str, object] = {
            "schema_version": BATCH_RESULT_SCHEMA_VERSION,
            "command": "batch-features",
            "status": "COMPLETE" if invalid == 0 else "COMPLETE_WITH_INVALID_ITEMS",
            "manifest_label": "local_batch_manifest",
            "processing_order": "ITEM_ID_ASCENDING",
            "total_items": len(self.items),
            "accepted_items": self.accepted_items,
            "invalid_items": invalid,
            "feature_preparation_succeeded": self.accepted_items,
            "processing_failures": 0,
            "feature_count": FEATURE_COUNT,
            "feature_dtype": "float32",
            "representation_order": list(REPRESENTATION_CHANNELS),
            "model_execution": "NOT_PERFORMED",
            "retention_policy": "NO_INPUT_RETENTION",
            "temporary_artifacts_retained": False,
            "item_results": [item.to_public_dict() for item in self.items],
        }
        if set(payload) != BATCH_PUBLIC_FIELDS:
            raise RuntimeError("batch public-field contract changed")
        return payload


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _manifest_source(raw_path: str | Path) -> Path:
    try:
        unresolved = Path(raw_path)
        if unresolved.is_symlink():
            raise BatchManifestError(BatchManifestErrorCode.SYMLINK_NOT_ALLOWED)
        source = unresolved.resolve(strict=True)
    except BatchManifestError:
        raise
    except (OSError, RuntimeError, ValueError) as exc:
        raise BatchManifestError(BatchManifestErrorCode.MANIFEST_UNAVAILABLE) from exc
    if not source.is_file() or source.suffix.casefold() != ".json":
        raise BatchManifestError(BatchManifestErrorCode.MANIFEST_UNAVAILABLE)
    try:
        size = source.stat().st_size
    except OSError as exc:
        raise BatchManifestError(BatchManifestErrorCode.MANIFEST_UNAVAILABLE) from exc
    if size > MAX_MANIFEST_BYTES:
        raise BatchManifestError(BatchManifestErrorCode.MANIFEST_TOO_LARGE)
    return source


def _safe_item_path(root: Path, reference: object) -> Path:
    if (
        not isinstance(reference, str)
        or not reference
        or len(reference) > MAX_TERRAIN_REFERENCE_CHARS
    ):
        raise BatchManifestError(BatchManifestErrorCode.INVALID_ITEM)
    if "\\" in reference or ":" in reference or any(ord(char) < 32 for char in reference):
        raise BatchManifestError(BatchManifestErrorCode.PATH_ESCAPE)
    pure = PurePosixPath(reference)
    if pure.is_absolute() or any(part in {"", ".", ".."} for part in pure.parts):
        raise BatchManifestError(BatchManifestErrorCode.PATH_ESCAPE)
    if pure.suffix.casefold() not in {".tif", ".tiff"}:
        raise BatchManifestError(BatchManifestErrorCode.INVALID_ITEM)

    unresolved = root.joinpath(*pure.parts)
    current = root
    try:
        for part in pure.parts:
            current = current / part
            if current.is_symlink():
                raise BatchManifestError(BatchManifestErrorCode.SYMLINK_NOT_ALLOWED)
        candidate = unresolved.resolve(strict=True)
        candidate.relative_to(root)
    except BatchManifestError:
        raise
    except ValueError as exc:
        raise BatchManifestError(BatchManifestErrorCode.PATH_ESCAPE) from exc
    except (OSError, RuntimeError) as exc:
        raise BatchManifestError(BatchManifestErrorCode.INVALID_ITEM) from exc
    if not candidate.is_file():
        raise BatchManifestError(BatchManifestErrorCode.INVALID_ITEM)
    return candidate


def load_batch_manifest(path: str | Path) -> BatchManifest:
    """Validate and admit one strict JSON manifest before terrain processing begins."""
    source = _manifest_source(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=_strict_object)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise BatchManifestError(BatchManifestErrorCode.MALFORMED_MANIFEST) from exc
    if not isinstance(payload, dict) or set(payload) != {"schema_version", "items"}:
        raise BatchManifestError(BatchManifestErrorCode.MANIFEST_SCHEMA_MISMATCH)
    if payload["schema_version"] != BATCH_MANIFEST_SCHEMA_VERSION:
        raise BatchManifestError(BatchManifestErrorCode.MANIFEST_SCHEMA_MISMATCH)
    raw_items = payload["items"]
    if not isinstance(raw_items, list) or not raw_items:
        raise BatchManifestError(BatchManifestErrorCode.MANIFEST_SCHEMA_MISMATCH)
    if len(raw_items) > MAX_BATCH_ITEMS:
        raise BatchManifestError(BatchManifestErrorCode.ITEM_LIMIT_EXCEEDED)

    root = source.parent.resolve()
    admitted: list[BatchManifestItem] = []
    identifiers: set[str] = set()
    references: set[Path] = set()
    content_digests: set[str] = set()
    cumulative_size = 0
    for raw_item in raw_items:
        if not isinstance(raw_item, dict) or set(raw_item) != {"item_id", "terrain"}:
            raise BatchManifestError(BatchManifestErrorCode.INVALID_ITEM)
        item_id = raw_item["item_id"]
        if not isinstance(item_id, str) or ITEM_ID_PATTERN.fullmatch(item_id) is None:
            raise BatchManifestError(BatchManifestErrorCode.INVALID_ITEM)
        if item_id in identifiers:
            raise BatchManifestError(BatchManifestErrorCode.DUPLICATE_ITEM_ID)
        identifiers.add(item_id)

        terrain_path = _safe_item_path(root, raw_item["terrain"])
        if terrain_path in references:
            raise BatchManifestError(BatchManifestErrorCode.DUPLICATE_FILE_REFERENCE)
        references.add(terrain_path)
        try:
            size = terrain_path.stat().st_size
        except OSError as exc:
            raise BatchManifestError(BatchManifestErrorCode.INVALID_ITEM) from exc
        if size > MAX_SINGLE_FILE_BYTES:
            raise BatchManifestError(BatchManifestErrorCode.FILE_TOO_LARGE)
        cumulative_size += size
        if cumulative_size > MAX_CUMULATIVE_INPUT_BYTES:
            raise BatchManifestError(BatchManifestErrorCode.CUMULATIVE_SIZE_EXCEEDED)
        try:
            digest = _file_sha256(terrain_path)
        except OSError as exc:
            raise BatchManifestError(BatchManifestErrorCode.INVALID_ITEM) from exc
        if digest in content_digests:
            raise BatchManifestError(BatchManifestErrorCode.DUPLICATE_FILE_CONTENT)
        content_digests.add(digest)
        admitted.append(BatchManifestItem(item_id, terrain_path, size, digest))

    return BatchManifest(
        input_root=root,
        items=tuple(sorted(admitted, key=lambda item: item.item_id)),
    )


def _item_unchanged(manifest: BatchManifest, item: BatchManifestItem) -> bool:
    try:
        resolved = item.terrain_path.resolve(strict=True)
        resolved.relative_to(manifest.input_root)
        current = manifest.input_root
        for part in resolved.relative_to(manifest.input_root).parts:
            current = current / part
            if current.is_symlink():
                return False
        return (
            resolved == item.terrain_path
            and resolved.is_file()
            and resolved.stat().st_size == item.size_bytes
            and _file_sha256(resolved) == item.content_sha256
        )
    except (OSError, RuntimeError, ValueError):
        return False


def run_feature_batch(
    manifest: BatchManifest,
) -> BatchRunResult:
    """Process admitted items sequentially, retaining no terrain or feature arrays."""
    if not isinstance(manifest, BatchManifest):
        raise TypeError("manifest must be a BatchManifest")
    results: list[BatchItemResult] = []
    for item in manifest.items:
        if not _item_unchanged(manifest, item):
            results.append(
                BatchItemResult(
                    item.item_id,
                    "INVALID_INPUT",
                    "FAILED",
                    "NOT_PERFORMED",
                    "INPUT_CHANGED_AFTER_ADMISSION",
                )
            )
            continue
        try:
            load_canonical_geotiff(item.terrain_path)
        except GeoTIFFValidationError as exc:
            results.append(
                BatchItemResult(
                    item.item_id,
                    "INVALID_INPUT",
                    "FAILED",
                    "NOT_PERFORMED",
                    exc.code.value,
                )
            )
            continue
        except Exception as exc:
            raise BatchProcessingError("batch item processing failed safely") from exc
        results.append(
            BatchItemResult(
                item.item_id,
                "FEATURES_READY",
                "SUCCEEDED",
                "NOT_PERFORMED",
                "NONE",
            )
        )
    return BatchRunResult(items=tuple(results))


__all__ = [
    "BATCH_ITEM_PUBLIC_FIELDS",
    "BATCH_MANIFEST_SCHEMA_VERSION",
    "BATCH_PUBLIC_FIELDS",
    "BATCH_RESULT_SCHEMA_VERSION",
    "ITEM_ID_PATTERN",
    "MAX_BATCH_ITEMS",
    "MAX_CUMULATIVE_INPUT_BYTES",
    "MAX_MANIFEST_BYTES",
    "MAX_SINGLE_FILE_BYTES",
    "BatchItemResult",
    "BatchManifest",
    "BatchManifestError",
    "BatchManifestErrorCode",
    "BatchManifestItem",
    "BatchProcessingError",
    "BatchRunResult",
    "load_batch_manifest",
    "run_feature_batch",
]
