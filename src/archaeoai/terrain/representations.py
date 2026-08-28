"""Interpretable, non-learned E001 terrain representations."""

from __future__ import annotations

import math

import numpy as np


def _surface(data: np.ndarray, mask: np.ndarray | None) -> tuple[np.ndarray, np.ndarray]:
    values = np.asarray(data, dtype=np.float64)
    if values.ndim != 2:
        raise ValueError("terrain representation input must be two-dimensional")
    invalid = ~np.isfinite(values)
    if mask is not None:
        supplied_mask = np.asarray(mask, dtype=bool)
        if supplied_mask.shape != values.shape:
            raise ValueError("terrain data and mask shapes must match")
        invalid |= supplied_mask
    return np.where(invalid, np.nan, values), invalid


def normalize_elevation(data: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
    """Subtract the valid per-patch median; no cross-site statistic is learned."""
    surface, invalid = _surface(data, mask)
    if invalid.all():
        raise ValueError("cannot normalize a patch without valid elevation")
    normalized = surface - float(np.nanmedian(surface))
    normalized[invalid] = np.nan
    return normalized.astype(np.float32)


def slope_degrees(
    data: np.ndarray, *, resolution_m: float, mask: np.ndarray | None = None
) -> np.ndarray:
    """Return gradient magnitude as slope angle in degrees."""
    if resolution_m <= 0:
        raise ValueError("resolution_m must be positive")
    surface, invalid = _surface(data, mask)
    south_gradient, east_gradient = np.gradient(surface, resolution_m, resolution_m)
    north_gradient = -south_gradient
    slope = np.degrees(np.arctan(np.hypot(east_gradient, north_gradient)))
    slope[invalid] = np.nan
    return slope.astype(np.float32)


def hillshade(
    data: np.ndarray,
    *,
    resolution_m: float,
    azimuth_deg: float = 315.0,
    altitude_deg: float = 45.0,
    mask: np.ndarray | None = None,
) -> np.ndarray:
    """Return unit hillshade for a sun azimuth clockwise from north."""
    if resolution_m <= 0:
        raise ValueError("resolution_m must be positive")
    if not 0 <= azimuth_deg < 360 or not 0 < altitude_deg <= 90:
        raise ValueError("hillshade azimuth/altitude are outside valid ranges")
    surface, invalid = _surface(data, mask)
    south_gradient, east_gradient = np.gradient(surface, resolution_m, resolution_m)
    north_gradient = -south_gradient

    azimuth = math.radians(azimuth_deg)
    altitude = math.radians(altitude_deg)
    sun_east = math.cos(altitude) * math.sin(azimuth)
    sun_north = math.cos(altitude) * math.cos(azimuth)
    sun_up = math.sin(altitude)
    normal_length = np.sqrt(east_gradient**2 + north_gradient**2 + 1.0)
    illumination = (-east_gradient * sun_east - north_gradient * sun_north + sun_up) / normal_length
    illumination = np.clip(illumination, 0.0, 1.0)
    illumination[invalid] = np.nan
    return illumination.astype(np.float32)


def _box_mean(surface: np.ndarray, *, radius_pixels: int) -> np.ndarray:
    valid = np.isfinite(surface)
    values = np.where(valid, surface, 0.0)
    value_integral = np.pad(values, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    count_integral = np.pad(valid.astype(np.int64), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    rows, columns = surface.shape
    row = np.arange(rows)[:, None]
    column = np.arange(columns)[None, :]
    row_min = np.maximum(row - radius_pixels, 0)
    row_max = np.minimum(row + radius_pixels + 1, rows)
    column_min = np.maximum(column - radius_pixels, 0)
    column_max = np.minimum(column + radius_pixels + 1, columns)
    totals = (
        value_integral[row_max, column_max]
        - value_integral[row_min, column_max]
        - value_integral[row_max, column_min]
        + value_integral[row_min, column_min]
    )
    counts = (
        count_integral[row_max, column_max]
        - count_integral[row_min, column_max]
        - count_integral[row_max, column_min]
        + count_integral[row_min, column_min]
    )
    return np.divide(totals, counts, out=np.full_like(totals, np.nan), where=counts > 0)


def local_relief_model(
    data: np.ndarray, *, radius_pixels: int = 16, mask: np.ndarray | None = None
) -> np.ndarray:
    """Subtract a square-window local mean to emphasize small terrain residuals."""
    if radius_pixels < 1:
        raise ValueError("radius_pixels must be at least one")
    surface, invalid = _surface(data, mask)
    relief = surface - _box_mean(surface, radius_pixels=radius_pixels)
    relief[invalid] = np.nan
    return relief.astype(np.float32)


def terrain_representations(
    data: np.ndarray,
    *,
    resolution_m: float,
    mask: np.ndarray | None = None,
    local_relief_radius_m: float = 16.0,
    hillshade_azimuth_deg: float = 315.0,
    hillshade_altitude_deg: float = 45.0,
) -> dict[str, np.ndarray]:
    radius_pixels = round(local_relief_radius_m / resolution_m)
    if not math.isclose(radius_pixels * resolution_m, local_relief_radius_m):
        raise ValueError("local relief radius must be an integer number of pixels")
    return {
        "elevation_normalized": normalize_elevation(data, mask),
        "slope_degrees": slope_degrees(data, resolution_m=resolution_m, mask=mask),
        "hillshade_315_45": hillshade(
            data,
            resolution_m=resolution_m,
            azimuth_deg=hillshade_azimuth_deg,
            altitude_deg=hillshade_altitude_deg,
            mask=mask,
        ),
        "local_relief_r16m": local_relief_model(
            data,
            radius_pixels=radius_pixels,
            mask=mask,
        ),
    }
