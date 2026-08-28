from dataclasses import replace
from pathlib import Path

import pytest

from archaeoai.terrain.acquisition import PrivateSiteLocation
from archaeoai.terrain.index import (
    TerrainIndexRecord,
    cross_group_patch_overlaps,
    overlap_components,
    validate_index,
    write_index,
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
        acquisition_status="verified",
        raw_qa_status="pass",
        representation_qa_status="pass",
        representations=("elevation_normalized;slope_degrees;hillshade_315_45;local_relief_r16m"),
        qa_status="pass",
        raw_sha256="b" * 64,
        patch_sha256=f"{list_entry:064x}",
        processed_sha256="c" * 64,
        cross_cell=False,
        overlap_group_id="",
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


def test_safe_index_serialization_excludes_coordinate_fields(tmp_path: Path) -> None:
    destination = tmp_path / "index.csv"

    write_index([_record(), _record("S2", 2)], destination)

    header = destination.read_text(encoding="utf-8").splitlines()[0].casefold()
    assert not {
        "easting",
        "northing",
        "ngr",
        "latitude",
        "longitude",
        "geometry",
        "bounds",
    }.intersection(header.split(","))
    assert "overlap_group_id" in header


def test_duplicate_samples_and_sources_are_rejected() -> None:
    with pytest.raises(ValueError, match="sample ID"):
        validate_index([_record(), _record("S1", 2)])
    with pytest.raises(ValueError, match="source observation"):
        validate_index([_record(), _record("S2", 1)])


def test_invalid_checksum_is_rejected() -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        validate_index([replace(_record(), patch_sha256="bad")])


def test_duplicate_exact_terrain_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate exact terrain"):
        validate_index([_record(), replace(_record("S2", 2), patch_sha256=_record().patch_sha256)])


def test_failure_checksum_must_use_lowercase_sha256_syntax() -> None:
    failed = replace(
        _record(),
        acquisition_status="failed",
        raw_qa_status="failed",
        representation_qa_status="not_run",
        representations="",
        qa_status="rejected",
        raw_sha256="G" * 64,
        patch_sha256="",
        processed_sha256="",
    )

    with pytest.raises(ValueError, match="failure-row checksums"):
        validate_index([failed])


def test_cross_group_overlap_detection_uses_private_locations() -> None:
    locations = (
        _location(1, 1000, "G1"),
        _location(2, 1050, "G2"),
        _location(3, 2000, "G3"),
    )

    assert cross_group_patch_overlaps(locations, patch_size_m=128) == ((1, 2),)


def test_overlap_components_are_stable_and_make_split_constraints_explicit() -> None:
    locations = (
        _location(1, 1000, "G1"),
        _location(2, 1050, "G1"),
        _location(3, 2000, "G2"),
    )

    mapping, pairs = overlap_components(locations, patch_size_m=128)

    assert pairs == ((1, 2),)
    assert mapping[1] == mapping[2]
    assert 3 not in mapping


def test_overlap_index_group_must_have_multiple_same_region_members() -> None:
    with pytest.raises(ValueError, match="fewer than two"):
        validate_index([replace(_record(), overlap_group_id="E001O-test")])

    with pytest.raises(ValueError, match="crosses provisional"):
        validate_index(
            [
                replace(_record(), overlap_group_id="E001O-test"),
                replace(
                    _record("S2", 2),
                    geographic_group_id="G2",
                    overlap_group_id="E001O-test",
                ),
            ]
        )
