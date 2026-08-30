"""Construct the frozen multi-region E001 external dataset without model access."""

from __future__ import annotations

import argparse
import csv
import hashlib
import http.client
import json
import math
import time
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

from archaeoai.curation import (
    CurationRecord,
    EvidenceValue,
    ExclusionReason,
    QaStatus,
    ReviewStatus,
    assess_full_entry,
)
from archaeoai.external_validation import (
    EXPANSION_CELL_IDS,
    MINIMUM_EXTERNAL_SEPARATION_M,
    coarse_cell_id,
    distance_to_private_domain,
    selected_positive_ids,
    validate_expansion_amendment,
    validate_external_protocol,
)
from archaeoai.nhle_audit import (
    NHLE_QUERY_URL,
    NhleRecord,
    broad_grid_id,
    fetch_barrow_records,
    fetch_source_metadata,
)
from archaeoai.terrain.acquisition import (
    PrivateSiteLocation,
    WcsRequestError,
    fetch_wcs_payload,
    terrain_provenance_id,
)
from archaeoai.terrain.background import (
    BACKGROUND_LABEL,
    BackgroundSamplingPolicy,
    generate_candidate,
)
from archaeoai.terrain.full_dataset import (
    inspect_cached_artifacts,
    write_processed_archive,
)
from archaeoai.terrain.patches import patch_bounds
from archaeoai.terrain.privacy import (
    assert_coordinate_safe_mapping,
    ensure_private_output,
    verify_git_ignored,
)
from archaeoai.terrain.raster import extract_patch
from archaeoai.terrain.representations import terrain_representations
from archaeoai.terrain_metadata import (
    esri_geometry_qa,
    fetch_terrain_qa,
    patch_sample_points,
    point_in_ring,
)

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "configs/e001-phase-3a-external-validation.json"
AMENDMENT_PATH = ROOT / "configs/e001-phase-3b-r1-expansion-amendment.json"
FEASIBILITY_PRIVATE_PATH = ROOT / "data/private/e001/external/expansion/feasibility_manifest.json"
REVIEW_PATH = ROOT / "data/private/e001/external/expansion/full_entry_reviews.json"
MANUAL_DECISIONS_PATH = ROOT / "data/private/e001/external/expansion/manual_evidence_decisions.json"
SUPPLEMENTARY_CURATION_PATH = (
    ROOT / "data/private/e001/external/expansion/supplementary_curation_manifest.json"
)
FIRST_CURATION_PATH = ROOT / "data/private/e001/external/curation_manifest.json"
PRIVATE_DATASET_ROOT = ROOT / "data/private/e001/external/dataset"
CONSTRUCTION_STATE_PATH = PRIVATE_DATASET_ROOT / "construction_state.json"
PRIVATE_DATASET_MANIFEST_PATH = PRIVATE_DATASET_ROOT / "dataset_manifest.json"
PUBLIC_FREEZE_PATH = ROOT / "outputs/external_validation/e001_phase3b_external_dataset_freeze.json"
PRIVATE_POSITIVE_LOCATIONS = ROOT / "data/private/e001/approved-site-locations.json"
PRIVATE_BACKGROUND_STATE = ROOT / "data/private/e001/backgrounds/sampling_state.json"
PRIVATE_INFERENCE_DOMAIN = (
    ROOT / "data/private/e001/inference/controlled_domain_001/domain_receipt.json"
)
MODELLING_INDEX = ROOT / "outputs/dataset/e001_modelling_index.csv"
EXTERNAL_BACKGROUND_VERSION = "e001-external-background-v1"
EXTERNAL_DATASET_VERSION = "e001-external-dataset-v1"
PROCESSING_VERSION = "e001-terrain-v1"
FROZEN_BACKGROUND_SEED = "E001-Phase-3A-background-2026-08-30"
EA_COMPOSITE_EXTENTS_QUERY = (
    "https://environment.data.gov.uk/KB6uNVj5ZcJr7jUP/ArcGIS/rest/services/"
    "LIDAR_Composite_Catalogues/FeatureServer/2/query"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("curate", "construct"), required=True)
    parser.add_argument("--workers", type=int, default=6)
    return parser.parse_args()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _request_json(url: str, parameters: dict[str, str]) -> dict[str, Any]:
    request_url = f"{url}?{urllib.parse.urlencode(parameters)}"
    request = urllib.request.Request(
        request_url, headers={"User-Agent": "ArchaeoAI-external-construction/1"}
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                payload = json.load(response)
            if "error" in payload:
                raise RuntimeError(f"source service error: {payload['error']}")
            return payload
        except HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 3:
                raise
        except (URLError, TimeoutError, http.client.RemoteDisconnected):
            if attempt == 3:
                raise
        time.sleep(min(8, 2**attempt))
    raise AssertionError("official service retry loop terminated unexpectedly")


def _fetch_geometry(records: list[NhleRecord]) -> dict[int, dict[str, Any]]:
    results: dict[int, dict[str, Any]] = {}
    for start in range(0, len(records), 80):
        identifiers = ",".join(str(record.list_entry) for record in records[start : start + 80])
        payload = _request_json(
            NHLE_QUERY_URL,
            {
                "where": f"ListEntry IN ({identifiers})",
                "outFields": "ListEntry,Easting,Northing,CaptureScale,area_ha",
                "returnGeometry": "true",
                "outSR": "27700",
                "f": "json",
            },
        )
        for feature in payload.get("features", []):
            list_entry = int(feature["attributes"]["ListEntry"])
            if list_entry in results:
                results[list_entry]["duplicate_feature"] = True
            else:
                results[list_entry] = feature
    return results


def _map_terrain_reason(reason: str | None) -> ExclusionReason:
    mapping = {
        "terrain_no_1m_coverage": ExclusionReason.TERRAIN_NO_1M_COVERAGE,
        "terrain_patch_incomplete": ExclusionReason.TERRAIN_PATCH_INCOMPLETE,
        "terrain_provenance_missing": ExclusionReason.TERRAIN_PROVENANCE_MISSING,
        "terrain_provenance_confounded": ExclusionReason.TERRAIN_PROVENANCE_CONFOUNDED,
    }
    return mapping.get(reason, ExclusionReason.INSUFFICIENT_EVIDENCE)


def _map_geometry_reason(reason: str | None) -> ExclusionReason:
    mapping = {
        "geometry_compound": ExclusionReason.GEOMETRY_COMPOUND,
        "geometry_off_centre": ExclusionReason.GEOMETRY_OFF_CENTRE,
        "geometry_too_large": ExclusionReason.GEOMETRY_TOO_LARGE,
    }
    return mapping.get(reason, ExclusionReason.INSUFFICIENT_EVIDENCE)


def _manual_decisions() -> dict[int, dict[str, str]]:
    decisions = {int(row["list_entry"]): row for row in _load_json(MANUAL_DECISIONS_PATH)}
    if any(row.get("decision") != "upstanding_relief_supported" for row in decisions.values()):
        raise ValueError("unsupported supplementary manual-evidence decision")
    return decisions


def _new_curation_record(
    source: NhleRecord,
    review: dict[str, str],
    *,
    manual: dict[int, dict[str, str]],
    access_date: str,
    last_edit_at: str,
) -> CurationRecord:
    assessment = assess_full_entry(reasons=review["reasons"], details=review["details"])
    if source.list_entry in manual:
        if assessment.status is not ReviewStatus.UNCERTAIN:
            raise ValueError("manual-evidence decision does not resolve an uncertain rubric result")
        decision = manual[source.list_entry]
        return CurationRecord(
            list_entry=source.list_entry,
            review_status=ReviewStatus.NEEDS_GEOMETRY_REVIEW,
            bowl_barrow_identity=EvidenceValue.YES,
            single_monument=EvidenceValue.YES,
            upstanding_earthwork=EvidenceValue.YES,
            geographic_group_id=broad_grid_id(source.easting, source.northing),
            evidence_codes=(*assessment.evidence_codes, decision["evidence_code"]),
            reviewer_notes=decision["rationale"],
            review_date=review["checked_at"][:10],
            source_access_date=access_date,
            source_last_edit_at=last_edit_at,
            capture_scale=source.capture_scale or "UNAVAILABLE",
        )
    return CurationRecord(
        list_entry=source.list_entry,
        review_status=assessment.status,
        bowl_barrow_identity=assessment.identity,
        single_monument=assessment.single_monument,
        upstanding_earthwork=assessment.upstanding,
        geographic_group_id=broad_grid_id(source.easting, source.northing),
        exclusion_reason=assessment.reason,
        evidence_codes=assessment.evidence_codes,
        reviewer_notes=assessment.note,
        review_date=review["checked_at"][:10],
        source_access_date=access_date,
        source_last_edit_at=last_edit_at,
        capture_scale=source.capture_scale or "UNAVAILABLE",
    )


def _apply_geometry(
    records: list[CurationRecord],
    geometry: dict[int, dict[str, Any]],
) -> dict[int, tuple[float, float]]:
    centres: dict[int, tuple[float, float]] = {}
    for record in records:
        if record.review_status is not ReviewStatus.NEEDS_GEOMETRY_REVIEW:
            continue
        feature = geometry.get(record.list_entry)
        if feature is None:
            record.geometry_qa = QaStatus.NEEDS_REVIEW
            record.reviewer_notes = "Official designation geometry was unavailable."
            continue
        if feature.get("duplicate_feature"):
            record.geometry_qa = QaStatus.FAIL
            record.review_status = ReviewStatus.REJECTED
            record.exclusion_reason = ExclusionReason.GEOMETRY_COMPOUND
            record.reviewer_notes = "Multiple source geometry features require resolution."
            continue
        attributes = feature["attributes"]
        centre = (float(attributes["Easting"]), float(attributes["Northing"]))
        qa = esri_geometry_qa(
            feature.get("geometry", {}),
            centroid=centre,
            area_ha=float(attributes["area_ha"]) if attributes.get("area_ha") else None,
        )
        record.geometry_qa = QaStatus(qa.status)
        if qa.status == "pass":
            record.review_status = ReviewStatus.NEEDS_TERRAIN_REVIEW
            centres[record.list_entry] = centre
        elif qa.status == "fail":
            record.review_status = ReviewStatus.REJECTED
            record.exclusion_reason = _map_geometry_reason(qa.reason)
            record.reviewer_notes = f"Geometry QA failed: {qa.reason}."
        else:
            record.review_status = ReviewStatus.UNCERTAIN
            record.exclusion_reason = _map_geometry_reason(qa.reason)
            record.reviewer_notes = f"Geometry remains unresolved: {qa.reason}."
    return centres


def _apply_terrain(
    records: list[CurationRecord],
    centres: dict[int, tuple[float, float]],
    *,
    workers: int,
    frozen_fallback: dict[int, dict[str, Any]],
) -> tuple[dict[int, str], dict[int, str]]:
    by_id = {record.list_entry: record for record in records}
    errors: dict[int, str] = {}
    fallback_reuses: dict[int, str] = {}

    def apply_qa(record: CurationRecord, qa: Any) -> None:
        coverage_status = (
            str(qa["coverage_status"]) if isinstance(qa, dict) else str(qa.coverage_status)
        )
        provenance_status = (
            str(qa["provenance_status"]) if isinstance(qa, dict) else str(qa.provenance_status)
        )
        reason = qa.get("reason") if isinstance(qa, dict) else qa.reason
        year = qa.get("year") if isinstance(qa, dict) else qa.year
        resolution = qa.get("resolution_m") if isinstance(qa, dict) else qa.resolution_m
        programme = qa.get("programme") if isinstance(qa, dict) else qa.programme
        record.terrain_coverage = QaStatus(coverage_status)
        record.terrain_provenance = QaStatus(provenance_status)
        record.terrain_year = str(year or "UNAVAILABLE")
        record.source_resolution_m = str(resolution or "UNAVAILABLE")
        record.survey_program = str(programme or "UNAVAILABLE")
        if coverage_status != "pass":
            record.review_status = ReviewStatus.REJECTED
            record.exclusion_reason = _map_terrain_reason(reason)
            record.reviewer_notes = f"Terrain coverage QA failed: {reason}."
        elif provenance_status == "pass":
            record.review_status = ReviewStatus.ACCEPTED
            record.exclusion_reason = None
            record.reviewer_notes = "Passed full-entry, geometry, coverage, and provenance gates."
        else:
            record.review_status = ReviewStatus.NEEDS_TERRAIN_REVIEW
            record.exclusion_reason = _map_terrain_reason(reason)
            record.reviewer_notes = f"Terrain provenance requires review: {reason}."

    pending: dict[int, tuple[float, float]] = {}
    for list_entry, centre in centres.items():
        if list_entry in frozen_fallback:
            apply_qa(by_id[list_entry], frozen_fallback[list_entry])
            fallback_reuses[list_entry] = "hash_bound_precuration_feasibility_metadata"
        else:
            pending[list_entry] = centre
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_terrain_qa, centre, patch_size_m=128): list_entry
            for list_entry, centre in pending.items()
        }
        for future in as_completed(futures):
            list_entry = futures[future]
            record = by_id[list_entry]
            try:
                qa = future.result()
            except Exception as error:  # metadata outage remains unresolved, never a pass
                qa = frozen_fallback.get(list_entry)
                if qa is None:
                    record.terrain_coverage = QaStatus.NEEDS_REVIEW
                    record.terrain_provenance = QaStatus.NEEDS_REVIEW
                    record.review_status = ReviewStatus.NEEDS_TERRAIN_REVIEW
                    record.exclusion_reason = ExclusionReason.TERRAIN_PROVENANCE_MISSING
                    record.reviewer_notes = "Terrain metadata query requires retry."
                    errors[list_entry] = type(error).__name__
                    continue
                fallback_reuses[list_entry] = type(error).__name__
            apply_qa(record, qa)
    return errors, fallback_reuses


