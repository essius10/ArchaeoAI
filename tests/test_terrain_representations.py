import math

import numpy as np
import pytest

from archaeoai.terrain.representations import (
    hillshade,
    local_relief_model,
    normalize_elevation,
    slope_degrees,
    terrain_representations,
)


def test_per_patch_elevation_normalization_uses_local_median() -> None:
    data = np.array([[10, 11], [12, 13]], dtype=np.float32)

    normalized = normalize_elevation(data)

    assert float(np.median(normalized)) == 0
    np.testing.assert_array_equal(normalized, data - 11.5)


def test_synthetic_plane_has_expected_slope() -> None:
    x = np.arange(10, dtype=np.float32)
    plane = np.tile(2 * x, (10, 1))

    slope = slope_degrees(plane, resolution_m=1)

    np.testing.assert_allclose(slope, math.degrees(math.atan(2)), atol=1e-5)


def test_flat_surface_hillshade_equals_sun_altitude_component() -> None:
    shade = hillshade(np.ones((8, 8)), resolution_m=1, altitude_deg=45)

    np.testing.assert_allclose(shade, math.sin(math.radians(45)), atol=1e-6)


def test_hillshade_changes_with_slope_orientation() -> None:
    east_rising = np.tile(np.arange(8, dtype=np.float32), (8, 1))

    illuminated_from_west = hillshade(east_rising, resolution_m=1, azimuth_deg=270)
    illuminated_from_east = hillshade(east_rising, resolution_m=1, azimuth_deg=90)

    assert float(np.nanmean(illuminated_from_west)) > float(np.nanmean(illuminated_from_east))


def test_local_relief_removes_linear_plane_interior() -> None:
    y, x = np.mgrid[:21, :21]
    plane = (2 * x + 3 * y).astype(np.float32)

    relief = local_relief_model(plane, radius_pixels=3)

    np.testing.assert_allclose(relief[3:-3, 3:-3], 0, atol=1e-6)


def test_local_relief_highlights_synthetic_mound() -> None:
    y, x = np.mgrid[-16:17, -16:17]
    mound = np.exp(-(x**2 + y**2) / (2 * 3**2)).astype(np.float32)

    relief = local_relief_model(mound, radius_pixels=8)

    assert relief[16, 16] > 0.7
    assert float(np.nanmin(relief)) < 0


def test_mask_is_propagated_without_silent_fill() -> None:
    data = np.ones((8, 8), dtype=np.float32)
    mask = np.zeros_like(data, dtype=bool)
    mask[3, 3] = True

    outputs = terrain_representations(data, resolution_m=1, mask=mask)

    assert set(outputs) == {
        "elevation_normalized",
        "slope_degrees",
        "hillshade_315_45",
        "local_relief_r16m",
    }
    assert all(np.isnan(output[3, 3]) for output in outputs.values())


def test_local_relief_radius_must_align_to_pixels() -> None:
    with pytest.raises(ValueError, match="integer number"):
        terrain_representations(np.ones((8, 8)), resolution_m=2, local_relief_radius_m=3)
