"""Run the coordinate-safe E001 Phase 2A.5 curation and terrain metadata gate."""

from __future__ import annotations

import argparse
import csv
import json
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from archaeoai.curation import (
    CURATION_VERSION,
    QUEUE_SEED,
    TRACKED_CURATION_FIELDS,
    CurationRecord,
    ExclusionReason,
    QaStatus,
    ReviewStatus,
    assert_coordinate_safe_fields,
    assess_full_entry,
    deterministic_second_review_ids,
    geographically_stratified_queue,
    select_nonadjacent_holdout_candidates,
    summarize_records,
)
from archaeoai.nhle_audit import (
    NHLE_LAYER_URL,
    NHLE_QUERY_URL,
    NhleRecord,
    broad_grid_id,
    fetch_barrow_records,
    fetch_source_metadata,
)
from archaeoai.terrain_metadata import esri_geometry_qa, fetch_terrain_qa

OUTPUT_DIR = Path("outputs/feasibility")
PRIVATE_REVIEW_DEFAULT = Path("data/private/e001_full_entry_reviews.json")
MINIMUM_VIABLE_GROUP_SITES = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-json", type=Path, default=PRIVATE_REVIEW_DEFAULT)
    parser.add_argument("--queue-size", type=int, default=360)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    parser.add_argument("--terrain-workers", type=int, default=6)
    parser.add_argument(
        "--print-queue",
        action="store_true",
        help="Print the deterministic queue as JSON and stop before review or spatial queries.",
    )
    return parser.parse_args()


def _request_json(url: str, parameters: dict[str, str]) -> dict[str, Any]:
    request_url = f"{url}?{urllib.parse.urlencode(parameters)}"
    request = urllib.request.Request(
        request_url, headers={"User-Agent": "ArchaeoAI-curation-gate/1"}
    )
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(f"source service error: {payload['error']}")
    return payload


