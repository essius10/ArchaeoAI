"""Coordinate-safe curation logic for the E001 bowl-barrow decision gate.

The functions in this module classify supplied official-entry text and small
metadata objects.  They never fetch terrain pixels and never persist source
coordinates or designation polygons.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from archaeoai.nhle_audit import NhleRecord, TriageCategory, broad_grid_id, triage_title

CURATION_VERSION = "e001-curation-v1"
QUEUE_SEED = "E001-Phase-2A5-2026-08-28"
SECOND_REVIEW_SEED = "E001-Phase-2A5-second-review-v1"


class EvidenceValue(StrEnum):
    YES = "yes"
    NO = "no"
    UNCERTAIN = "uncertain"


class ReviewStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"
    NEEDS_GEOMETRY_REVIEW = "needs_geometry_review"
    NEEDS_TERRAIN_REVIEW = "needs_terrain_review"


class QaStatus(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_REVIEW = "needs_review"
    NOT_REVIEWED = "not_reviewed"


class ExclusionReason(StrEnum):
    NOT_BOWL_BARROW = "not_bowl_barrow"
    COMPOUND_OR_MULTIPLE = "compound_or_multiple"
    NO_UPSTANDING_RELIEF = "no_upstanding_relief"
    CROPMARK_ONLY = "cropmark_only"
    DESTROYED_OR_RECONSTRUCTED = "destroyed_or_reconstructed"
    CAIRN = "cairn"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    GEOMETRY_COMPOUND = "geometry_compound"
    GEOMETRY_OFF_CENTRE = "geometry_off_centre"
    GEOMETRY_TOO_LARGE = "geometry_too_large"
    TERRAIN_NO_1M_COVERAGE = "terrain_no_1m_coverage"
    TERRAIN_PATCH_INCOMPLETE = "terrain_patch_incomplete"
    TERRAIN_PROVENANCE_MISSING = "terrain_provenance_missing"
    TERRAIN_PROVENANCE_CONFOUNDED = "terrain_provenance_confounded"


@dataclass(frozen=True, slots=True)
class EntryAssessment:
    status: ReviewStatus
    identity: EvidenceValue
    single_monument: EvidenceValue
    upstanding: EvidenceValue
    reason: ExclusionReason | None
    evidence_codes: tuple[str, ...]
    note: str


@dataclass(slots=True)
class CurationRecord:
    list_entry: int
    review_status: ReviewStatus
    bowl_barrow_identity: EvidenceValue
    single_monument: EvidenceValue
    upstanding_earthwork: EvidenceValue
    geometry_qa: QaStatus = QaStatus.NOT_REVIEWED
    terrain_coverage: QaStatus = QaStatus.NOT_REVIEWED
    terrain_provenance: QaStatus = QaStatus.NOT_REVIEWED
    geographic_group_id: str = "UNAVAILABLE"
    exclusion_reason: ExclusionReason | None = None
    evidence_codes: tuple[str, ...] = field(default_factory=tuple)
    reviewer_notes: str = ""
    review_date: str = ""
    source_access_date: str = ""
    source_last_edit_at: str = ""
    capture_scale: str = "UNAVAILABLE"
    terrain_year: str = "UNAVAILABLE"
    source_resolution_m: str = "UNAVAILABLE"
    survey_program: str = "UNAVAILABLE"

    def validate(self) -> None:
        if self.list_entry <= 0:
            raise ValueError("List Entry Number must be positive")
        if self.review_status is ReviewStatus.ACCEPTED and (
            self.bowl_barrow_identity is not EvidenceValue.YES
            or self.single_monument is not EvidenceValue.YES
            or self.upstanding_earthwork is not EvidenceValue.YES
            or self.geometry_qa is not QaStatus.PASS
            or self.terrain_coverage is not QaStatus.PASS
            or self.terrain_provenance is not QaStatus.PASS
            or self.geographic_group_id == "UNAVAILABLE"
            or self.exclusion_reason is not None
        ):
            raise ValueError("accepted records must pass every curation gate")
        if self.review_status is ReviewStatus.REJECTED and self.exclusion_reason is None:
            raise ValueError("rejected records require a controlled exclusion reason")


_BOWL = re.compile(r"\bbowl\s+barrow\b", re.I)
_CAIRN = re.compile(
    r"\b(?:is|comprises|includes)\s+(?:an?\s+)?"
    r"(?:(?:round|circular|sub-circular)\s+)?cairn\b",
    re.I,
)
_MULTIPLE = re.compile(
    r"\bmonument\s+includes\s+(?:the\s+remains\s+of\s+)?"
    r"(?:two|three|four|five|six|seven|eight|nine|ten|a\s+pair\s+of)\s+"
    r"(?:bowl\s+)?barrows?\b",
    re.I | re.S,
)
_COMPOUND = re.compile(
    r"\bmonument\s+includes\b.{0,220}\b(?:and|together with)\b.{0,40}"
    r"\b(?:another|second|settlement|field system|enclosure|cross|cairn)\b",
    re.I | re.S,
)
_DESTROYED = re.compile(
    r"\b(?:reconstructed|wholly removed|completely removed|"
    r"(?:wholly|completely|entirely) destroyed|has been destroyed)\b",
    re.I,
)
_LEVELLED = re.compile(
    r"\b(?:completely |wholly |entirely )?(?:levelled|flattened)\b|"
    r"\bno longer visible as (?:an? )?(?:earthwork|mound)\b",
    re.I,
)
_CROPMARK = re.compile(
    r"\b(?:visible|survives?|identified)\s+(?:only\s+)?as\s+(?:a\s+)?cropmark\b", re.I
)
_RELIEF = re.compile(
    r"\b(?:survives?|visible|stands?|measures?|rises?|remains?)\b.{0,100}"
    r"\b(?:mound|earthwork|rise|[0-9]+(?:\.[0-9]+)?m\s+high)\b|"
    r"\b(?:mound|earthwork)\b.{0,100}\b(?:survives?|visible|[0-9]+(?:\.[0-9]+)?m\s+high)\b|"
    r"\b[0-9]+(?:\.[0-9]+)?m\s+high\b",
    re.I | re.S,
)


def assess_full_entry(*, reasons: str, details: str) -> EntryAssessment:
    """Apply the frozen E001 inclusion rubric to official full-entry sections.

    This is structured primary review, not an independent archaeological opinion.
    Ambiguity is deliberately sent to a human review queue.
    """
    reasons = " ".join(reasons.split())
    details = " ".join(details.split())
    combined = f"{reasons} {details}"
    codes: list[str] = []

    if not _BOWL.search(combined):
        return EntryAssessment(
            ReviewStatus.REJECTED,
            EvidenceValue.NO,
            EvidenceValue.UNCERTAIN,
            EvidenceValue.UNCERTAIN,
            ExclusionReason.NOT_BOWL_BARROW,
            ("identity:not_explicit",),
            "Official entry does not explicitly support bowl-barrow identity.",
        )
    codes.append("identity:explicit_bowl_barrow")

    if _CAIRN.search(details):
        return EntryAssessment(
            ReviewStatus.REJECTED,
            EvidenceValue.NO,
            EvidenceValue.YES,
            EvidenceValue.YES if _RELIEF.search(details) else EvidenceValue.UNCERTAIN,
            ExclusionReason.CAIRN,
            (*codes, "type:described_as_cairn"),
            "Details identify the scheduled feature as a cairn.",
        )
    opening_details = details[:700]
    if _MULTIPLE.search(opening_details) or _COMPOUND.search(opening_details):
        return EntryAssessment(
            ReviewStatus.REJECTED,
            EvidenceValue.YES,
            EvidenceValue.NO,
            EvidenceValue.YES if _RELIEF.search(details) else EvidenceValue.UNCERTAIN,
            ExclusionReason.COMPOUND_OR_MULTIPLE,
            (*codes, "monument:not_single"),
            "Details do not isolate one usable monument.",
        )
    codes.append("monument:single_supported")

    if _DESTROYED.search(details):
        return EntryAssessment(
            ReviewStatus.REJECTED,
            EvidenceValue.YES,
            EvidenceValue.YES,
            EvidenceValue.NO,
            ExclusionReason.DESTROYED_OR_RECONSTRUCTED,
            (*codes, "relief:destroyed_or_reconstructed"),
            "Details report destruction, complete removal, or reconstruction.",
        )
    if _LEVELLED.search(details):
        return EntryAssessment(
            ReviewStatus.REJECTED,
            EvidenceValue.YES,
            EvidenceValue.YES,
            EvidenceValue.NO,
            ExclusionReason.NO_UPSTANDING_RELIEF,
            (*codes, "relief:levelled"),
            "Details do not support surviving upstanding relief.",
        )
    if _CROPMARK.search(details) and not _RELIEF.search(details):
        return EntryAssessment(
            ReviewStatus.REJECTED,
            EvidenceValue.YES,
            EvidenceValue.YES,
            EvidenceValue.NO,
            ExclusionReason.CROPMARK_ONLY,
            (*codes, "relief:cropmark_only"),
            "Details support cropmark evidence only.",
        )
    if not _RELIEF.search(details):
        return EntryAssessment(
            ReviewStatus.UNCERTAIN,
            EvidenceValue.YES,
            EvidenceValue.YES,
            EvidenceValue.UNCERTAIN,
            ExclusionReason.INSUFFICIENT_EVIDENCE,
            (*codes, "relief:insufficient_evidence"),
            "Surviving upstanding morphology is not explicit enough.",
        )
    return EntryAssessment(
        ReviewStatus.NEEDS_GEOMETRY_REVIEW,
        EvidenceValue.YES,
        EvidenceValue.YES,
        EvidenceValue.YES,
        None,
        (*codes, "relief:upstanding_supported"),
        "Official entry supports one surviving upstanding bowl barrow.",
    )


def _rank(record: NhleRecord, seed: str) -> str:
    return hashlib.sha256(f"{seed}:{record.list_entry}".encode()).hexdigest()


def _grid_indices(group_id: str) -> tuple[int, int]:
    match = re.fullmatch(r"BNG_100KM_E(-?\d+)_N(-?\d+)", group_id)
    if match is None:
        raise ValueError(f"invalid 100 km grid ID: {group_id}")
    return int(match.group(1)), int(match.group(2))


def geographically_stratified_queue(
    records: Iterable[NhleRecord], *, size: int = 360, seed: str = QUEUE_SEED
) -> list[NhleRecord]:
    """Select a stable, geographically distributed probable-title review queue."""
    if size <= 0:
        raise ValueError("queue size must be positive")
    eligible = [r for r in records if triage_title(r.name).category is TriageCategory.PROBABLE_BOWL]
    if size > len(eligible):
        raise ValueError("queue size exceeds eligible records")
    groups: dict[str, list[NhleRecord]] = defaultdict(list)
    for record in eligible:
        groups[broad_grid_id(record.easting, record.northing)].append(record)
    for values in groups.values():
        values.sort(key=lambda record: _rank(record, seed))

    # Round-robin gives every occupied group a chance before any group dominates.
    ordered_groups = sorted(
        groups,
        key=lambda group: hashlib.sha256(f"{seed}:group:{group}".encode()).hexdigest(),
    )
    selected: list[NhleRecord] = []
    level = 0
    while len(selected) < size:
        progressed = False
        for group in ordered_groups:
            if level < len(groups[group]):
                selected.append(groups[group][level])
                progressed = True
                if len(selected) == size:
                    break
        if not progressed:
            raise AssertionError("eligible queue exhausted unexpectedly")
        level += 1
    return selected


def deterministic_second_review_ids(
    records: Sequence[CurationRecord], *, sample_size: int = 40
) -> list[int]:
    """Choose a reproducible status-stratified queue for an independent reviewer."""
    if sample_size < 0:
        raise ValueError("sample size must not be negative")
    accepted = [r for r in records if r.review_status is ReviewStatus.ACCEPTED]
    nonaccepted = [r for r in records if r.review_status is not ReviewStatus.ACCEPTED]
    each = sample_size // 2

    def ranked(values: list[CurationRecord], label: str) -> list[CurationRecord]:
        return sorted(
            values,
            key=lambda item: hashlib.sha256(
                f"{SECOND_REVIEW_SEED}:{label}:{item.list_entry}".encode()
            ).hexdigest(),
        )

    chosen = ranked(accepted, "accepted")[:each] + ranked(nonaccepted, "other")[:each]
    if len(chosen) < sample_size:
        used = {r.list_entry for r in chosen}
        remainder = [r for r in records if r.list_entry not in used]
        chosen.extend(ranked(remainder, "remainder")[: sample_size - len(chosen)])
    return [r.list_entry for r in chosen]


def select_nonadjacent_holdout_candidates(
    group_counts: Mapping[str, int], *, minimum_count: int = 15, limit: int = 4
) -> list[str]:
    """Select strong 100 km groups with no edge or corner adjacency."""
    candidates = sorted(
        ((group, count) for group, count in group_counts.items() if count >= minimum_count),
        key=lambda item: (-item[1], item[0]),
    )
    selected: list[str] = []
    for group, _count in candidates:
        easting, northing = _grid_indices(group)
        if all(
            max(abs(easting - other_e), abs(northing - other_n)) > 1
            for other_e, other_n in map(_grid_indices, selected)
        ):
            selected.append(group)
            if len(selected) == limit:
                break
    return selected


def summarize_records(records: Sequence[CurationRecord]) -> dict[str, Any]:
    """Return verified counts and coordinate-free group aggregates."""
    for record in records:
        record.validate()
    statuses = Counter(record.review_status for record in records)
    groups = Counter(
        record.geographic_group_id
        for record in records
        if record.review_status is ReviewStatus.ACCEPTED
    )
    reasons = Counter(
        record.exclusion_reason.value for record in records if record.exclusion_reason is not None
    )
    return {
        "records_reviewed": len(records),
        "accepted": statuses[ReviewStatus.ACCEPTED],
        "rejected": statuses[ReviewStatus.REJECTED],
        "uncertain": statuses[ReviewStatus.UNCERTAIN],
        "needs_geometry_review": statuses[ReviewStatus.NEEDS_GEOMETRY_REVIEW],
        "needs_terrain_review": statuses[ReviewStatus.NEEDS_TERRAIN_REVIEW],
        "accepted_by_group": dict(sorted(groups.items())),
        "exclusion_reasons": dict(sorted(reasons.items())),
    }


TRACKED_CURATION_FIELDS = (
    "list_entry",
    "review_status",
    "bowl_barrow_identity",
    "single_monument",
    "upstanding_earthwork",
    "geometry_qa",
    "terrain_coverage",
    "terrain_provenance",
    "geographic_group_id",
    "exclusion_reason",
    "evidence_codes",
    "reviewer_notes",
    "review_date",
    "source_access_date",
    "source_last_edit_at",
    "capture_scale",
    "terrain_year",
    "source_resolution_m",
    "survey_program",
    "second_review_required",
)

FORBIDDEN_TRACKED_FIELDS = frozenset(
    {"easting", "northing", "ngr", "latitude", "longitude", "geometry", "polygon", "bbox"}
)


def assert_coordinate_safe_fields(fields: Iterable[str]) -> None:
    normalized = {field.casefold() for field in fields}
    forbidden = normalized & FORBIDDEN_TRACKED_FIELDS
    if forbidden:
        raise ValueError(f"tracked output contains coordinate fields: {sorted(forbidden)}")
