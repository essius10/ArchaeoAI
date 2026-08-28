"""Resumable positive-terrain cache and representation integrity helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from archaeoai.terrain.acquisition import PrivateSiteLocation
from archaeoai.terrain.privacy import ensure_private_output, verify_git_ignored
from archaeoai.terrain.raster import TerrainPatch, extract_patch, sha256_file
from archaeoai.terrain.representations import terrain_representations

REPRESENTATION_NAMES = (
    "elevation_normalized",
    "slope_degrees",
    "hillshade_315_45",
    "local_relief_r16m",
)
ARCHIVE_NAMES = ("elevation", "mask", *REPRESENTATION_NAMES)


@dataclass(frozen=True, slots=True)
class RepresentationQa:
    passed: bool
    reasons: tuple[str, ...]
    digest: str


@dataclass(frozen=True, slots=True)
class CacheInspection:
    status: str
    reasons: tuple[str, ...]
    raw_sha256: str
    patch_sha256: str
    processed_sha256: str
    patch: TerrainPatch | None
    representations: dict[str, np.ndarray] | None


def sha256_path(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def terrain_content_digest(data: np.ndarray, mask: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(data.astype("<f4")).tobytes())
    digest.update(np.ascontiguousarray(mask.astype(np.uint8)).tobytes())
    return digest.hexdigest()


def representation_digest(representations: dict[str, np.ndarray]) -> str:
    digest = hashlib.sha256()
    for name in REPRESENTATION_NAMES:
        digest.update(name.encode())
        values = np.asarray(representations[name], dtype="<f4")
        digest.update(np.ascontiguousarray(values).tobytes())
        digest.update(np.ascontiguousarray(~np.isfinite(values)).tobytes())
    return digest.hexdigest()


def _dilate_one_pixel(mask: np.ndarray) -> np.ndarray:
    padded = np.pad(mask, 1, constant_values=False)
    result = np.zeros_like(mask, dtype=bool)
    for row_offset in range(3):
        for column_offset in range(3):
            result |= padded[
                row_offset : row_offset + mask.shape[0],
                column_offset : column_offset + mask.shape[1],
            ]
    return result


def validate_representations(
    representations: dict[str, np.ndarray],
    *,
    source_mask: np.ndarray,
    expected_shape: tuple[int, int] = (128, 128),
    deterministic_reference: dict[str, np.ndarray] | None = None,
) -> RepresentationQa:
    reasons: list[str] = []
    if set(representations) != set(REPRESENTATION_NAMES):
        reasons.append("representation_set_incomplete")
        return RepresentationQa(False, tuple(reasons), "")
    if source_mask.shape != expected_shape:
        raise ValueError("source mask does not match the expected representation shape")

    dilated_mask = _dilate_one_pixel(np.asarray(source_mask, dtype=bool))
    for name in REPRESENTATION_NAMES:
        values = np.asarray(representations[name])
        if values.shape != expected_shape:
            reasons.append(f"{name}:shape_mismatch")
            continue
        nonfinite = ~np.isfinite(values)
        if np.any(source_mask & ~nonfinite):
            reasons.append(f"{name}:nodata_not_propagated")
        allowed_nonfinite = (
            dilated_mask if name in {"slope_degrees", "hillshade_315_45"} else source_mask
        )
        if np.any(nonfinite & ~allowed_nonfinite):
            reasons.append(f"{name}:unexpected_nan")
        finite = values[np.isfinite(values)]
        if not finite.size:
            reasons.append(f"{name}:no_finite_values")
            continue
        if name == "slope_degrees" and (finite.min() < 0 or finite.max() > 90):
            reasons.append("slope_degrees:range")
        if name == "hillshade_315_45" and (finite.min() < 0 or finite.max() > 1):
            reasons.append("hillshade_315_45:range")
        if name == "elevation_normalized" and abs(float(np.median(finite))) > 1e-4:
            reasons.append("elevation_normalized:median")
        if deterministic_reference is not None:
            reference = deterministic_reference.get(name)
            if reference is None or not np.array_equal(values, reference, equal_nan=True):
                reasons.append(f"{name}:deterministic_mismatch")
    unique_reasons = tuple(dict.fromkeys(reasons))
    return RepresentationQa(
        passed=not unique_reasons,
        reasons=unique_reasons,
        digest=representation_digest(representations) if not unique_reasons else "",
    )


def load_processed_archive(path: Path) -> tuple[np.ndarray, np.ndarray, dict[str, np.ndarray]]:
    with np.load(path) as archive:
        if set(archive.files) != set(ARCHIVE_NAMES):
            raise ValueError("representation_set_incomplete")
        elevation = np.asarray(archive["elevation"], dtype=np.float32)
        mask = np.asarray(archive["mask"], dtype=bool)
        representations = {
            name: np.asarray(archive[name], dtype=np.float32) for name in REPRESENTATION_NAMES
        }
    return elevation, mask, representations


def write_processed_archive(
    path: Path,
    *,
    patch: TerrainPatch,
    representations: dict[str, np.ndarray],
    project_root: Path,
) -> str:
    destination = ensure_private_output(project_root, path)
    verify_git_ignored(project_root, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f"{destination.stem}.partial.npz")
    np.savez_compressed(
        temporary,
        elevation=patch.data,
        mask=patch.mask,
        **representations,
    )
    elevation, mask, loaded = load_processed_archive(temporary)
    if not np.array_equal(elevation, patch.data, equal_nan=True) or not np.array_equal(
        mask, patch.mask
    ):
        raise ValueError("processed_archive_source_mismatch")
    qa = validate_representations(
        loaded,
        source_mask=patch.mask,
        expected_shape=patch.data.shape,
        deterministic_reference=representations,
    )
    if not qa.passed:
        raise ValueError(",".join(qa.reasons))
    temporary.replace(destination)
    return sha256_path(destination)


def inspect_cached_artifacts(
    *,
    raw_path: Path,
    processed_path: Path,
    location: PrivateSiteLocation,
    expected_raw_sha256: str | None = None,
) -> CacheInspection:
    if not raw_path.is_file():
        return CacheInspection("raw_missing", ("raw_missing",), "", "", "", None, None)
    try:
        raw_sha256 = sha256_file(raw_path)
    except (OSError, ValueError):
        return CacheInspection("raw_invalid", ("raw_unreadable",), "", "", "", None, None)
    if expected_raw_sha256 and raw_sha256 != expected_raw_sha256:
        return CacheInspection(
            "raw_invalid", ("raw_checksum_mismatch",), raw_sha256, "", "", None, None
        )
    try:
        patch = extract_patch(
            [raw_path],
            centre=(location.easting, location.northing),
            patch_size_m=128,
            resolution_m=1,
            max_nodata_fraction=0.2,
        )
    except (OSError, ValueError):
        return CacheInspection(
            "raw_invalid", ("raw_raster_qa_failed",), raw_sha256, "", "", None, None
        )
    patch_sha256 = terrain_content_digest(patch.data, patch.mask)
    fresh = terrain_representations(
        patch.data,
        resolution_m=1,
        mask=patch.mask,
        local_relief_radius_m=16,
    )
    fresh_qa = validate_representations(
        fresh,
        source_mask=patch.mask,
        expected_shape=patch.data.shape,
    )
    if not fresh_qa.passed:
        return CacheInspection(
            "representation_invalid",
            fresh_qa.reasons,
            raw_sha256,
            patch_sha256,
            "",
            patch,
            fresh,
        )
    if not processed_path.is_file():
        return CacheInspection(
            "processed_missing",
            ("processed_missing",),
            raw_sha256,
            patch_sha256,
            "",
            patch,
            fresh,
        )
    try:
        elevation, mask, cached = load_processed_archive(processed_path)
        if not np.array_equal(elevation, patch.data, equal_nan=True) or not np.array_equal(
            mask, patch.mask
        ):
            raise ValueError("processed_archive_source_mismatch")
        cached_qa = validate_representations(
            cached,
            source_mask=patch.mask,
            expected_shape=patch.data.shape,
            deterministic_reference=fresh,
        )
        if not cached_qa.passed:
            raise ValueError(",".join(cached_qa.reasons))
        processed_sha256 = sha256_path(processed_path)
    except (OSError, ValueError, KeyError):
        return CacheInspection(
            "processed_invalid",
            ("processed_archive_qa_failed",),
            raw_sha256,
            patch_sha256,
            "",
            patch,
            fresh,
        )
    return CacheInspection(
        "valid",
        (),
        raw_sha256,
        patch_sha256,
        processed_sha256,
        patch,
        cached,
    )


def quarantine_artifact(path: Path, *, reason: str, rejected_root: Path) -> Path:
    if not path.exists():
        raise FileNotFoundError(path)
    rejected_root.mkdir(parents=True, exist_ok=True)
    digest = sha256_path(path)[:12]
    destination = rejected_root / f"{path.stem}.{reason}.{digest}{path.suffix}"
    if destination.exists():
        sequence = 2
        while destination.exists():
            destination = rejected_root / (f"{path.stem}.{reason}.{digest}.{sequence}{path.suffix}")
            sequence += 1
    path.replace(destination)
    return destination
