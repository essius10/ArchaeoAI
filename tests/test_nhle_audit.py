from datetime import UTC, datetime

import pytest

from archaeoai.nhle_audit import (
    NhleRecord,
    TriageCategory,
    broad_grid_id,
    build_audit_summary,
    stable_sample_ids,
    triage_title,
)


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Bowl barrow 400m north of Example Farm", TriageCategory.PROBABLE_BOWL),
        ("Two bowl barrows west of Example Farm", TriageCategory.CLEAR_EXCLUSION),
        ("Bell barrow called Example", TriageCategory.CLEAR_EXCLUSION),
        ("Example round barrow", TriageCategory.MANUAL_REVIEW),
        (
            "Bowl barrow and associated field system",
            TriageCategory.MANUAL_REVIEW,
        ),
        (
            "Bowl barrow forming part of a barrow cemetery",
            TriageCategory.MANUAL_REVIEW,
        ),
    ],
)
def test_title_triage_is_conservative(title: str, expected: TriageCategory) -> None:
    assert triage_title(title).category is expected


def test_title_triage_rejects_unrelated_title() -> None:
    with pytest.raises(ValueError, match="containing 'barrow'"):
        triage_title("Roman fort")


def test_broad_grid_id_aggregates_without_coordinates() -> None:
    assert broad_grid_id(234_567.0, 345_678.0) == "BNG_100KM_E2_N3"
    assert broad_grid_id(None, 345_678.0) == "UNAVAILABLE"


def test_broad_grid_id_rejects_invalid_size() -> None:
    with pytest.raises(ValueError, match="positive"):
        broad_grid_id(1.0, 1.0, size_km=0)


def test_stable_sample_is_deterministic_and_coordinate_independent() -> None:
    records = [
        NhleRecord(number, f"Bowl barrow example {number}", float(number), 1.0)
        for number in range(100, 110)
    ]
    changed_coordinates = [
        NhleRecord(record.list_entry, record.name, 999_999.0, 999_999.0) for record in records
    ]

    assert stable_sample_ids(records, sample_size=4) == stable_sample_ids(
        changed_coordinates, sample_size=4
    )


def test_build_summary_partitions_counts_and_retains_only_aggregates() -> None:
    records = [
        NhleRecord(
            1,
            "Bowl barrow at Example",
            210_000.0,
            310_000.0,
            "1:10000",
            0.05,
        ),
        NhleRecord(2, "Long barrow at Example", 220_000.0, 320_000.0, "1:10000", 0.08),
        NhleRecord(3, "Example round barrow", 230_000.0, 330_000.0, "1:10000", 0.10),
    ]
    service_metadata = {"supportedExportFormats": "csv,geojson"}
    layer_metadata = {
        "name": "Scheduled Monuments",
        "geometryType": "esriGeometryPolygon",
        "supportedQueryFormats": "JSON, geoJSON",
        "extent": {"spatialReference": {"wkid": 27700}},
        "fields": [{"name": "ListEntry", "alias": "List Entry Number", "type": "integer"}],
        "editingInfo": {"lastEditDate": 0},
    }

    summary, rows = build_audit_summary(
        total_features=20_001,
        distinct_list_entries=20_000,
        barrow_records=records,
        service_metadata=service_metadata,
        layer_metadata=layer_metadata,
        accessed_at=datetime(2026, 8, 27, tzinfo=UTC),
        sample_size=1,
    )

    assert summary["counts"] == {
        "total_scheduled_monument_records_examined": 20_000,
        "scheduled_monument_polygon_features": 20_001,
        "duplicate_list_entry_features": 1,
        "broad_barrow_candidates": 3,
        "probable_bowl_candidates": 1,
        "clear_title_exclusions": 1,
        "manual_review_required": 1,
    }
    assert summary["privacy"]["stored_coordinates"] is False
    assert summary["geometry_metadata"]["probable_candidate_capture_scales"] == {"1:10000": 1}
    assert summary["geometry_metadata"]["probable_candidate_area_ha"]["median"] == 0.05
    assert rows == [
        {
            "broad_group": "BNG_100KM_E2_N3",
            "broad_barrow_candidates": 3,
            "probable_bowl_candidates": 1,
            "clear_title_exclusions": 1,
            "manual_review_required": 1,
        }
    ]


def test_build_summary_rejects_duplicate_broad_list_entries() -> None:
    records = [
        NhleRecord(1, "Bowl barrow at Example", 1.0, 1.0),
        NhleRecord(1, "Bowl barrow at Example", 1.0, 1.0),
    ]

    with pytest.raises(ValueError, match="unique List Entry"):
        build_audit_summary(
            total_features=2,
            distinct_list_entries=1,
            barrow_records=records,
            service_metadata={},
            layer_metadata={},
            accessed_at=datetime(2026, 8, 27, tzinfo=UTC),
        )
