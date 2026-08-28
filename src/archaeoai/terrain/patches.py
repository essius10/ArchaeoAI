"""Deterministic BNG patch bounds and provider-independent 5 km grid discovery."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Bounds:
    left: float
    bottom: float
    right: float
    top: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def height(self) -> float:
        return self.top - self.bottom

    def as_tuple(self) -> tuple[float, float, float, float]:
        return self.left, self.bottom, self.right, self.top


@dataclass(frozen=True, slots=True)
class GridTile:
    """A coordinate-free reference to one 5 km BNG source cell."""

    tile_id: str
    bounds: Bounds


def _snap_to_grid(value: float, resolution_m: float) -> float:
    return math.floor(value / resolution_m + 0.5) * resolution_m


def patch_bounds(
    centre: tuple[float, float], *, patch_size_m: float, resolution_m: float = 1.0
) -> Bounds:
    """Return pixel-aligned square bounds around a private BNG centre."""
    if patch_size_m <= 0 or resolution_m <= 0:
        raise ValueError("patch size and resolution must be positive")
    pixels = patch_size_m / resolution_m
    if not pixels.is_integer():
        raise ValueError("patch size must contain an integer number of pixels")
    x, y = centre
    if not math.isfinite(x) or not math.isfinite(y):
        raise ValueError("patch centre must contain finite BNG coordinates")
    snapped_x = _snap_to_grid(x, resolution_m)
    snapped_y = _snap_to_grid(y, resolution_m)
    half = patch_size_m / 2
    return Bounds(
        left=snapped_x - half,
        bottom=snapped_y - half,
        right=snapped_x + half,
        top=snapped_y + half,
    )


def required_grid_tiles(bounds: Bounds, *, tile_size_m: int = 5000) -> tuple[GridTile, ...]:
    """Discover every half-open BNG grid cell intersected by ``bounds``."""
    if tile_size_m <= 0:
        raise ValueError("tile_size_m must be positive")
    if bounds.width <= 0 or bounds.height <= 0:
        raise ValueError("bounds must have positive width and height")

    first_e = math.floor(bounds.left / tile_size_m)
    last_e = math.ceil(bounds.right / tile_size_m) - 1
    first_n = math.floor(bounds.bottom / tile_size_m)
    last_n = math.ceil(bounds.top / tile_size_m) - 1
    tiles = []
    for north_index in range(first_n, last_n + 1):
        for east_index in range(first_e, last_e + 1):
            left = east_index * tile_size_m
            bottom = north_index * tile_size_m
            tiles.append(
                GridTile(
                    tile_id=f"BNG5K_E{east_index:03d}_N{north_index:03d}",
                    bounds=Bounds(
                        left=left,
                        bottom=bottom,
                        right=left + tile_size_m,
                        top=bottom + tile_size_m,
                    ),
                )
            )
    return tuple(tiles)
