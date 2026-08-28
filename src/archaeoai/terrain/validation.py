"""Raster metadata and patch-quality validation with explicit reason codes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

import numpy as np
from pyproj import CRS

from archaeoai.terrain.patches import Bounds

if TYPE_CHECKING:
    from rasterio.io import DatasetReader


class TerrainReason(StrEnum):
    CRS_MISMATCH = "crs_mismatch"
    RESOLUTION_MISMATCH = "resolution_mismatch"
    DIMENSIONS_MISMATCH = "dimensions_mismatch"
    NONFINITE_VALUES = "nonfinite_values"
    NODATA_EXCESS = "nodata_excess"
    MISSING_COVERAGE = "missing_coverage"
    ELEVATION_RANGE = "elevation_range"
    SOURCE_METADATA_MISSING = "source_metadata_missing"
    BOUNDARY_MISMATCH = "boundary_mismatch"


class TerrainValidationError(ValueError):
    """Reject unsafe or scientifically invalid terrain with stable codes."""

    def __init__(self, reasons: TerrainReason | tuple[TerrainReason, ...], message: str):
        self.reasons = (reasons,) if isinstance(reasons, TerrainReason) else reasons
        super().__init__(f"{','.join(self.reasons)}: {message}")


@dataclass(frozen=True, slots=True)
class RasterMetadata:
    width: int
    height: int
    crs: str | None
    resolution_m: tuple[float, float]
    nodata: float | None
    bounds: Bounds
    transform: tuple[float, ...]
    dtype: str
    band_count: int


@dataclass(frozen=True, slots=True)
class PatchQa:
    passed: bool
    reasons: tuple[TerrainReason, ...]
    nodata_fraction: float
    minimum_elevation_m: float | None
    maximum_elevation_m: float | None


def inspect_dataset(dataset: DatasetReader) -> RasterMetadata:
    return RasterMetadata(
        width=dataset.width,
        height=dataset.height,
        crs=dataset.crs.to_string() if dataset.crs else None,
        resolution_m=(abs(float(dataset.res[0])), abs(float(dataset.res[1]))),
        nodata=None if dataset.nodata is None else float(dataset.nodata),
        bounds=Bounds(*map(float, dataset.bounds)),
        transform=tuple(float(value) for value in dataset.transform),
        dtype=str(dataset.dtypes[0]) if dataset.count else "",
        band_count=dataset.count,
    )


def validate_raster_metadata(
    metadata: RasterMetadata,
    *,
    expected_crs: str = "EPSG:27700",
    expected_resolution_m: float = 1.0,
    tolerance: float = 1e-6,
) -> None:
    if metadata.crs is None or CRS.from_user_input(metadata.crs) != CRS.from_user_input(
        expected_crs
    ):
        raise TerrainValidationError(
            TerrainReason.CRS_MISMATCH, f"expected {expected_crs}, got {metadata.crs}"
        )
    if any(
        not math.isclose(value, expected_resolution_m, abs_tol=tolerance)
        for value in metadata.resolution_m
    ):
        raise TerrainValidationError(
            TerrainReason.RESOLUTION_MISMATCH,
            f"expected {expected_resolution_m} m, got {metadata.resolution_m}",
        )
    if metadata.band_count != 1 or not metadata.dtype:
        raise TerrainValidationError(
            TerrainReason.SOURCE_METADATA_MISSING,
            "terrain source must contain exactly one typed elevation band",
        )


def evaluate_patch(
    data: np.ndarray,
    mask: np.ndarray,
    *,
    expected_shape: tuple[int, int],
    max_nodata_fraction: float,
    minimum_allowed_m: float = -500.0,
    maximum_allowed_m: float = 2000.0,
) -> PatchQa:
    if data.ndim != 2 or mask.shape != data.shape:
        raise ValueError("data and mask must be matching two-dimensional arrays")
    reasons: list[TerrainReason] = []
    if data.shape != expected_shape:
        reasons.append(TerrainReason.DIMENSIONS_MISMATCH)

    effective_mask = np.asarray(mask, dtype=bool)
    unexpected_nonfinite = ~np.isfinite(data) & ~effective_mask
    if unexpected_nonfinite.any():
        reasons.append(TerrainReason.NONFINITE_VALUES)
    effective_mask = effective_mask | ~np.isfinite(data)
    nodata_fraction = float(effective_mask.mean())
    if nodata_fraction == 1.0:
        reasons.append(TerrainReason.MISSING_COVERAGE)
    elif nodata_fraction > max_nodata_fraction:
        reasons.append(TerrainReason.NODATA_EXCESS)

    valid = data[~effective_mask]
    minimum = float(valid.min()) if valid.size else None
    maximum = float(valid.max()) if valid.size else None
    if (
        minimum is not None
        and maximum is not None
        and (minimum < minimum_allowed_m or maximum > maximum_allowed_m)
    ):
        reasons.append(TerrainReason.ELEVATION_RANGE)

    unique_reasons = tuple(dict.fromkeys(reasons))
    return PatchQa(
        passed=not unique_reasons,
        reasons=unique_reasons,
        nodata_fraction=nodata_fraction,
        minimum_elevation_m=minimum,
        maximum_elevation_m=maximum,
    )
