from dataclasses import replace

import pytest

from archaeoai.terrain.acquisition import PrivateSiteLocation
from archaeoai.terrain.index import (
    TerrainIndexRecord,
    cross_group_patch_overlaps,
    validate_index,
)


def _record(sample_id: str = "S1", list_entry: int = 1) -> TerrainIndexRecord:
    return TerrainIndexRecord(
        sample_id=sample_id,
        nhle_list_entry=list_entry,
        geographic_group_id="G1",
        terrain_provenance_id="PROV1",
        survey_year="2020",
        source_resolution_m=1.0,
        processing_version="test-v1",
        patch_size_m=128,
        representations="raw",
        qa_status="pass",
        patch_sha256="a" * 64,
    )


def _location(list_entry: int, x: float, group: str) -> PrivateSiteLocation:
    return PrivateSiteLocation(
        list_entry=list_entry,
        easting=x,
        northing=1000,
        geographic_group_id=group,
        terrain_year="2020",
        source_resolution_m="1",
        survey_program="test",
    )


def test_valid_coordinate_safe_index() -> None:
    validate_index([_record(), _record("S2", 2)])


def test_duplicate_samples_and_sources_are_rejected() -> None:
    with pytest.raises(ValueError, match="sample ID"):
        validate_index([_record(), _record("S1", 2)])
    with pytest.raises(ValueError, match="source observation"):
        validate_index([_record(), _record("S2", 1)])


def test_invalid_checksum_is_rejected() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        validate_index([replace(_record(), patch_sha256="bad")])


def test_cross_group_overlap_detection_uses_private_locations() -> None:
    locations = (
        _location(1, 1000, "G1"),
        _location(2, 1050, "G2"),
        _location(3, 2000, "G3"),
    )

    assert cross_group_patch_overlaps(locations, patch_size_m=128) == ((1, 2),)
