import pytest

from archaeoai.curation import (
    CurationRecord,
    EvidenceValue,
    ExclusionReason,
    QaStatus,
    ReviewStatus,
    assert_coordinate_safe_fields,
    assess_full_entry,
    deterministic_second_review_ids,
    geographically_stratified_queue,
    select_nonadjacent_holdout_candidates,
)
from archaeoai.nhle_audit import NhleRecord


def test_full_entry_accepts_only_with_explicit_identity_single_and_relief() -> None:
    assessment = assess_full_entry(
        reasons="Bowl barrows are funerary monuments.",
        details="The monument includes a bowl barrow. It survives as an earthen mound 1.2m high.",
    )

    assert assessment.status is ReviewStatus.NEEDS_GEOMETRY_REVIEW
    assert assessment.identity is EvidenceValue.YES
    assert assessment.single_monument is EvidenceValue.YES
    assert assessment.upstanding is EvidenceValue.YES


@pytest.mark.parametrize(
    ("details", "reason"),
    [
        ("The bowl barrow is visible only as a cropmark.", ExclusionReason.CROPMARK_ONLY),
        ("The bowl barrow has been completely levelled.", ExclusionReason.NO_UPSTANDING_RELIEF),
        (
            "The bowl barrow was wholly removed and reconstructed.",
            ExclusionReason.DESTROYED_OR_RECONSTRUCTED,
        ),
        ("The bowl barrow comprises a round cairn 1m high.", ExclusionReason.CAIRN),
        (
            "The monument includes two bowl barrows which survive as mounds.",
            ExclusionReason.COMPOUND_OR_MULTIPLE,
        ),
    ],
)
def test_full_entry_rejects_controlled_exclusions(details: str, reason: ExclusionReason) -> None:
    assessment = assess_full_entry(reasons="A bowl barrow.", details=details)

    assert assessment.status is ReviewStatus.REJECTED
    assert assessment.reason is reason


def test_full_entry_keeps_missing_relief_uncertain() -> None:
    assessment = assess_full_entry(
        reasons="The monument is a bowl barrow.",
        details="The monument includes a bowl barrow of Bronze Age date.",
    )

    assert assessment.status is ReviewStatus.UNCERTAIN
    assert assessment.reason is ExclusionReason.INSUFFICIENT_EVIDENCE


def test_barrows_nearby_or_a_single_barrows_ditch_do_not_make_record_compound() -> None:
    assessment = assess_full_entry(
        reasons="The scheduled example is a bowl barrow; other barrows survive nearby.",
        details=(
            "The monument includes a bowl barrow on a natural knoll near marshes and an estuary. "
            "The barrow is visible as a mound 1.5m high. Its infilled ditch is buried."
        ),
    )

    assert assessment.status is ReviewStatus.NEEDS_GEOMETRY_REVIEW


def test_queue_is_deterministic_geographically_distributed_and_unique() -> None:
    records = [
        NhleRecord(
            list_entry=index + 1,
            name=f"Bowl barrow at fictional place {index}",
            easting=float((index % 4 + 1) * 100_000 + 10),
            northing=float((index % 3 + 1) * 100_000 + 10),
        )
        for index in range(80)
    ]

    first = geographically_stratified_queue(records, size=36)
    second = geographically_stratified_queue(list(reversed(records)), size=36)

    assert [record.list_entry for record in first] == [record.list_entry for record in second]
    assert len({record.list_entry for record in first}) == 36
    assert len({(int(r.easting // 100_000), int(r.northing // 100_000)) for r in first}) == 12


def _record(list_entry: int, status: ReviewStatus) -> CurationRecord:
    accepted = status is ReviewStatus.ACCEPTED
    return CurationRecord(
        list_entry=list_entry,
        review_status=status,
        bowl_barrow_identity=EvidenceValue.YES,
        single_monument=EvidenceValue.YES,
        upstanding_earthwork=EvidenceValue.YES,
        geometry_qa=QaStatus.PASS if accepted else QaStatus.NOT_REVIEWED,
        terrain_coverage=QaStatus.PASS if accepted else QaStatus.NOT_REVIEWED,
        terrain_provenance=QaStatus.PASS if accepted else QaStatus.NOT_REVIEWED,
        geographic_group_id="BNG_100KM_E1_N1" if accepted else "UNAVAILABLE",
        exclusion_reason=None if accepted else ExclusionReason.INSUFFICIENT_EVIDENCE,
    )


def test_accepted_record_requires_every_gate() -> None:
    record = _record(1, ReviewStatus.ACCEPTED)
    record.terrain_provenance = QaStatus.NEEDS_REVIEW

    with pytest.raises(ValueError, match="every curation gate"):
        record.validate()


def test_second_review_queue_is_deterministic_and_status_stratified() -> None:
    records = [_record(index, ReviewStatus.ACCEPTED) for index in range(1, 21)]
    records += [_record(index, ReviewStatus.REJECTED) for index in range(21, 41)]

    selected = deterministic_second_review_ids(records, sample_size=10)

    assert selected == deterministic_second_review_ids(records, sample_size=10)
    assert sum(value <= 20 for value in selected) == 5
    assert sum(value > 20 for value in selected) == 5


def test_holdout_groups_are_nonadjacent() -> None:
    counts = {
        "BNG_100KM_E1_N1": 30,
        "BNG_100KM_E2_N2": 40,
        "BNG_100KM_E4_N1": 25,
        "BNG_100KM_E5_N3": 20,
    }

    selected = select_nonadjacent_holdout_candidates(counts, minimum_count=15)

    assert selected == ["BNG_100KM_E2_N2", "BNG_100KM_E4_N1", "BNG_100KM_E5_N3"]


def test_coordinate_fields_are_forbidden_in_tracked_outputs() -> None:
    with pytest.raises(ValueError, match="coordinate fields"):
        assert_coordinate_safe_fields(["list_entry", "Easting"])

    assert_coordinate_safe_fields(["list_entry", "geographic_group_id"])