def _record_payload(
    record: CurationRecord,
    *,
    source: NhleRecord,
    centre: tuple[float, float] | None,
    cell_id: str,
) -> dict[str, Any]:
    payload = {
        "list_entry": record.list_entry,
        "title": source.name,
        "easting": centre[0] if centre else source.easting,
        "northing": centre[1] if centre else source.northing,
        "coarse_external_cell": cell_id,
        "review_status": record.review_status.value,
        "bowl_barrow_identity": record.bowl_barrow_identity.value,
        "single_monument": record.single_monument.value,
        "upstanding_earthwork": record.upstanding_earthwork.value,
        "geometry_qa": record.geometry_qa.value,
        "terrain_coverage": record.terrain_coverage.value,
        "terrain_provenance": record.terrain_provenance.value,
        "terrain_year": record.terrain_year,
        "source_resolution_m": record.source_resolution_m,
        "survey_program": record.survey_program,
        "terrain_provenance_id": terrain_provenance_id(
            record.terrain_year, record.source_resolution_m, record.survey_program
        )
        if record.terrain_provenance is QaStatus.PASS
        else None,
        "exclusion_reason": record.exclusion_reason.value if record.exclusion_reason else None,
        "evidence_codes": list(record.evidence_codes),
        "reviewer_notes": record.reviewer_notes,
        "source_access_date": record.source_access_date,
        "source_last_edit_at": record.source_last_edit_at,
    }
    return payload


