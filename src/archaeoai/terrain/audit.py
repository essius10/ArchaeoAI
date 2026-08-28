"""Coordinate-safe helpers for freezing the full E001 positive terrain dataset."""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

import numpy as np

from archaeoai.terrain.patches import Bounds

_DIAMETER_PATTERNS = (
    re.compile(
        r"(?:diameter(?: of)?|measur(?:e|es|ing)|dimensions? of)"
        r"[^.;]{0,90}?(\d+(?:\.\d+)?)\s*m\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(\d+(?:\.\d+)?)\s*m\s+(?:in\s+)?(?:maximum\s+)?diameter\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(\d+(?:\.\d+)?)\s*m\s+across\b", re.IGNORECASE),
)


@dataclass(frozen=True, slots=True)
class SeamDiagnostic:
    orientation: str
    pixel_index: int
    elevation_median_step: float
    elevation_step_percentile: float
    duplicate_edge: bool
    slope_strip_median: float
    local_relief_strip_median_abs: float


def extract_described_diameter(details: str) -> float | None:
    """Extract a conservative mound/barrow size for QA stratification, not labelling."""
    candidates: list[float] = []
    for sentence in re.split(r"(?<=[.!?])\s+", details):
        if "mound" not in sentence.casefold() and "barrow" not in sentence.casefold():
            continue
        for pattern in _DIAMETER_PATTERNS:
            candidates.extend(float(match) for match in pattern.findall(sentence))
    plausible = [value for value in candidates if 1 <= value <= 80]
    return max(plausible) if plausible else None


def deterministic_rank(sample_id: str, *, seed: str) -> str:
    return hashlib.sha256(f"{seed}:{sample_id}".encode()).hexdigest()


def _percentile_rank(value: float, population: np.ndarray) -> float:
    finite = population[np.isfinite(population)]
    if not finite.size:
        return math.nan
    return float(np.mean(finite <= value) * 100)


def cross_cell_seams(
    elevation: np.ndarray,
    slope: np.ndarray,
    local_relief: np.ndarray,
    *,
    bounds: Bounds,
    cell_size_m: int = 5000,
) -> tuple[SeamDiagnostic, ...]:
    """Measure internal 5 km boundaries without serializing their coordinates."""
    if elevation.shape != slope.shape or elevation.shape != local_relief.shape:
        raise ValueError("cross-cell QA layers must have matching shapes")
    height, width = elevation.shape
    east_steps = np.abs(np.diff(elevation, axis=1))
    north_steps = np.abs(np.diff(elevation, axis=0))
    diagnostics: list[SeamDiagnostic] = []

    first_east = math.floor(bounds.left / cell_size_m) + 1
    last_east = math.ceil(bounds.right / cell_size_m)
    for cell_index in range(first_east, last_east):
        column = round(cell_index * cell_size_m - bounds.left)
        if not 0 < column < width:
            continue
        seam = np.abs(elevation[:, column] - elevation[:, column - 1])
        median_step = float(np.nanmedian(seam))
        diagnostics.append(
            SeamDiagnostic(
                orientation="vertical",
                pixel_index=column,
                elevation_median_step=median_step,
                elevation_step_percentile=_percentile_rank(median_step, east_steps),
                duplicate_edge=np.array_equal(
                    elevation[:, column], elevation[:, column - 1], equal_nan=True
                ),
                slope_strip_median=float(
                    np.nanmedian(slope[:, max(0, column - 1) : min(width, column + 1)])
                ),
                local_relief_strip_median_abs=float(np.nanmedian(np.abs(local_relief[:, column]))),
            )
        )

    first_north = math.floor(bounds.bottom / cell_size_m) + 1
    last_north = math.ceil(bounds.top / cell_size_m)
    for cell_index in range(first_north, last_north):
        row = round(bounds.top - cell_index * cell_size_m)
        if not 0 < row < height:
            continue
        seam = np.abs(elevation[row, :] - elevation[row - 1, :])
        median_step = float(np.nanmedian(seam))
        diagnostics.append(
            SeamDiagnostic(
                orientation="horizontal",
                pixel_index=row,
                elevation_median_step=median_step,
                elevation_step_percentile=_percentile_rank(median_step, north_steps),
                duplicate_edge=np.array_equal(
                    elevation[row, :], elevation[row - 1, :], equal_nan=True
                ),
                slope_strip_median=float(
                    np.nanmedian(slope[max(0, row - 1) : min(height, row + 1), :])
                ),
                local_relief_strip_median_abs=float(np.nanmedian(np.abs(local_relief[row, :]))),
            )
        )
    return tuple(diagnostics)
