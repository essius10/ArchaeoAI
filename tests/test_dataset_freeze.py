import csv
import json
from pathlib import Path

from archaeoai.dataset import (
    BACKGROUND_LABEL,
    POSITIVE_LABEL,
    DatasetRecord,
    validate_dataset_index,
)
from archaeoai.splits import validate_frozen_assignment
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

ROOT = Path(__file__).resolve().parents[1]


def _load_records() -> list[DatasetRecord]:
    with (ROOT / "outputs/dataset/e001_modelling_index.csv").open(
        encoding="utf-8-sig", newline=""
    ) as file:
        rows = list(csv.DictReader(file))
    return [
        DatasetRecord(
            sample_id=row["sample_id"],
            class_label=row["class_label"],
            observation_group_id=row["observation_group_id"],
            overlap_component_id=row["overlap_component_id"],
            geographic_block_id=row["geographic_block_id"],
            survey_year=row["survey_year"],
            provenance_id=row["provenance_id"],
            source_resolution_m=float(row["source_resolution_m"]),
            patch_size_m=int(row["patch_size_m"]),
            processing_version=row["processing_version"],
            qa_status=row["qa_status"],
            sampling_stratum=row["sampling_stratum"],
            patch_sha256=row["patch_sha256"],
            split_random=row["split_random"],
            split_geographic=row["split_geographic"],
        )
        for row in rows
    ]


def test_frozen_dataset_artifacts_are_complete_balanced_and_coordinate_safe() -> None:
    records = _load_records()
    validate_dataset_index(records)

    assert len(records) == 522
    assert sum(row.class_label == POSITIVE_LABEL for row in records) == 261
    assert sum(row.class_label == BACKGROUND_LABEL for row in records) == 261
    with (ROOT / "outputs/dataset/e001_modelling_index.csv").open(encoding="utf-8-sig") as file:
        header = next(csv.reader(file))
    forbidden = {"easting", "northing", "latitude", "longitude", "bbox", "geometry"}
    assert forbidden.isdisjoint({field.casefold() for field in header})


def test_frozen_manifests_guard_exact_assignments() -> None:
    records = _load_records()
    for condition in ("random", "geographic"):
        manifest = json.loads(
            (ROOT / f"outputs/dataset/e001_{condition}_split_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        assert manifest["frozen"] is True
        assert_coordinate_safe_mapping(manifest)
        validate_frozen_assignment(
            records,
            condition=condition,
            expected_digest=manifest["assignment_sha256"],
        )


def test_geographic_final_test_is_the_predeclared_complete_block_pair() -> None:
    records = _load_records()
    final_rows = [row for row in records if row.split_geographic == "final_test"]

    assert {row.geographic_block_id for row in final_rows} == {
        "BNG_100KM_E3_N2",
        "BNG_100KM_E5_N4",
    }
    assert sum(row.class_label == POSITIVE_LABEL for row in final_rows) == 31
    assert sum(row.class_label == BACKGROUND_LABEL for row in final_rows) == 31


def test_tracked_dataset_uses_no_false_negative_terminology() -> None:
    records = _load_records()
    labels = {row.class_label for row in records}

    assert labels == {POSITIVE_LABEL, BACKGROUND_LABEL}
    assert labels.isdisjoint({"negative", "non_archaeology", "true_negative", "no_archaeology"})
