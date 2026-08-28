from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from archaeoai.terrain.raster import extract_patch, read_raster_metadata, sha256_file
from archaeoai.terrain.validation import TerrainReason, TerrainValidationError


def _write_raster(
    path: Path,
    data: np.ndarray,
    *,
    left: float,
    top: float,
    resolution: float = 1.0,
    crs: str = "EPSG:27700",
    nodata: float = -9999.0,
) -> Path:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=data.shape[1],
        height=data.shape[0],
        count=1,
        dtype="float32",
        crs=crs,
        transform=from_origin(left, top, resolution, resolution),
        nodata=nodata,
    ) as dataset:
        dataset.write(data.astype("float32"), 1)
    return path


def test_reads_raster_metadata_and_checksum(tmp_path: Path) -> None:
    source = _write_raster(tmp_path / "terrain.tif", np.ones((10, 20)), left=0, top=10)

    metadata = read_raster_metadata(source)

    assert metadata.crs == "EPSG:27700"
    assert metadata.resolution_m == (1.0, 1.0)
    assert metadata.width == 20
    assert len(sha256_file(source)) == 64


def test_rejects_wrong_crs(tmp_path: Path) -> None:
    source = _write_raster(
        tmp_path / "wrong-crs.tif", np.ones((10, 10)), left=0, top=10, crs="EPSG:4326"
    )

    with pytest.raises(TerrainValidationError) as error:
        extract_patch([source], centre=(5, 5), patch_size_m=4)

    assert error.value.reasons == (TerrainReason.CRS_MISMATCH,)


def test_rejects_wrong_resolution(tmp_path: Path) -> None:
    source = _write_raster(
        tmp_path / "wrong-resolution.tif",
        np.ones((10, 10)),
        left=0,
        top=20,
        resolution=2,
    )

    with pytest.raises(TerrainValidationError) as error:
        extract_patch([source], centre=(10, 10), patch_size_m=4)

    assert error.value.reasons == (TerrainReason.RESOLUTION_MISMATCH,)


def test_extracts_deterministic_single_tile_patch(tmp_path: Path) -> None:
    values = np.arange(100, dtype=np.float32).reshape(10, 10)
    source = _write_raster(tmp_path / "terrain.tif", values, left=0, top=10)

    first = extract_patch([source], centre=(5, 5), patch_size_m=4)
    second = extract_patch([source], centre=(5, 5), patch_size_m=4)

    np.testing.assert_array_equal(first.data, values[3:7, 3:7])
    np.testing.assert_array_equal(first.data, second.data)
    assert first.bounds.as_tuple() == (3, 3, 7, 7)
    assert first.qa.nodata_fraction == 0


def test_stitches_patch_across_two_tiles(tmp_path: Path) -> None:
    west = _write_raster(tmp_path / "west.tif", np.ones((10, 5)), left=0, top=10)
    east = _write_raster(tmp_path / "east.tif", np.full((10, 5), 2), left=5, top=10)

    patch = extract_patch([east, west], centre=(5, 5), patch_size_m=4)

    np.testing.assert_array_equal(
        patch.data,
        np.array([[1, 1, 2, 2]] * 4, dtype=np.float32),
    )


def test_rejects_excess_nodata_without_filling(tmp_path: Path) -> None:
    values = np.ones((6, 6), dtype=np.float32)
    values[2:4, 2:4] = -9999
    source = _write_raster(tmp_path / "nodata.tif", values, left=0, top=6)

    with pytest.raises(TerrainValidationError) as error:
        extract_patch(
            [source],
            centre=(3, 3),
            patch_size_m=4,
            max_nodata_fraction=0.2,
        )

    assert TerrainReason.NODATA_EXCESS in error.value.reasons


def test_rejects_missing_tile_coverage(tmp_path: Path) -> None:
    west = _write_raster(tmp_path / "west.tif", np.ones((4, 2)), left=0, top=4)

    with pytest.raises(TerrainValidationError) as error:
        extract_patch([west], centre=(2, 2), patch_size_m=4, max_nodata_fraction=0.2)

    assert TerrainReason.NODATA_EXCESS in error.value.reasons