def curate_supplementary(*, workers: int) -> dict[str, Any]:
    protocol = validate_external_protocol(PROTOCOL_PATH)
    amendment = validate_expansion_amendment(AMENDMENT_PATH)
    feasibility = _load_json(FEASIBILITY_PRIVATE_PATH)
    selected_cells = tuple(feasibility["selected_cells"])
    if selected_cells != EXPANSION_CELL_IDS:
        raise ValueError("private feasibility selection differs from the frozen amendment")
    private_rows = [row for row in feasibility["records"] if row["cell_id"] in selected_cells]
    if len(private_rows) != 33:
        raise ValueError("supplementary private feasibility pool must contain 33 records")
    expected_ids = {int(row["list_entry"]) for row in private_rows}
    public_feasibility = _load_json(
        ROOT / "outputs/external_validation/e001_phase3b_r1_expansion_feasibility.json"
    )
    if (
        hashlib.sha256(FEASIBILITY_PRIVATE_PATH.read_bytes()).hexdigest()
        != public_feasibility["privacy"]["private_manifest_sha256"]
    ):
        raise ValueError("private expansion feasibility manifest hash mismatch")
    reviews = {int(row["list_entry"]): row for row in _load_json(REVIEW_PATH)}
    if set(reviews) != expected_ids:
        raise ValueError("supplementary full-entry review cache does not match the frozen pool")
    sources = {record.list_entry: record for record in fetch_barrow_records()}
    if not expected_ids.issubset(sources):
        raise ValueError("official NHLE metadata no longer contains every frozen record")
    selected_sources = [sources[list_entry] for list_entry in sorted(expected_ids)]
    _service, layer = fetch_source_metadata()
    last_edit_ms = layer.get("editingInfo", {}).get("lastEditDate")
    last_edit_at = (
        datetime.fromtimestamp(last_edit_ms / 1000, tz=UTC).isoformat()
        if last_edit_ms is not None
        else "UNAVAILABLE"
    )
    access_date = datetime.now(UTC).date().isoformat()
    manual = _manual_decisions()
    records = [
        _new_curation_record(
            source,
            reviews[source.list_entry],
            manual=manual,
            access_date=access_date,
            last_edit_at=last_edit_at,
        )
        for source in selected_sources
    ]
    geometry = _fetch_geometry(selected_sources)
    centres = _apply_geometry(records, geometry)
    frozen_terrain = {
        int(row["list_entry"]): row["terrain_qa"]
        for row in private_rows
        if row.get("terrain_qa") is not None
    }
    errors, fallback_reuses = _apply_terrain(
        records,
        centres,
        workers=workers,
        frozen_fallback=frozen_terrain,
    )
    for record in records:
        record.validate()
    cell_by_id = {int(row["list_entry"]): row["cell_id"] for row in private_rows}
    private_payload = {
        "schema_version": "e001-phase-3b-r1-supplementary-curation-v1",
        "stage": "curation",
        "warning": "PRIVATE: official-entry evidence and exact coordinates; never publish",
        "protocol_sha256": protocol["protocol_sha256"],
        "amendment_sha256": amendment["amendment_sha256"],
        "full_entry_review_sha256": hashlib.sha256(REVIEW_PATH.read_bytes()).hexdigest(),
        "reviewed_at": datetime.now(UTC).isoformat(),
        "external_RF_scoring_performed": False,
        "external_performance_metrics_computed": False,
        "records": [
            _record_payload(
                record,
                source=sources[record.list_entry],
                centre=centres.get(record.list_entry),
                cell_id=cell_by_id[record.list_entry],
            )
            for record in records
        ],
        "metadata_query_errors": errors,
        "frozen_feasibility_metadata_reused": fallback_reuses,
    }
    destination = ensure_private_output(ROOT, SUPPLEMENTARY_CURATION_PATH)
    verify_git_ignored(ROOT, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(private_payload, indent=2) + "\n", encoding="utf-8")
    statuses = Counter(record.review_status.value for record in records)
    summary = {
        "records_reviewed": len(records),
        "accepted": statuses[ReviewStatus.ACCEPTED.value],
        "rejected": statuses[ReviewStatus.REJECTED.value],
        "uncertain": statuses[ReviewStatus.UNCERTAIN.value],
        "needs_terrain_review": statuses[ReviewStatus.NEEDS_TERRAIN_REVIEW.value],
        "supplementary_curation_manifest_sha256": hashlib.sha256(
            destination.read_bytes()
        ).hexdigest(),
        "external_RF_scoring_performed": False,
        "external_performance_metrics_computed": False,
    }
    print(json.dumps(summary, indent=2))
    return summary