def fetch_queue_geometry(queue: list[NhleRecord]) -> dict[int, dict[str, Any]]:
    """Fetch designation geometry in bounded chunks; callers must not persist it."""
    results: dict[int, dict[str, Any]] = {}
    for start in range(0, len(queue), 80):
        ids = ",".join(str(record.list_entry) for record in queue[start : start + 80])
        payload = _request_json(
            NHLE_QUERY_URL,
            {
                "where": f"ListEntry IN ({ids})",
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


def _load_reviews(path: Path, queue_ids: set[int]) -> dict[int, dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(
            f"missing ignored full-entry review input: {path}; run --print-queue first"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    reviews: dict[int, dict[str, str]] = {}
    for item in payload:
        list_entry = int(item["list_entry"])
        if list_entry in reviews:
            raise ValueError(f"duplicate full-entry review: {list_entry}")
        reviews[list_entry] = item
    if set(reviews) != queue_ids:
        missing = sorted(queue_ids - set(reviews))
        extra = sorted(set(reviews) - queue_ids)
        raise ValueError(f"review input must exactly match queue; missing={missing}, extra={extra}")
    return reviews


def _map_reason(reason: str | None) -> ExclusionReason | None:
    if reason is None:
        return None
    mapping = {
        "geometry_compound": ExclusionReason.GEOMETRY_COMPOUND,
        "geometry_off_centre": ExclusionReason.GEOMETRY_OFF_CENTRE,
        "geometry_too_large": ExclusionReason.GEOMETRY_TOO_LARGE,
        "terrain_no_1m_coverage": ExclusionReason.TERRAIN_NO_1M_COVERAGE,
        "terrain_patch_incomplete": ExclusionReason.TERRAIN_PATCH_INCOMPLETE,
        "terrain_provenance_missing": ExclusionReason.TERRAIN_PROVENANCE_MISSING,
        "terrain_provenance_confounded": ExclusionReason.TERRAIN_PROVENANCE_CONFOUNDED,
    }
    return mapping.get(reason, ExclusionReason.INSUFFICIENT_EVIDENCE)


def _new_record(
    source: NhleRecord, review: dict[str, str], *, access_date: str, last_edit_at: str
) -> CurationRecord:
    assessment = assess_full_entry(reasons=review["reasons"], details=review["details"])
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
        review_date=review.get("checked_at", access_date)[:10],
        source_access_date=access_date,
        source_last_edit_at=last_edit_at,
        capture_scale=source.capture_scale or "UNAVAILABLE",
    )


def apply_geometry_gate(
    records: list[CurationRecord], geometry_by_id: dict[int, dict[str, Any]]
) -> dict[int, tuple[float, float]]:
    centres: dict[int, tuple[float, float]] = {}
    for record in records:
        if record.review_status is not ReviewStatus.NEEDS_GEOMETRY_REVIEW:
            continue
        feature = geometry_by_id.get(record.list_entry)
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
            record.exclusion_reason = _map_reason(qa.reason)
            record.reviewer_notes = f"Geometry QA failed: {qa.reason}."
        else:
            record.review_status = ReviewStatus.NEEDS_GEOMETRY_REVIEW
            record.exclusion_reason = _map_reason(qa.reason)
            record.reviewer_notes = f"Geometry requires visual review: {qa.reason}."
    return centres


def apply_terrain_gate(
    records: list[CurationRecord], centres: dict[int, tuple[float, float]], *, workers: int
) -> dict[int, str]:
    errors: dict[int, str] = {}
    by_id = {record.list_entry: record for record in records}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_terrain_qa, centre): list_entry
            for list_entry, centre in centres.items()
        }
        for future in as_completed(futures):
            list_entry = futures[future]
            record = by_id[list_entry]
            try:
                qa = future.result()
            except Exception as error:  # metadata outage is a review state, not a false absence
                record.terrain_coverage = QaStatus.NEEDS_REVIEW
                record.terrain_provenance = QaStatus.NEEDS_REVIEW
                record.review_status = ReviewStatus.NEEDS_TERRAIN_REVIEW
                record.exclusion_reason = ExclusionReason.TERRAIN_PROVENANCE_MISSING
                record.reviewer_notes = "Terrain metadata query requires retry."
                errors[list_entry] = type(error).__name__
                continue
            record.terrain_coverage = QaStatus(qa.coverage_status)
            record.terrain_provenance = QaStatus(qa.provenance_status)
            record.terrain_year = qa.year or "UNAVAILABLE"
            record.source_resolution_m = qa.resolution_m or "UNAVAILABLE"
            record.survey_program = qa.programme or "UNAVAILABLE"
            if qa.coverage_status == "fail":
                record.review_status = ReviewStatus.REJECTED
                record.exclusion_reason = _map_reason(qa.reason)
                record.reviewer_notes = f"Terrain coverage QA failed: {qa.reason}."
            elif qa.provenance_status == "pass":
                record.review_status = ReviewStatus.ACCEPTED
                record.exclusion_reason = None
                record.reviewer_notes = (
                    "Passed full-entry, geometry, coverage, and provenance gates."
                )
            else:
                record.review_status = ReviewStatus.NEEDS_TERRAIN_REVIEW
                record.exclusion_reason = _map_reason(qa.reason)
                record.reviewer_notes = f"Terrain provenance requires review: {qa.reason}."
    return errors


def _record_row(record: CurationRecord, second_review_ids: set[int]) -> dict[str, Any]:
    return {
        "list_entry": record.list_entry,
        "review_status": record.review_status.value,
        "bowl_barrow_identity": record.bowl_barrow_identity.value,
        "single_monument": record.single_monument.value,
        "upstanding_earthwork": record.upstanding_earthwork.value,
        "geometry_qa": record.geometry_qa.value,
        "terrain_coverage": record.terrain_coverage.value,
        "terrain_provenance": record.terrain_provenance.value,
        "geographic_group_id": record.geographic_group_id,
        "exclusion_reason": record.exclusion_reason.value if record.exclusion_reason else "",
        "evidence_codes": ";".join(record.evidence_codes),
        "reviewer_notes": record.reviewer_notes,
        "review_date": record.review_date,
        "source_access_date": record.source_access_date,
        "source_last_edit_at": record.source_last_edit_at,
        "capture_scale": record.capture_scale,
        "terrain_year": record.terrain_year,
        "source_resolution_m": record.source_resolution_m,
        "survey_program": record.survey_program,
        "second_review_required": str(record.list_entry in second_review_ids).lower(),
    }


def write_outputs(
    records: list[CurationRecord],
    *,
    output_dir: Path,
    access_time: datetime,
    layer_url: str,
    last_edit_at: str,
    query_errors: dict[int, str],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    second_review_ids = set(deterministic_second_review_ids(records, sample_size=40))
    counts = summarize_records(records)
    accepted = [record for record in records if record.review_status is ReviewStatus.ACCEPTED]
    group_counts = Counter(record.geographic_group_id for record in accepted)
    viable_groups = {
        group: count for group, count in group_counts.items() if count >= MINIMUM_VIABLE_GROUP_SITES
    }
    holdouts = select_nonadjacent_holdout_candidates(
        viable_groups, minimum_count=MINIMUM_VIABLE_GROUP_SITES, limit=4
    )

    provenance_counts = Counter(
        (
            record.geographic_group_id,
            record.terrain_year,
            record.source_resolution_m,
            record.survey_program,
            record.capture_scale,
        )
        for record in accepted
    )
    group_years: dict[str, set[str]] = defaultdict(set)
    for record in accepted:
        group_years[record.geographic_group_id].add(record.terrain_year)
    all_one_m = all(float(record.source_resolution_m) <= 1 for record in accepted)
    all_provenance_known = all(record.survey_program != "UNAVAILABLE" for record in accepted)
    final_go = (
        len(accepted) >= 250
        and len(viable_groups) >= 8
        and len(holdouts) >= 2
        and all_one_m
        and all_provenance_known
    )
    decision = "FINAL GO" if final_go else "CONDITIONAL GO REMAINS"

    summary = {
        "gate": {
            "phase": "2A.5",
            "decision": decision,
            "curation_version": CURATION_VERSION,
            "queue_seed": QUEUE_SEED,
            "generated_at": access_time.astimezone(UTC).isoformat(),
            "warning": "No raster, background sample, model, or exact coordinate is included.",
        },
        "source": {
            "nhle_scheduled_monuments_layer": layer_url,
            "source_access_date": access_time.date().isoformat(),
            "source_last_edit_at": last_edit_at,
            "official_entry_review": "every queue ID loaded from its Historic England full entry",
            "terrain_index": "official Defra/Environment Agency OGC Features collections",
            "future_patch_footprint_assumption": "128 m square at nominal 1 m resolution",
        },
        "counts": counts,
        "qa": {
            "geometry_pass": sum(r.geometry_qa is QaStatus.PASS for r in records),
            "geometry_fail": sum(r.geometry_qa is QaStatus.FAIL for r in records),
            "geometry_needs_review": sum(r.geometry_qa is QaStatus.NEEDS_REVIEW for r in records),
            "terrain_coverage_pass": sum(r.terrain_coverage is QaStatus.PASS for r in records),
            "terrain_coverage_fail": sum(r.terrain_coverage is QaStatus.FAIL for r in records),
            "terrain_coverage_needs_review": sum(
                r.terrain_coverage is QaStatus.NEEDS_REVIEW for r in records
            ),
            "terrain_provenance_pass": sum(r.terrain_provenance is QaStatus.PASS for r in records),
            "terrain_provenance_fail": sum(r.terrain_provenance is QaStatus.FAIL for r in records),
            "terrain_provenance_needs_review": sum(
                r.terrain_provenance is QaStatus.NEEDS_REVIEW for r in records
            ),
            "metadata_query_errors": len(query_errors),
        },
        "geography": {
            "provisional_group_definition": "100 km British National Grid cell",
            "accepted_groups": len(group_counts),
            "minimum_sites_per_viable_group": MINIMUM_VIABLE_GROUP_SITES,
            "viable_groups": len(viable_groups),
            "nonadjacent_holdout_candidates": holdouts,
            "holdout_warning": "provisional only; patch autocorrelation is not yet measured",
        },
        "provenance_confound": {
            "all_accepted_nominally_1m": all_one_m,
            "all_accepted_programmes_known": all_provenance_known,
            "groups_with_one_observed_survey_year": sum(
                len(years) == 1 for years in group_years.values()
            ),
            "groups_examined": len(group_years),
            "interpretation": (
                "Positive-only metadata cannot prove absence of label-survey confounding. "
                "Future backgrounds must be matched within acquisition and geographic strata."
            ),
        },
        "second_review": {
            "queue_size": len(second_review_ids),
            "independent_review_completed": False,
            "warning": "This queue requires a different human/independent reviewer.",
        },
        "privacy": {
            "stored_coordinates": False,
            "stored_geometry": False,
            "tracked_stable_public_ids": True,
            "private_inputs_ignored_by_git": True,
        },
    }

    assert_coordinate_safe_fields(TRACKED_CURATION_FIELDS)
    with (output_dir / "e001_curated_records.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=TRACKED_CURATION_FIELDS)
        writer.writeheader()
        writer.writerows(_record_row(record, second_review_ids) for record in records)
    with (output_dir / "e001_group_counts.csv").open("w", encoding="utf-8", newline="") as file:
        fields = [
            "geographic_group_id",
            "accepted_sites",
            "viable_at_12",
            "holdout_candidate",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for group, count in sorted(group_counts.items()):
            writer.writerow(
                {
                    "geographic_group_id": group,
                    "accepted_sites": count,
                    "viable_at_12": str(count >= MINIMUM_VIABLE_GROUP_SITES).lower(),
                    "holdout_candidate": str(group in holdouts).lower(),
                }
            )
    with (output_dir / "e001_provenance_summary.csv").open(
        "w", encoding="utf-8", newline=""
    ) as file:
        fields = [
            "geographic_group_id",
            "terrain_year",
            "source_resolution_m",
            "survey_program",
            "nhle_capture_scale",
            "accepted_sites",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for values, count in sorted(provenance_counts.items()):
            writer.writerow(dict(zip(fields, (*values, count), strict=True)))
    with (output_dir / "e001_second_review_queue.csv").open(
        "w", encoding="utf-8", newline=""
    ) as file:
        fields = ["list_entry", "primary_status", "required_action"]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for record in records:
            if record.list_entry in second_review_ids:
                writer.writerow(
                    {
                        "list_entry": record.list_entry,
                        "primary_status": record.review_status.value,
                        "required_action": "independent_human_full_entry_review",
                    }
                )
    (output_dir / "e001_curation_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def main() -> int:
    args = parse_args()
    if args.queue_size < 300 or args.queue_size > 400:
        raise SystemExit("--queue-size must be between 300 and 400")
    if args.terrain_workers < 1 or args.terrain_workers > 8:
        raise SystemExit("--terrain-workers must be between 1 and 8")
    source_records = fetch_barrow_records()
    queue = geographically_stratified_queue(source_records, size=args.queue_size)
    if args.print_queue:
        print(json.dumps([record.list_entry for record in queue]))
        return 0

    access_time = datetime.now(UTC)
    reviews = _load_reviews(args.review_json, {record.list_entry for record in queue})
    _service_metadata, layer_metadata = fetch_source_metadata()
    last_edit_ms = layer_metadata.get("editingInfo", {}).get("lastEditDate")
    last_edit_at = (
        datetime.fromtimestamp(last_edit_ms / 1000, tz=UTC).isoformat()
        if last_edit_ms is not None
        else "UNAVAILABLE"
    )
    records = [
        _new_record(
            source,
            reviews[source.list_entry],
            access_date=access_time.date().isoformat(),
            last_edit_at=last_edit_at,
        )
        for source in queue
    ]
    geometry = fetch_queue_geometry(queue)
    centres = apply_geometry_gate(records, geometry)
    query_errors = apply_terrain_gate(records, centres, workers=args.terrain_workers)
    summary = write_outputs(
        records,
        output_dir=args.output_dir,
        access_time=access_time,
        layer_url=NHLE_LAYER_URL,
        last_edit_at=last_edit_at,
        query_errors=query_errors,
    )
    print(json.dumps({"decision": summary["gate"]["decision"], **summary["counts"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
