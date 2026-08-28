"""Bounded, coordinate-controlled terrain processing for E001."""

from archaeoai.terrain.patches import Bounds, GridTile, patch_bounds, required_grid_tiles
from archaeoai.terrain.raster import TerrainPatch, extract_patch, read_raster_metadata
from archaeoai.terrain.representations import terrain_representations
from archaeoai.terrain.validation import (
    PatchQa,
    RasterMetadata,
    TerrainReason,
    TerrainValidationError,
)

__all__ = [
    "Bounds",
    "GridTile",
    "PatchQa",
    "RasterMetadata",
    "TerrainPatch",
    "TerrainReason",
    "TerrainValidationError",
    "extract_patch",
    "patch_bounds",
    "read_raster_metadata",
    "required_grid_tiles",
    "terrain_representations",
]
