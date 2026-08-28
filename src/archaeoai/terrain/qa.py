"""Private, non-georeferenced visual QA mosaics for terrain representations."""

from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import NotGeoreferencedWarning

from archaeoai.terrain.privacy import ensure_private_output, verify_git_ignored

QA_ORDER = (
    "elevation_normalized",
    "hillshade_315_45",
    "slope_degrees",
    "local_relief_r16m",
)


def _scale_byte(values: np.ndarray) -> np.ndarray:
    finite = np.isfinite(values)
    if not finite.any():
        raise ValueError("cannot visualize an all-nodata representation")
    lower, upper = np.percentile(values[finite], [2, 98])
    if upper <= lower:
        return np.where(finite, 127, 0).astype(np.uint8)
    scaled = np.clip((values - lower) / (upper - lower), 0, 1) * 255
    return np.where(finite, scaled, 0).astype(np.uint8)


def qa_mosaic(representations: dict[str, np.ndarray], *, gutter: int = 2) -> np.ndarray:
    missing = set(QA_ORDER) - set(representations)
    if missing:
        raise ValueError(f"missing QA representations: {sorted(missing)}")
    shapes = {representations[name].shape for name in QA_ORDER}
    if len(shapes) != 1:
        raise ValueError("QA representations must have matching dimensions")
    height, width = next(iter(shapes))
    mosaic = np.full((2 * height + gutter, 2 * width + gutter), 255, dtype=np.uint8)
    positions = (
        (0, 0),
        (0, width + gutter),
        (height + gutter, 0),
        (height + gutter, width + gutter),
    )
    for name, (row, column) in zip(QA_ORDER, positions, strict=True):
        mosaic[row : row + height, column : column + width] = _scale_byte(representations[name])
    return mosaic


def write_private_qa_png(
    representations: dict[str, np.ndarray], *, destination: Path, project_root: Path
) -> Path:
    output = ensure_private_output(project_root, destination)
    verify_git_ignored(project_root, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    mosaic = qa_mosaic(representations)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", NotGeoreferencedWarning)
        with rasterio.open(
            output,
            "w",
            driver="PNG",
            width=mosaic.shape[1],
            height=mosaic.shape[0],
            count=1,
            dtype="uint8",
        ) as dataset:
            dataset.write(mosaic, 1)
    return output
