"""Small deterministic GeoTIFF reader, mosaic, and E001 patch extractor."""

from __future__ import annotations

import hashlib
from contextlib import ExitStack
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from affine import Affine
from rasterio.merge import merge
from rasterio.transform import from_origin

from archaeoai.terrain.patches import Bounds, patch_bounds
from archaeoai.terrain.validation import (
    PatchQa,
    RasterMetadata,
    TerrainReason,
    TerrainValidationError,
    evaluate_patch,
    inspect_dataset,
    validate_raster_metadata,
)


@dataclass(frozen=True, slots=True)
class TerrainPatch:
    data: np.ndarray
    mask: np.ndarray
    transform: Affine
    crs: str
    bounds: Bounds
    source_paths: tuple[Path, ...]
    qa: PatchQa


def _safe_raster_path(path: str | Path) -> Path:
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"terrain source is not a local file: {resolved}")
    if resolved.suffix.casefold() not in {".tif", ".tiff"}:
        raise ValueError(f"terrain source must be a GeoTIFF: {resolved}")
    return resolved


def read_raster_metadata(path: str | Path) -> RasterMetadata:
    source = _safe_raster_path(path)
    with rasterio.open(source) as dataset:
        return inspect_dataset(dataset)


def sha256_file(path: str | Path, *, chunk_size: int = 1024 * 1024) -> str:
    source = _safe_raster_path(path)
    digest = hashlib.sha256()
    with source.open("rb") as file:
        while chunk := file.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def extract_patch(
    source_paths: list[str | Path] | tuple[str | Path, ...],
    *,
    centre: tuple[float, float],
    patch_size_m: float = 128.0,
    resolution_m: float = 1.0,
    expected_crs: str = "EPSG:27700",
    max_nodata_fraction: float = 0.2,
) -> TerrainPatch:
    """Mosaic only supplied local sources and extract one deterministic patch."""
    if not source_paths:
        raise TerrainValidationError(TerrainReason.MISSING_COVERAGE, "no source rasters supplied")
    paths = tuple(sorted({_safe_raster_path(path) for path in source_paths}, key=str))
    bounds = patch_bounds(centre, patch_size_m=patch_size_m, resolution_m=resolution_m)
    expected_pixels = round(patch_size_m / resolution_m)
    expected_shape = (expected_pixels, expected_pixels)
    expected_transform = from_origin(bounds.left, bounds.top, resolution_m, resolution_m)

    with ExitStack() as stack:
        datasets = [stack.enter_context(rasterio.open(path)) for path in paths]
        for dataset in datasets:
            validate_raster_metadata(
                inspect_dataset(dataset),
                expected_crs=expected_crs,
                expected_resolution_m=resolution_m,
            )
        mosaic, transform = merge(
            datasets,
            bounds=bounds.as_tuple(),
            res=(resolution_m, resolution_m),
            nodata=np.nan,
            dtype="float32",
            masked=True,
            method="first",
        )

    band = np.ma.asarray(mosaic[0])
    data = np.asarray(band.filled(np.nan), dtype=np.float32)
    mask = np.ma.getmaskarray(band) | ~np.isfinite(data)
    if not transform.almost_equals(expected_transform):
        raise TerrainValidationError(
            TerrainReason.BOUNDARY_MISMATCH,
            f"expected transform {expected_transform}, got {transform}",
        )
    qa = evaluate_patch(
        data,
        mask,
        expected_shape=expected_shape,
        max_nodata_fraction=max_nodata_fraction,
    )
    if not qa.passed:
        raise TerrainValidationError(qa.reasons, "terrain patch failed automatic QA")
    return TerrainPatch(
        data=data,
        mask=mask,
        transform=transform,
        crs=expected_crs,
        bounds=bounds,
        source_paths=paths,
        qa=qa,
    )
