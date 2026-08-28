"""Deterministic, uncertainty-aware E001 background sampling primitives."""

from __future__ import annotations

import csv
import hashlib
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

BACKGROUND_LABEL = "unlabelled_background"
BACKGROUND_ALGORITHM_VERSION = "e001-background-v1"
BACKGROUND_SEED = "E001-Phase-2C-2026-08-29"


@dataclass(frozen=True, slots=True)
class BackgroundSamplingPolicy:
    label: str = BACKGROUND_LABEL
    backgrounds_per_positive: int = 1
    positive_exclusion_buffer_m: float = 500.0
    known_archaeology_exclusion_buffer_m: float = 250.0
    minimum_sample_separation_m: float = 256.0
    sampling_radius_min_m: float = 1000.0
    sampling_radius_max_m: float = 5000.0
    deterministic_seed: str = BACKGROUND_SEED
    require_landscape_matching: bool = True
    require_survey_provenance_matching: bool = True
    require_geographic_group_assignment: bool = True
    require_modern_feature_screen: bool = True
    maximum_nodata_fraction: float = 0.2

    def __post_init__(self) -> None:
        if self.label != BACKGROUND_LABEL:
            raise ValueError("unknown terrain must be labelled unlabelled_background")
        if self.backgrounds_per_positive != 1:
            raise ValueError("the primary Phase 2C dataset freezes a 1:1 class ratio")
        if (
            min(
                self.positive_exclusion_buffer_m,
                self.known_archaeology_exclusion_buffer_m,
                self.minimum_sample_separation_m,
                self.sampling_radius_min_m,
            )
            <= 0
        ):
            raise ValueError("background distances must be positive")
        if self.sampling_radius_max_m <= self.sampling_radius_min_m:
            raise ValueError("background sampling radius must define a non-empty annulus")
        if not 0 <= self.maximum_nodata_fraction <= 1:
            raise ValueError("maximum_nodata_fraction must be between zero and one")


@dataclass(frozen=True, slots=True)
class CandidatePoint:
    easting: float
    northing: float
    attempt: int


@dataclass(frozen=True, slots=True)
class BackgroundIndexRecord:
    sample_id: str
    class_label: str
    observation_group_id: str
    geographic_group_id: str
    terrain_provenance_id: str
    survey_year: str
    source_resolution_m: float
    patch_size_m: int
    sampling_algorithm_version: str
    processing_version: str
    sampling_stratum: str
    acquisition_status: str
    raw_qa_status: str
    representation_qa_status: str
    qa_status: str
    raw_sha256: str
    patch_sha256: str
    processed_sha256: str
    cross_cell: bool


BACKGROUND_INDEX_FIELDS = tuple(BackgroundIndexRecord.__dataclass_fields__)


def opaque_background_id(positive_sample_id: str, attempt: int) -> str:
    if attempt < 1:
        raise ValueError("background candidate attempt must be positive")
    digest = hashlib.sha256(
        f"{BACKGROUND_ALGORITHM_VERSION}:{positive_sample_id}:{attempt}".encode()
    ).hexdigest()[:12]
    return f"E001B-{digest}"


def observation_group_id(identity: str) -> str:
    digest = hashlib.sha256(f"E001-observation-group-v1:{identity}".encode()).hexdigest()[:12]
    return f"E001G-{digest}"


def sampling_stratum_id(positive_sample_id: str) -> str:
    digest = hashlib.sha256(
        f"E001-background-stratum-v1:{positive_sample_id}".encode()
    ).hexdigest()[:12]
    return f"E001S-{digest}"


def generate_candidate(
    positive_sample_id: str,
    *,
    positive_centre: tuple[float, float],
    attempt: int,
    policy: BackgroundSamplingPolicy,
) -> CandidatePoint:
    """Generate a stable area-uniform point in the frozen sampling annulus."""
    if attempt < 1:
        raise ValueError("background candidate attempt must be positive")
    digest = hashlib.sha256(
        f"{policy.deterministic_seed}:{positive_sample_id}:{attempt}".encode()
    ).digest()
    unit_angle = int.from_bytes(digest[:8], "big") / 2**64
    unit_area = int.from_bytes(digest[8:16], "big") / 2**64
    angle = 2 * math.pi * unit_angle
    radius = math.sqrt(
        policy.sampling_radius_min_m**2
        + unit_area * (policy.sampling_radius_max_m**2 - policy.sampling_radius_min_m**2)
    )
    easting = round(positive_centre[0] + radius * math.cos(angle))
    northing = round(positive_centre[1] + radius * math.sin(angle))
    return CandidatePoint(float(easting), float(northing), attempt)


def geographic_group_id(centre: tuple[float, float]) -> str:
    easting, northing = centre
    return f"BNG_100KM_E{math.floor(easting / 100000)}_N{math.floor(northing / 100000)}"


def euclidean_distance(first: tuple[float, float], second: tuple[float, float]) -> float:
    return math.hypot(first[0] - second[0], first[1] - second[1])


def violates_minimum_distance(
    candidate: tuple[float, float],
    existing: tuple[tuple[float, float], ...],
    *,
    minimum_m: float,
) -> bool:
    return any(euclidean_distance(candidate, other) < minimum_m for other in existing)


def candidate_rejection_reason(
    candidate: tuple[float, float],
    *,
    expected_geographic_group_id: str,
    positive_centres: tuple[tuple[float, float], ...],
    background_centres: tuple[tuple[float, float], ...],
    known_scheduled_monument_present: bool,
    policy: BackgroundSamplingPolicy,
) -> str | None:
    """Return the first frozen spatial-policy violation for a candidate."""
    if geographic_group_id(candidate) != expected_geographic_group_id:
        return "outside_geographic_group"
    if violates_minimum_distance(
        candidate,
        positive_centres,
        minimum_m=policy.positive_exclusion_buffer_m,
    ):
        return "positive_exclusion"
    if violates_minimum_distance(
        candidate,
        background_centres,
        minimum_m=policy.minimum_sample_separation_m,
    ):
        return "too_close_background"
    if known_scheduled_monument_present:
        return "known_archaeology_exclusion"
    return None


def validate_background_index(records: list[BackgroundIndexRecord]) -> None:
    for record in records:
        assert_coordinate_safe_mapping(asdict(record))
        if record.class_label != BACKGROUND_LABEL:
            raise ValueError("background index must use unlabelled_background")
        if record.qa_status != "pass":
            raise ValueError("the frozen background index may contain only QA-passed records")
        if (
            record.acquisition_status != "verified"
            or record.raw_qa_status != "pass"
            or record.representation_qa_status != "pass"
        ):
            raise ValueError("background rows require all acquisition and QA gates")
        for checksum in (record.raw_sha256, record.patch_sha256, record.processed_sha256):
            if len(checksum) != 64 or any(
                character not in "0123456789abcdef" for character in checksum
            ):
                raise ValueError("background rows require lowercase SHA-256 digests")
    if len({record.sample_id for record in records}) != len(records):
        raise ValueError("duplicate background sample ID")
    if len({record.patch_sha256 for record in records}) != len(records):
        raise ValueError("duplicate exact background terrain")


def write_background_index(records: list[BackgroundIndexRecord], destination: Path) -> None:
    validate_background_index(records)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=BACKGROUND_INDEX_FIELDS)
        writer.writeheader()
        writer.writerows(asdict(record) for record in records)
