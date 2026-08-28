import pytest

from archaeoai.terrain.patches import Bounds, patch_bounds, required_grid_tiles


def test_patch_bounds_snap_to_resolution_grid() -> None:
    bounds = patch_bounds((100.4, 200.6), patch_size_m=128, resolution_m=1)

    assert bounds == Bounds(36, 137, 164, 265)
    assert bounds.width == bounds.height == 128


def test_patch_bounds_reject_fractional_pixel_count() -> None:
    with pytest.raises(ValueError, match="integer number"):
        patch_bounds((100, 200), patch_size_m=100, resolution_m=3)


def test_tile_discovery_handles_boundary_crossing() -> None:
    tiles = required_grid_tiles(Bounds(4998, 4998, 5002, 5002))

    assert [tile.tile_id for tile in tiles] == [
        "BNG5K_E000_N000",
        "BNG5K_E001_N000",
        "BNG5K_E000_N001",
        "BNG5K_E001_N001",
    ]


def test_tile_discovery_does_not_add_touching_cell() -> None:
    tiles = required_grid_tiles(Bounds(0, 0, 5000, 5000))

    assert [tile.tile_id for tile in tiles] == ["BNG5K_E000_N000"]