def _canonical_sha256(payload: dict[str, Any], *, omit: str) -> str:
    content = {key: value for key, value in payload.items() if key != omit}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _write_private_json(path: Path, payload: dict[str, Any]) -> None:
    destination = ensure_private_output(ROOT, path)
    verify_git_ignored(ROOT, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".partial.json")
    temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)


def _opaque_id(prefix: str, identity: str) -> str:
    digest = hashlib.sha256(f"{EXTERNAL_DATASET_VERSION}:{identity}".encode()).hexdigest()[:12]
    return f"EXT-{prefix}-{digest}"


def _accepted_records() -> list[dict[str, Any]]:
    first = _load_json(FIRST_CURATION_PATH)
    supplementary = _load_json(SUPPLEMENTARY_CURATION_PATH)
    if first.get("external_RF_scoring_performed") or supplementary.get(
        "external_RF_scoring_performed"
    ):
        raise ValueError("external curation state crossed the no-score boundary")
    accepted = [
        row
        for row in (*first["records"], *supplementary["records"])
        if row["review_status"] == ReviewStatus.ACCEPTED.value
    ]
    if len(accepted) != 76:
        raise ValueError("combined accepted external count changed from 76")
    for row in accepted:
        row.setdefault("coarse_external_cell", "BNG_25KM_E16_N5")
        row.setdefault(
            "terrain_provenance_id",
            terrain_provenance_id(
                str(row["terrain_year"]),
                str(row["source_resolution_m"]),
                str(row["survey_program"]),
            ),
        )
    return accepted


def _prior_centres() -> tuple[tuple[float, float], ...]:
    positive = _load_json(PRIVATE_POSITIVE_LOCATIONS)["records"]
    background = _load_json(PRIVATE_BACKGROUND_STATE)["records"].values()
    centres = [(float(row["easting"]), float(row["northing"])) for row in positive]
    centres.extend(
        (float(row["easting"]), float(row["northing"]))
        for row in background
        if isinstance(row, dict) and "easting" in row
    )
    if len(centres) != 522:
        raise ValueError("E001 independence audit requires all 522 prior observations")
    return tuple(centres)


def _private_domain_extent() -> tuple[float, float, float, float]:
    receipt = _load_json(PRIVATE_INFERENCE_DOMAIN)
    return tuple(float(receipt[key]) for key in ("left", "bottom", "right", "top"))  # type: ignore[return-value]


def _assert_independent(
    point: tuple[float, float],
    *,
    prior_centres: tuple[tuple[float, float], ...],
    private_domain: tuple[float, float, float, float],
) -> None:
    if min(math.dist(point, centre) for centre in prior_centres) < MINIMUM_EXTERNAL_SEPARATION_M:
        raise ValueError("external observation violates the 15 km E001 exclusion")
    if distance_to_private_domain(point, private_domain) < MINIMUM_EXTERNAL_SEPARATION_M:
        raise ValueError("external observation violates the 15 km Phase 2F exclusion")


