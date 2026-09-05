"""Strict, coordinate-private GeoTIFF loading for reusable inference plumbing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import RasterioIOError

from archaeoai.inference_system.contracts import E001_TERRAIN_INPUT, TerrainInputMetadata
from archaeoai.inference_system.single_patch import (
    SinglePatchFeatures,
    TerrainPatch,
    transform_single_patch,
)


class GeoTIFFErrorCode(StrEnum):
    """Bounded reasons that never contain caller-controlled path or metadata text."""

    FILE_UNAVAILABLE = "FILE_UNAVAILABLE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    RASTER_UNREADABLE = "RASTER_UNREADABLE"
    NONCANONICAL_INPUT = "NONCANONICAL_INPUT"


class GeoTIFFValidationError(ValueError):
    """A safe GeoTIFF failure whose original exception remains private."""

    def __init__(self, code: GeoTIFFErrorCode):
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class CanonicalGeoTIFF:
    """Private in-memory patch plus facts allowed in coordinate-free reports."""

    features: SinglePatchFeatures = field(repr=False)
    width: int
    height: int
    band_count: int
    dtype: str
    nodata_fraction: float


def resolve_local_geotiff(raw_path: str | Path) -> Path:
    """Resolve one local GeoTIFF without including its value in an exception."""
    try:
        source = Path(raw_path).resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise GeoTIFFValidationError(GeoTIFFErrorCode.FILE_UNAVAILABLE) from exc
    if not source.is_file():
        raise GeoTIFFValidationError(GeoTIFFErrorCode.FILE_UNAVAILABLE)
    if source.suffix.casefold() not in {".tif", ".tiff"}:
        raise GeoTIFFValidationError(GeoTIFFErrorCode.UNSUPPORTED_FORMAT)
    return source


def load_canonical_geotiff(path: str | Path) -> CanonicalGeoTIFF:
    """Read one canonical GeoTIFF without retaining spatial metadata in output."""
    source = resolve_local_geotiff(path)
    try:
        with rasterio.open(source) as dataset:
            if dataset.driver != "GTiff":
                raise GeoTIFFValidationError(GeoTIFFErrorCode.UNSUPPORTED_FORMAT)
            crs = dataset.crs.to_string() if dataset.crs is not None else None
            resolution = (abs(float(dataset.res[0])), abs(float(dataset.res[1])))
            preliminary = TerrainInputMetadata(
                crs=crs,
                width=dataset.width,
                height=dataset.height,
                resolution_m=resolution,
                band_count=dataset.count,
                nodata_fraction=0.0,
            )
            E001_TERRAIN_INPUT.validate(preliminary)
            band = dataset.read(1, masked=True)
            elevation = np.asarray(band.data)
            mask = np.ma.getmaskarray(band)
            dtype = str(dataset.dtypes[0])
    except GeoTIFFValidationError:
        raise
    except (RasterioIOError, OSError) as exc:
        raise GeoTIFFValidationError(GeoTIFFErrorCode.RASTER_UNREADABLE) from exc
    except (TypeError, ValueError) as exc:
        raise GeoTIFFValidationError(GeoTIFFErrorCode.NONCANONICAL_INPUT) from exc

    nodata_fraction = float(mask.mean())
    metadata = TerrainInputMetadata(
        crs=crs,
        width=preliminary.width,
        height=preliminary.height,
        resolution_m=resolution,
        band_count=preliminary.band_count,
        nodata_fraction=nodata_fraction,
    )
    try:
        features = transform_single_patch(TerrainPatch(elevation, mask, metadata))
    except (TypeError, ValueError) as exc:
        raise GeoTIFFValidationError(GeoTIFFErrorCode.NONCANONICAL_INPUT) from exc
    return CanonicalGeoTIFF(
        features=features,
        width=metadata.width,
        height=metadata.height,
        band_count=metadata.band_count,
        dtype=dtype,
        nodata_fraction=nodata_fraction,
    )


__all__ = [
    "CanonicalGeoTIFF",
    "GeoTIFFErrorCode",
    "GeoTIFFValidationError",
    "load_canonical_geotiff",
    "resolve_local_geotiff",
]
