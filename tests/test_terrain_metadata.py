from archaeoai.terrain_metadata import (
    assess_terrain_features,
    esri_geometry_qa,
    patch_sample_points,
    point_in_ring,
)


def _square_geojson(size: float = 100) -> dict[str, object]:
    return {
        "type": "Polygon",
        "coordinates": [[[0, 0], [size, 0], [size, size], [0, size], [0, 0]]],
    }


def test_point_in_ring() -> None:
    ring = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]
    assert point_in_ring((5, 5), ring)
    assert not point_in_ring((20, 5), ring)


def test_geometry_qa_passes_one_compact_polygon() -> None:
    # Clockwise winding is the ArcGIS exterior-ring convention.
    geometry = {"rings": [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]]}

    result = esri_geometry_qa(geometry, centroid=(5, 5), area_ha=0.01)

    assert result.status == "pass"
    assert result.part_count == 1


def test_geometry_qa_flags_off_centre_and_large_designations() -> None:
    geometry = {"rings": [[[0, 0], [0, 10], [10, 10], [10, 0], [0, 0]]]}

    assert esri_geometry_qa(geometry, centroid=(15, 5), area_ha=0.01).reason == (
        "geometry_off_centre"
    )
    assert esri_geometry_qa(geometry, centroid=(5, 5), area_ha=0.7).reason == ("geometry_too_large")


def test_terrain_assessment_requires_full_patch_and_provenance() -> None:
    composite = [
        {
            "geometry": _square_geojson(),
            "properties": {
                "polygon_id": "P_1",
                "year": 2021,
                "resolution": 1,
                "sd_flown": "2021-01-01",
                "ed_flown": "2021-02-01",
            },
        }
    ]
    programme = [{"properties": {"polygon_id": "P_1"}}]

    result = assess_terrain_features(
        composite_features=composite,
        programme_features=programme,
        timestamped_features=[],
        sample_points=patch_sample_points((50, 50), patch_size_m=50),
    )

    assert result.coverage_status == "pass"
    assert result.provenance_status == "pass"
    assert result.programme == "National LIDAR Programme"


def test_terrain_assessment_flags_incomplete_patch() -> None:
    composite = [
        {
            "geometry": _square_geojson(20),
            "properties": {
                "polygon_id": "P_1",
                "year": 2021,
                "resolution": 1,
                "sd_flown": "2021-01-01",
                "ed_flown": "2021-02-01",
            },
        }
    ]

    result = assess_terrain_features(
        composite_features=composite,
        programme_features=[],
        timestamped_features=[],
        sample_points=patch_sample_points((10, 10), patch_size_m=30),
    )

    assert result.coverage_status == "fail"
    assert result.reason == "terrain_patch_incomplete"


def test_composite_source_filename_supplies_programme_without_extra_query() -> None:
    composite = [
        {
            "geometry": _square_geojson(),
            "properties": {
                "polygon_id": "P_1",
                "year": 2021,
                "resolution": 1,
                "sd_flown": "2021-01-01",
                "ed_flown": "2021-02-01",
                "od_dtm_fn": "NP 1m DTM tiles (5x5km)",
            },
        }
    ]

    result = assess_terrain_features(
        composite_features=composite,
        programme_features=[],
        timestamped_features=[],
        sample_points=patch_sample_points((50, 50), patch_size_m=50),
    )

    assert result.provenance_status == "pass"
    assert result.programme == "National LIDAR Programme"
