from dataclasses import replace

import pytest

from archaeoai.dataset import (
    BACKGROUND_LABEL,
    DATASET_FIELDS,
    POSITIVE_LABEL,
    DatasetRecord,
    validate_dataset_index,
)
from archaeoai.splits import (
    assign_geographic,
    assign_group_aware_random,
    assignment_digest,
    cross_partition_distance_violations,
    cross_partition_window_overlaps,
    terrain_windows_overlap,
    validate_frozen_assignment,
    validate_split_integrity,
)


def _record(
    number: int,
    class_label: str,
    group: str,
    block: str,
    *,
    overlap: str = "",
) -> DatasetRecord:
    return DatasetRecord(
        sample_id=f"E001X-{number:012d}",
        class_label=class_label,
        observation_group_id=group,
        overlap_component_id=overlap,
        geographic_block_id=block,
        survey_year="2020",
        provenance_id="EAP-test",
        source_resolution_m=1.0,
        patch_size_m=128,
        processing_version="test-v1",
        qa_status="pass",
        sampling_stratum="E001S-test",
        patch_sha256=f"{number:064x}",
        split_random="train",
        split_geographic="train",
    )


def _balanced_records(group_count: int = 20) -> list[DatasetRecord]:
    records = []
    for index in range(group_count):
        group = f"G{index:02d}"
        block = f"B{index // 4}"
        records.extend(
            [
                _record(index * 2 + 1, POSITIVE_LABEL, group, block),
                _record(index * 2 + 2, BACKGROUND_LABEL, group, block),
            ]
        )
    return records


def test_group_aware_random_split_is_balanced_deterministic_and_inseparable() -> None:
    records = _balanced_records()
    first = assign_group_aware_random(
        records, development_positive_count=3, final_test_positive_count=4
    )
    second = assign_group_aware_random(
        records, development_positive_count=3, final_test_positive_count=4
    )

    assert first == second
    for partition, expected_per_class in (("train", 13), ("development", 3), ("final_test", 4)):
        assert (
            sum(
                row.split_random == partition and row.class_label == POSITIVE_LABEL for row in first
            )
            == expected_per_class
        )
        assert (
            sum(
                row.split_random == partition and row.class_label == BACKGROUND_LABEL
                for row in first
            )
            == expected_per_class
        )
    assert all(
        len({row.split_random for row in first if row.observation_group_id == group}) == 1
        for group in {row.observation_group_id for row in first}
    )


def test_geographic_split_holds_out_complete_blocks() -> None:
    records = _balanced_records()
    assigned = assign_geographic(
        records,
        development_groups=frozenset({"B1"}),
        final_test_groups=frozenset({"B3", "B4"}),
    )

    assert {
        row.geographic_block_id for row in assigned if row.split_geographic == "development"
    } == {"B1"}
    assert {
        row.geographic_block_id for row in assigned if row.split_geographic == "final_test"
    } == {
        "B3",
        "B4",
    }


def test_overlap_component_cannot_cross_a_partition() -> None:
    records = _balanced_records(3)
    records[0] = replace(records[0], overlap_component_id="O1", split_random="train")
    records[1] = replace(records[1], split_random="train")
    records[2] = replace(records[2], overlap_component_id="O1", split_random="final_test")
    records[3] = replace(records[3], split_random="final_test")

    with pytest.raises(ValueError, match="overlap component"):
        validate_split_integrity(records, condition="random")


def test_duplicate_ids_and_duplicate_rasters_are_rejected() -> None:
    records = _balanced_records(2)
    with pytest.raises(ValueError, match="duplicate sample ID"):
        validate_dataset_index([records[0], records[0], *records[1:]])
    with pytest.raises(ValueError, match="duplicate terrain content"):
        validate_dataset_index(
            [records[0], replace(records[1], patch_sha256=records[0].patch_sha256)]
        )


def test_frozen_assignment_digest_detects_change() -> None:
    records = assign_group_aware_random(
        _balanced_records(), development_positive_count=3, final_test_positive_count=4
    )
    digest = assignment_digest(records, condition="random")
    validate_frozen_assignment(records, condition="random", expected_digest=digest)

    changed = [replace(records[0], split_random="final_test"), *records[1:]]
    with pytest.raises(ValueError):
        validate_frozen_assignment(changed, condition="random", expected_digest=digest)


def test_modelling_index_schema_is_coordinate_safe() -> None:
    forbidden = {"easting", "northing", "latitude", "longitude", "bbox", "geometry"}
    assert forbidden.isdisjoint(DATASET_FIELDS)
    validate_dataset_index(_balanced_records(3))


def test_cross_split_window_overlap_is_detected_without_serializing_coordinates() -> None:
    assert terrain_windows_overlap((0, 0), (127, 0), patch_size_m=128)
    assert not terrain_windows_overlap((0, 0), (128, 0), patch_size_m=128)
    samples = [
        ("A", "train", (0.0, 0.0)),
        ("B", "final_test", (100.0, 0.0)),
        ("C", "train", (1000.0, 1000.0)),
    ]
    assert cross_partition_window_overlaps(samples, patch_size_m=128) == [("A", "B")]
    assert cross_partition_distance_violations(samples, minimum_m=128) == [("A", "B")]
    assert cross_partition_distance_violations(samples, minimum_m=100) == []