def _known_archaeology_count(centre: tuple[float, float], *, exclusion_m: float) -> int:
    easting, northing = centre
    payload = _request_json(
        NHLE_QUERY_URL,
        {
            "geometry": (
                f"{easting - exclusion_m:g},{northing - exclusion_m:g},"
                f"{easting + exclusion_m:g},{northing + exclusion_m:g}"
            ),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "27700",
            "spatialRel": "esriSpatialRelIntersects",
            "returnCountOnly": "true",
            "f": "json",
        },
    )
    count = payload.get("count")
    if isinstance(count, bool) or not isinstance(count, int):
        raise RuntimeError("official Scheduled Monument exclusion query omitted its count")
    return count


def _matching_terrain(
    centre: tuple[float, float], *, expected_provenance_id: str
) -> tuple[bool, Any]:
    half = 64
    easting, northing = centre
    payload = _request_json(
        EA_COMPOSITE_EXTENTS_QUERY,
        {
            "geometry": (
                f"{easting - half:g},{northing - half:g},{easting + half:g},{northing + half:g}"
            ),
            "geometryType": "esriGeometryEnvelope",
            "inSR": "27700",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "polygon_id,year,resolution,sd_flown,ed_flown,od_dtm_fn",
            "returnGeometry": "true",
            "outSR": "27700",
            "f": "json",
        },
    )
    points = patch_sample_points(centre, patch_size_m=128)
    relevant = []
    for feature in payload.get("features", []):
        rings = feature.get("geometry", {}).get("rings", [])
        if any(any(point_in_ring(point, ring) for ring in rings) for point in points):
            relevant.append(feature)
    coverage = bool(relevant) and all(
        any(
            any(point_in_ring(point, ring) for ring in feature.get("geometry", {}).get("rings", []))
            for feature in relevant
        )
        for point in points
    )
    signatures = {
        (
            str(feature["attributes"].get("polygon_id") or ""),
            str(feature["attributes"].get("year") or ""),
            str(feature["attributes"].get("resolution") or ""),
            str(feature["attributes"].get("sd_flown") or ""),
            str(feature["attributes"].get("ed_flown") or ""),
            str(feature["attributes"].get("od_dtm_fn") or ""),
        )
        for feature in relevant
    }
    if not coverage or len(signatures) != 1:
        return False, None
    _polygon, year, resolution, _start, _end, filename = next(iter(signatures))
    resolution = f"{float(resolution):g}"
    programme = (
        "National LIDAR Programme"
        if filename.casefold().startswith("np ")
        else "EA Composite source survey"
    )
    qa = type(
        "TerrainMatch",
        (),
        {"year": year, "resolution_m": resolution, "programme": programme},
    )()
    matches = (
        float(resolution) <= 1
        and terrain_provenance_id(year, resolution, programme) == expected_provenance_id
    )
    return matches, qa


def _new_construction_state(selected: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "e001-phase-3b-private-construction-state-v1",
        "dataset_version": EXTERNAL_DATASET_VERSION,
        "warning": "PRIVATE: coordinates and terrain paths; never publish",
        "records": {
            str(row["list_entry"]): {
                "list_entry": int(row["list_entry"]),
                "positive_sample_id": _opaque_id("P", str(row["list_entry"])),
                "positive_easting": float(row["easting"]),
                "positive_northing": float(row["northing"]),
                "coarse_external_cell": row["coarse_external_cell"],
                "terrain_year": str(row["terrain_year"]),
                "source_resolution_m": str(row["source_resolution_m"]),
                "survey_program": str(row["survey_program"]),
                "terrain_provenance_id": row["terrain_provenance_id"],
            }
            for row in selected
        },
        "candidate_attempts": 0,
        "candidate_rejections": {},
        "external_RF_scoring_performed": False,
        "external_performance_metrics_computed": False,
    }


def _load_or_create_state(selected: list[dict[str, Any]]) -> dict[str, Any]:
    expected_ids = {str(row["list_entry"]) for row in selected}
    if CONSTRUCTION_STATE_PATH.exists():
        state = _load_json(CONSTRUCTION_STATE_PATH)
        if state.get("schema_version") != "e001-phase-3b-private-construction-state-v1":
            raise ValueError("unexpected external construction-state schema")
        if set(state["records"]) != expected_ids:
            raise ValueError("resumed external construction state has a changed selection")
        return state
    state = _new_construction_state(selected)
    _write_private_json(CONSTRUCTION_STATE_PATH, state)
    return state


def _record_rejection(state: dict[str, Any], reason: str) -> None:
    state["candidate_attempts"] += 1
    counts = state["candidate_rejections"]
    counts[reason] = int(counts.get(reason, 0)) + 1


def _bind_backgrounds(
    state: dict[str, Any],
    *,
    prior_centres: tuple[tuple[float, float], ...],
    private_domain: tuple[float, float, float, float],
) -> None:
    policy = BackgroundSamplingPolicy(deterministic_seed=FROZEN_BACKGROUND_SEED)
    records = list(state["records"].values())
    positive_centres = tuple(
        (float(row["positive_easting"]), float(row["positive_northing"])) for row in records
    )
    existing_backgrounds = [
        (float(row["background_easting"]), float(row["background_northing"]))
        for row in records
        if "background_easting" in row
    ]
    for completed, row in enumerate(records, start=1):
        positive = (float(row["positive_easting"]), float(row["positive_northing"]))
        _assert_independent(positive, prior_centres=prior_centres, private_domain=private_domain)
        if "background_easting" in row:
            continue
        for attempt in range(int(row.get("next_attempt", 1)), 2001):
            candidate = generate_candidate(
                str(row["positive_sample_id"]),
                positive_centre=positive,
                attempt=attempt,
                policy=policy,
            )
            centre = (candidate.easting, candidate.northing)
            reason = None
            if coarse_cell_id(centre) != row["coarse_external_cell"]:
                reason = "outside_25km_cell"
            elif any(math.dist(centre, point) < 500 for point in positive_centres):
                reason = "positive_exclusion"
            elif any(math.dist(centre, point) < 256 for point in existing_backgrounds):
                reason = "background_separation"
            elif min(math.dist(centre, point) for point in prior_centres) < 15_000:
                reason = "E001_exclusion"
            elif distance_to_private_domain(centre, private_domain) < 15_000:
                reason = "phase2f_exclusion"
            elif _known_archaeology_count(centre, exclusion_m=250):
                reason = "known_scheduled_monument_exclusion"
            if reason is None:
                matches, qa = _matching_terrain(
                    centre, expected_provenance_id=str(row["terrain_provenance_id"])
                )
                if not matches:
                    reason = "terrain_provenance_mismatch"
            if reason is None:
                row.update(
                    {
                        "background_sample_id": _opaque_id(
                            "B", f"{row['positive_sample_id']}:{attempt}"
                        ),
                        "pair_id": _opaque_id("G", str(row["list_entry"])),
                        "background_easting": centre[0],
                        "background_northing": centre[1],
                        "background_attempt": attempt,
                        "background_terrain_year": str(qa.year),
                        "background_survey_program": str(qa.programme),
                    }
                )
                state["candidate_attempts"] += 1
                existing_backgrounds.append(centre)
                _write_private_json(CONSTRUCTION_STATE_PATH, state)
                print(f"background={completed}/60 attempt={attempt}", flush=True)
                break
            _record_rejection(state, reason)
            row["next_attempt"] = attempt + 1
            _write_private_json(CONSTRUCTION_STATE_PATH, state)
        else:
            raise RuntimeError(f"background attempts exhausted for {row['positive_sample_id']}")


def _process_terrain(row: dict[str, Any], *, role: str) -> dict[str, Any]:
    sample_id = str(row[f"{role}_sample_id"])
    centre = (float(row[f"{role}_easting"]), float(row[f"{role}_northing"]))
    raw_path = PRIVATE_DATASET_ROOT / "raw" / f"{sample_id}.tif"
    processed_path = PRIVATE_DATASET_ROOT / "processed" / f"{sample_id}.npz"
    location = PrivateSiteLocation(
        list_entry=int(row["list_entry"]) if role == "positive" else 0,
        easting=centre[0],
        northing=centre[1],
        geographic_group_id=str(row["coarse_external_cell"]),
        terrain_year=str(
            row["terrain_year"] if role == "positive" else row["background_terrain_year"]
        ),
        source_resolution_m="1",
        survey_program=str(
            row["survey_program"] if role == "positive" else row["background_survey_program"]
        ),
    )
    expected_raw = str(row.get(f"{role}_raw_sha256") or "") or None
    inspection = inspect_cached_artifacts(
        raw_path=raw_path,
        processed_path=processed_path,
        location=location,
        expected_raw_sha256=expected_raw,
    )
    action = "cache_verified"
    if inspection.status not in {"valid", "processed_missing"}:
        if raw_path.exists():
            raise ValueError(f"private cached terrain failed QA: {sample_id}:{inspection.status}")
        bounds = patch_bounds(centre, patch_size_m=128, resolution_m=1)
        payload = fetch_wcs_payload(bounds)
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        verify_git_ignored(ROOT, raw_path)
        temporary = raw_path.with_name(f"{raw_path.stem}.partial.tif")
        verify_git_ignored(ROOT, temporary)
        temporary.write_bytes(payload.content)
        patch = extract_patch(
            [temporary],
            centre=centre,
            patch_size_m=128,
            resolution_m=1,
            max_nodata_fraction=0.2,
        )
        temporary.replace(raw_path)
        representations = terrain_representations(
            patch.data, resolution_m=1, mask=patch.mask, local_relief_radius_m=16
        )
        processed_sha = write_processed_archive(
            processed_path,
            patch=patch,
            representations=representations,
            project_root=ROOT,
        )
        inspection = inspect_cached_artifacts(
            raw_path=raw_path,
            processed_path=processed_path,
            location=location,
            expected_raw_sha256=payload.sha256,
        )
        action = "downloaded"
        if inspection.status != "valid" or inspection.processed_sha256 != processed_sha:
            raise ValueError(f"downloaded external terrain failed deterministic QA: {sample_id}")
    elif inspection.status == "processed_missing":
        if inspection.patch is None or inspection.representations is None:
            raise AssertionError("processed regeneration lacks verified source terrain")
        write_processed_archive(
            processed_path,
            patch=inspection.patch,
            representations=inspection.representations,
            project_root=ROOT,
        )
        inspection = inspect_cached_artifacts(
            raw_path=raw_path,
            processed_path=processed_path,
            location=location,
            expected_raw_sha256=inspection.raw_sha256,
        )
        action = "processed_regenerated"
    if (
        inspection.status != "valid"
        or inspection.patch is None
        or inspection.representations is None
    ):
        raise ValueError(f"external terrain cache is not valid: {sample_id}")
    representation_sha = {
        name: hashlib.sha256(values.astype("<f4").tobytes()).hexdigest()
        for name, values in inspection.representations.items()
    }
    return {
        "sample_id": sample_id,
        "role": role,
        "class_label": "positive_bowl_barrow" if role == "positive" else BACKGROUND_LABEL,
        "pair_id": row["pair_id"],
        "easting": centre[0],
        "northing": centre[1],
        "coarse_external_cell": row["coarse_external_cell"],
        "terrain_year": location.terrain_year,
        "source_resolution_m": 1.0,
        "survey_program": location.survey_program,
        "terrain_provenance_id": terrain_provenance_id(
            location.terrain_year, "1", location.survey_program
        ),
        "raw_path": str(raw_path.relative_to(ROOT)),
        "processed_path": str(processed_path.relative_to(ROOT)),
        "raw_sha256": inspection.raw_sha256,
        "patch_sha256": inspection.patch_sha256,
        "processed_sha256": inspection.processed_sha256,
        "representation_sha256": representation_sha,
        "nodata_fraction": float(inspection.patch.mask.mean()),
        "shape": list(inspection.patch.data.shape),
        "resolution_m": 1.0,
        "crs": "EPSG:27700",
        "action": action,
        "qa_status": "pass",
    }


def _process_terrain_resilient(row: dict[str, Any], *, role: str) -> dict[str, Any]:
    """Retry only transient official WCS delivery failures for one frozen observation."""
    for delivery_round in range(1, 13):
        try:
            return _process_terrain(row, role=role)
        except (PermissionError, WcsRequestError):
            if delivery_round == 12:
                raise
            time.sleep(20)
    raise AssertionError("terrain delivery retry loop terminated unexpectedly")


def _terrain_overlaps(first: dict[str, Any], second: dict[str, Any]) -> bool:
    return (
        abs(float(first["easting"]) - float(second["easting"])) < 128
        and abs(float(first["northing"]) - float(second["northing"])) < 128
    )


def _freeze_dataset(state: dict[str, Any], observations: list[dict[str, Any]]) -> dict[str, Any]:
    if len(observations) != 120:
        raise ValueError("external dataset must contain exactly 120 observations")
    labels = Counter(row["class_label"] for row in observations)
    if labels != {"positive_bowl_barrow": 60, BACKGROUND_LABEL: 60}:
        raise ValueError("external dataset must contain 60 matched pairs")
    sample_ids = [row["sample_id"] for row in observations]
    patch_hashes = [row["patch_sha256"] for row in observations]
    centres = [(row["easting"], row["northing"]) for row in observations]
    if len(set(sample_ids)) != 120:
        raise ValueError("external sample-ID collision")
    if len(set(patch_hashes)) != 120:
        raise ValueError("external duplicate terrain content")
    if len(set(centres)) != 120:
        raise ValueError("external centre collision")
    with MODELLING_INDEX.open(encoding="utf-8", newline="") as file:
        prior_rows = list(csv.DictReader(file))
    prior_ids = {row["sample_id"] for row in prior_rows}
    prior_patch_hashes = {row["patch_sha256"] for row in prior_rows}
    if prior_ids.intersection(sample_ids):
        raise ValueError("external sample ID collides with E001")
    if prior_patch_hashes.intersection(patch_hashes):
        raise ValueError("external terrain content duplicates E001")
    pair_counts = Counter(row["pair_id"] for row in observations)
    if len(pair_counts) != 60 or set(pair_counts.values()) != {2}:
        raise ValueError("external observations are not one-to-one matched pairs")
    within_overlap_count = sum(
        _terrain_overlaps(observations[first], observations[second])
        for first in range(len(observations))
        for second in range(first + 1, len(observations))
    )
    overlap_roles = Counter(
        tuple(sorted((observations[first]["role"], observations[second]["role"])))
        for first in range(len(observations))
        for second in range(first + 1, len(observations))
        if _terrain_overlaps(observations[first], observations[second])
    )
    if overlap_roles != {("positive", "positive"): 5}:
        raise ValueError("external internal-overlap composition changed")
    manifest: dict[str, Any] = {
        "schema_version": "e001-phase-3b-private-external-dataset-v1",
        "dataset_version": EXTERNAL_DATASET_VERSION,
        "warning": "PRIVATE: coordinates, terrain paths, and row-level labels; never publish",
        "status": "READY_UNSCORED",
        "protocol_sha256": validate_external_protocol(PROTOCOL_PATH)["protocol_sha256"],
        "amendment_sha256": validate_expansion_amendment(AMENDMENT_PATH)["amendment_sha256"],
        "processing_version": PROCESSING_VERSION,
        "observations": sorted(observations, key=lambda row: row["sample_id"]),
        "external_RF_scoring_performed": False,
        "external_performance_metrics_computed": False,
    }
    manifest["dataset_sha256"] = _canonical_sha256(manifest, omit="dataset_sha256")
    _write_private_json(PRIVATE_DATASET_MANIFEST_PATH, manifest)
    private_manifest_sha = hashlib.sha256(PRIVATE_DATASET_MANIFEST_PATH.read_bytes()).hexdigest()
    region_positive = Counter(
        row["coarse_external_cell"]
        for row in observations
        if row["class_label"] == "positive_bowl_barrow"
    )
    region_background = Counter(
        row["coarse_external_cell"]
        for row in observations
        if row["class_label"] == BACKGROUND_LABEL
    )
    years = Counter(str(row["terrain_year"]) for row in observations)
    programmes = Counter(str(row["survey_program"]) for row in observations)
    actions = Counter(str(row["action"]) for row in observations)
    receipt: dict[str, Any] = {
        "schema_version": "e001-phase-3b-external-dataset-freeze-v1",
        "phase": "3B multi-region external dataset construction",
        "status": "READY_UNSCORED",
        "frozen": True,
        "protocol_sha256": manifest["protocol_sha256"],
        "amendment_sha256": manifest["amendment_sha256"],
        "curation": {
            "supplementary_records_reviewed": 33,
            "supplementary_accepted": 29,
            "supplementary_rejected": 2,
            "supplementary_uncertain": 0,
            "supplementary_needs_terrain_review": 2,
            "combined_accepted": 76,
            "selection_method": "frozen_SHA256_ranking_without_model_output",
        },
        "counts": {
            "positive_bowl_barrow": 60,
            BACKGROUND_LABEL: 60,
            "total_observations": 120,
            "matched_pairs": 60,
        },
        "region_composition": {
            cell: {
                "positive_bowl_barrow": region_positive[cell],
                BACKGROUND_LABEL: region_background[cell],
            }
            for cell in sorted(region_positive)
        },
        "terrain": {
            "source": "Environment Agency LiDAR Composite DTM 1m",
            "license": "Open Government Licence v3.0",
            "crs": "EPSG:27700",
            "resolution_m": 1.0,
            "patch_dimensions": [128, 128],
            "patch_size_m": 128,
            "raw_QA_passed": 120,
            "representation_QA_passed": 120,
            "actions": dict(sorted(actions.items())),
            "survey_years": dict(sorted(years.items())),
            "survey_programmes": dict(sorted(programmes.items())),
            "checksums_complete": True,
        },
        "representations": {
            "names": [
                "elevation_normalized",
                "slope_degrees",
                "hillshade_315_45",
                "local_relief_r16m",
            ],
            "complete_observations": 120,
            "preprocessing_changed": False,
        },
        "background_policy": {
            "label_interpretation": "unlabelled terrain, not a known negative",
            "matching": "same 25 km cell and exact terrain provenance",
            "sampling_annulus_m": [1000, 5000],
            "positive_exclusion_m": 500,
            "known_scheduled_monument_exclusion_m": 250,
            "background_separation_m": 256,
            "deterministic_seed": FROZEN_BACKGROUND_SEED,
        },
        "independence": {
            "E001_observations_audited": 522,
            "minimum_E001_separation_m": 15_000,
            "phase2D_phase2E_geography_independent": True,
            "phase2F_private_domain_minimum_separation_m": 15_000,
            "phase2F_independent": True,
            "sample_ID_collisions": 0,
            "centre_collisions": 0,
            "E001_content_duplicates": 0,
            "external_content_duplicates": 0,
            "positive_background_content_duplicates": 0,
            "internal_terrain_window_overlaps": within_overlap_count,
            "internal_overlap_composition": {"positive_positive": 5},
            "internal_overlap_protocol_status": (
                "permitted_distinct_positives; prior-study and background spacing gates pass"
            ),
        },
        "privacy": {
            "private_manifest_ignored": True,
            "private_manifest_sha256": private_manifest_sha,
            "coordinates_tracked": False,
            "raw_or_processed_terrain_tracked": False,
        },
        "dataset_sha256": manifest["dataset_sha256"],
        "execution_state": {
            "external_dataset_frozen": True,
            "external_RF_loaded": False,
            "predict_called": False,
            "predict_proba_called": False,
            "external_RF_scoring_performed": False,
            "external_performance_metrics_computed": False,
        },
    }
    assert_coordinate_safe_mapping(receipt)
    receipt["freeze_receipt_sha256"] = _canonical_sha256(receipt, omit="freeze_receipt_sha256")
    PUBLIC_FREEZE_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_FREEZE_PATH.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def construct_dataset(*, workers: int) -> dict[str, Any]:
    validate_external_protocol(PROTOCOL_PATH)
    amendment = validate_expansion_amendment(AMENDMENT_PATH)
    if amendment["amendment_sha256"] != (
        "330263472d6b947fa688cbe6a21a52f437fc7c206555a023b7e64900c7bf13f9"
    ):
        raise ValueError("frozen Phase 3B-R1 amendment changed")
    accepted = _accepted_records()
    selected_ids = set(selected_positive_ids(row["list_entry"] for row in accepted))
    selected = [row for row in accepted if str(row["list_entry"]) in selected_ids]
    if len(selected) != 60:
        raise ValueError("frozen deterministic selection did not yield 60 positives")
    state = _load_or_create_state(selected)
    if state.get("external_RF_scoring_performed") or state.get(
        "external_performance_metrics_computed"
    ):
        raise ValueError("private construction state crossed the no-score boundary")
    prior_centres = _prior_centres()
    private_domain = _private_domain_extent()
    _bind_backgrounds(state, prior_centres=prior_centres, private_domain=private_domain)
    observations: list[dict[str, Any]] = []
    records = list(state["records"].values())
    pending: dict[Any, tuple[dict[str, Any], str]] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for row in records:
            for role in ("positive", "background"):
                cached = row.get(f"{role}_terrain")
                if isinstance(cached, dict) and cached.get("qa_status") == "pass":
                    observations.append(cached)
                else:
                    pending[executor.submit(_process_terrain_resilient, row, role=role)] = (
                        row,
                        role,
                    )
        completed = len(observations)
        for future in as_completed(pending):
            row, role = pending[future]
            cached = future.result()
            row[f"{role}_terrain"] = cached
            observations.append(cached)
            completed += 1
            _write_private_json(CONSTRUCTION_STATE_PATH, state)
            print(f"terrain_observation={completed}/120", flush=True)
    for row in records:
        for role in ("positive", "background"):
            cached = row.get(f"{role}_terrain")
            if not isinstance(cached, dict) or cached.get("qa_status") != "pass":
                raise ValueError("external terrain construction ended with an incomplete record")
    receipt = _freeze_dataset(state, observations)
    print(json.dumps(receipt, indent=2))
    return receipt


def main() -> int:
    args = parse_args()
    if not 1 <= args.workers <= 8:
        raise SystemExit("--workers must be between 1 and 8")
    if args.stage == "curate":
        curate_supplementary(workers=args.workers)
        return 0
    if args.stage == "construct":
        construct_dataset(workers=args.workers)
        return 0
    raise AssertionError("unreachable stage")


if __name__ == "__main__":
    raise SystemExit(main())
