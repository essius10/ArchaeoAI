"""Build staged, provenance-matched E001 unlabelled-background terrain."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError

from archaeoai.nhle_audit import NHLE_QUERY_URL
from archaeoai.paths import find_project_root
from archaeoai.terrain.acquisition import (
    PrivateSiteLocation,
    WcsRequestError,
    fetch_wcs_payload,
    terrain_provenance_id,
)
from archaeoai.terrain.background import (
    BACKGROUND_ALGORITHM_VERSION,
    BACKGROUND_LABEL,
    BackgroundIndexRecord,
    BackgroundSamplingPolicy,
    candidate_rejection_reason,
    generate_candidate,
    observation_group_id,
    opaque_background_id,
    sampling_stratum_id,
    write_background_index,
)
from archaeoai.terrain.full_dataset import (
    inspect_cached_artifacts,
    quarantine_artifact,
    terrain_content_digest,
    validate_representations,
    write_processed_archive,
)
from archaeoai.terrain.patches import patch_bounds, required_grid_tiles
from archaeoai.terrain.privacy import (
    assert_coordinate_safe_mapping,
    ensure_private_output,
    verify_git_ignored,
)
from archaeoai.terrain.raster import extract_patch
from archaeoai.terrain.representations import terrain_representations
from archaeoai.terrain_metadata import fetch_terrain_qa

PROCESSING_VERSION = "e001-terrain-v1"
STATE_SCHEMA = "e001-background-state-v1"
KNOWN_ARCHAEOLOGY_SOURCE = "Historic England NHLE Scheduled Monuments"


@dataclass(frozen=True, slots=True)
class PositiveRow:
    sample_id: str
    source_id: int
    geographic_group_id: str
    terrain_provenance_id: str
    survey_year: str
    overlap_group_id: str


@dataclass(frozen=True, slots=True)
class BackgroundResult:
    sample_id: str
    observation_group_id: str
    geographic_group_id: str
    terrain_provenance_id: str
    survey_year: str
    status: str
    action: str
    raw_sha256: str
    patch_sha256: str
    processed_sha256: str
    cross_cell: bool
    request_attempts: int
    request_retries: int
    failure_reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-count", type=int, choices=(10, 40, 261), required=True)
    return parser.parse_args()


def _load_positive_rows(path: Path) -> list[PositiveRow]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = [
            PositiveRow(
                sample_id=row["sample_id"],
                source_id=int(row["nhle_list_entry"]),
                geographic_group_id=row["geographic_group_id"],
                terrain_provenance_id=row["terrain_provenance_id"],
                survey_year=row["survey_year"],
                overlap_group_id=row["overlap_group_id"],
            )
            for row in csv.DictReader(file)
        ]
    if len(rows) != 261 or len({row.sample_id for row in rows}) != 261:
        raise ValueError("the frozen positive terrain index must contain 261 unique rows")
    return rows


def _load_locations(path: Path) -> dict[int, PrivateSiteLocation]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = {int(item["list_entry"]): PrivateSiteLocation(**item) for item in payload["records"]}
    if payload.get("schema_version") != "e001-private-locations-v1" or len(records) != 261:
        raise ValueError("the private positive location cache must contain 261 records")
    return records


def _diverse_order(rows: list[PositiveRow]) -> list[PositiveRow]:
    remaining = sorted(
        rows,
        key=lambda row: hashlib.sha256(
            f"E001-background-pilot-order-v1:{row.sample_id}".encode()
        ).hexdigest(),
    )
    selected: list[PositiveRow] = []
    groups: set[str] = set()
    provenances: set[str] = set()
    years: set[str] = set()
    while remaining:
        choice = max(
            remaining,
            key=lambda row: (
                int(row.geographic_group_id not in groups)
                + int(row.terrain_provenance_id not in provenances)
                + int(row.survey_year not in years),
                int(row.geographic_group_id not in groups),
                int(row.terrain_provenance_id not in provenances),
            ),
        )
        selected.append(choice)
        remaining.remove(choice)
        groups.add(choice.geographic_group_id)
        provenances.add(choice.terrain_provenance_id)
        years.add(choice.survey_year)
    return selected


def _load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {
            "schema_version": STATE_SCHEMA,
            "algorithm_version": BACKGROUND_ALGORITHM_VERSION,
            "records": {},
            "rejection_counts": {},
            "candidate_attempts": 0,
        }
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        payload.get("schema_version") != STATE_SCHEMA
        or payload.get("algorithm_version") != BACKGROUND_ALGORITHM_VERSION
    ):
        raise ValueError("unsupported private background state")
    return payload


def _write_state(path: Path, state: dict[str, object], root: Path) -> None:
    destination = ensure_private_output(root, path)
    verify_git_ignored(root, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".partial.json")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)


def _request_json(url: str, *, attempts: int = 4) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": "ArchaeoAI-background/1"})
    for attempt_index in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                payload = json.load(response)
            if isinstance(payload, dict) and "error" not in payload:
                return payload
            raise RuntimeError("official exclusion service returned an error payload")
        except HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt_index == attempts - 1:
                raise
        except (URLError, TimeoutError):
            if attempt_index == attempts - 1:
                raise
        time.sleep(min(8, 2**attempt_index))
    raise AssertionError("official service retry loop terminated unexpectedly")


def _known_archaeology_count(centre: tuple[float, float], *, exclusion_m: float) -> int:
    easting, northing = centre
    parameters = {
        "geometry": (
            f"{easting - exclusion_m:g},{northing - exclusion_m:g},"
            f"{easting + exclusion_m:g},{northing + exclusion_m:g}"
        ),
        "geometryType": "esriGeometryEnvelope",
        "inSR": "27700",
        "spatialRel": "esriSpatialRelIntersects",
        "returnCountOnly": "true",
        "f": "json",
    }
    payload = _request_json(f"{NHLE_QUERY_URL}?{urllib.parse.urlencode(parameters)}")
    count = payload.get("count")
    if isinstance(count, bool) or not isinstance(count, int):
        raise RuntimeError("official exclusion service omitted its count")
    return count


def _matching_terrain_metadata(
    centre: tuple[float, float], *, expected_provenance_id: str
) -> tuple[bool, str, str, str]:
    for attempt_index in range(3):
        try:
            qa = fetch_terrain_qa(centre, patch_size_m=128)
            break
        except (HTTPError, URLError, TimeoutError):
            if attempt_index == 2:
                raise
            time.sleep(min(4, 2**attempt_index))
    if qa.coverage_status != "pass":
        return False, "missing_terrain", qa.year, qa.programme
    if qa.provenance_status != "pass":
        return False, "outside_provenance", qa.year, qa.programme
    candidate_id = terrain_provenance_id(qa.year, qa.resolution, qa.programme)
    return candidate_id == expected_provenance_id, "outside_provenance", qa.year, qa.programme


def _record_rejection(state: dict[str, object], reason: str) -> None:
    counts = state["rejection_counts"]
    assert isinstance(counts, dict)
    counts[reason] = int(counts.get(reason, 0)) + 1
    state["candidate_attempts"] = int(state["candidate_attempts"]) + 1


def _select_candidate(
    positive: PositiveRow,
    *,
    location: PrivateSiteLocation,
    all_positive_centres: tuple[tuple[float, float], ...],
    existing_background_centres: tuple[tuple[float, float], ...],
    state: dict[str, object],
    root: Path,
    state_path: Path,
    policy: BackgroundSamplingPolicy,
) -> dict[str, object]:
    records = state["records"]
    assert isinstance(records, dict)
    existing = records.get(positive.sample_id)
    if isinstance(existing, dict) and "easting" in existing:
        return existing
    start_attempt = int(existing.get("next_attempt", 1)) if isinstance(existing, dict) else 1
    for attempt in range(start_attempt, 1001):
        candidate = generate_candidate(
            positive.sample_id,
            positive_centre=(location.easting, location.northing),
            attempt=attempt,
            policy=policy,
        )
        centre = (candidate.easting, candidate.northing)
        reason = candidate_rejection_reason(
            centre,
            expected_geographic_group_id=positive.geographic_group_id,
            positive_centres=all_positive_centres,
            background_centres=existing_background_centres,
            known_scheduled_monument_present=False,
            policy=policy,
        )
        if reason is None:
            known_scheduled_monument = bool(
                _known_archaeology_count(
                    centre, exclusion_m=policy.known_archaeology_exclusion_buffer_m
                )
            )
            reason = candidate_rejection_reason(
                centre,
                expected_geographic_group_id=positive.geographic_group_id,
                positive_centres=all_positive_centres,
                background_centres=existing_background_centres,
                known_scheduled_monument_present=known_scheduled_monument,
                policy=policy,
            )
        if reason is None:
            matches, reason, year, programme = _matching_terrain_metadata(
                centre,
                expected_provenance_id=positive.terrain_provenance_id,
            )
            if matches:
                record: dict[str, object] = {
                    "positive_sample_id": positive.sample_id,
                    "sample_id": opaque_background_id(positive.sample_id, attempt),
                    "easting": candidate.easting,
                    "northing": candidate.northing,
                    "candidate_attempt": attempt,
                    "geographic_group_id": positive.geographic_group_id,
                    "terrain_provenance_id": positive.terrain_provenance_id,
                    "survey_year": year,
                    "survey_program": programme,
                    "observation_group_id": observation_group_id(
                        positive.overlap_group_id or positive.sample_id
                    ),
                    "sampling_stratum": sampling_stratum_id(positive.sample_id),
                    "selection_status": "selected",
                }
                records[positive.sample_id] = record
                state["candidate_attempts"] = int(state["candidate_attempts"]) + 1
                _write_state(state_path, state, root)
                return record
        assert reason is not None
        _record_rejection(state, reason)
        records[positive.sample_id] = {"next_attempt": attempt + 1}
        _write_state(state_path, state, root)
    raise RuntimeError(f"candidate attempts exhausted for {positive.sample_id}")


def _background_location(record: dict[str, object]) -> PrivateSiteLocation:
    return PrivateSiteLocation(
        list_entry=0,
        easting=float(record["easting"]),
        northing=float(record["northing"]),
        geographic_group_id=str(record["geographic_group_id"]),
        terrain_year=str(record["survey_year"]),
        source_resolution_m="1",
        survey_program=str(record["survey_program"]),
    )


def _process_background(
    record: dict[str, object], *, root: Path, policy: BackgroundSamplingPolicy
) -> BackgroundResult:
    sample_id = str(record["sample_id"])
    location = _background_location(record)
    private_root = root / "data/private/e001/backgrounds"
    raw_path = private_root / "raw" / f"{sample_id}.tif"
    processed_path = private_root / "processed" / f"{sample_id}.npz"
    rejected_root = private_root / "rejected"
    bounds = patch_bounds((location.easting, location.northing), patch_size_m=128, resolution_m=1)
    cross_cell = len(required_grid_tiles(bounds)) > 1
    expected_raw = str(record.get("raw_sha256") or "") or None
    inspection = inspect_cached_artifacts(
        raw_path=raw_path,
        processed_path=processed_path,
        location=location,
        expected_raw_sha256=expected_raw,
    )
    if inspection.status == "valid":
        return BackgroundResult(
            sample_id,
            str(record["observation_group_id"]),
            str(record["geographic_group_id"]),
            str(record["terrain_provenance_id"]),
            str(record["survey_year"]),
            "pass",
            "cache_verified",
            inspection.raw_sha256,
            inspection.patch_sha256,
            inspection.processed_sha256,
            cross_cell,
            0,
            0,
            "",
        )
    if inspection.status == "processed_invalid" and processed_path.exists():
        quarantine_artifact(
            processed_path, reason="processed_archive_qa_failed", rejected_root=rejected_root
        )
    if inspection.status in {"processed_missing", "processed_invalid"}:
        assert inspection.patch is not None and inspection.representations is not None
        processed_sha = write_processed_archive(
            processed_path,
            patch=inspection.patch,
            representations=inspection.representations,
            project_root=root,
        )
        return BackgroundResult(
            sample_id,
            str(record["observation_group_id"]),
            str(record["geographic_group_id"]),
            str(record["terrain_provenance_id"]),
            str(record["survey_year"]),
            "pass",
            "processed_regenerated",
            inspection.raw_sha256,
            inspection.patch_sha256,
            processed_sha,
            cross_cell,
            0,
            0,
            "",
        )
    if inspection.status == "raw_invalid":
        if raw_path.exists():
            quarantine_artifact(raw_path, reason=inspection.reasons[0], rejected_root=rejected_root)
        if processed_path.exists():
            quarantine_artifact(
                processed_path, reason="source_raw_invalid", rejected_root=rejected_root
            )
    if inspection.status == "representation_invalid":
        return BackgroundResult(
            sample_id,
            str(record["observation_group_id"]),
            str(record["geographic_group_id"]),
            str(record["terrain_provenance_id"]),
            str(record["survey_year"]),
            "failed",
            "processing_failure",
            inspection.raw_sha256,
            inspection.patch_sha256,
            "",
            cross_cell,
            0,
            0,
            ";".join(inspection.reasons),
        )
    try:
        payload = fetch_wcs_payload(bounds)
    except WcsRequestError as error:
        return BackgroundResult(
            sample_id,
            str(record["observation_group_id"]),
            str(record["geographic_group_id"]),
            str(record["terrain_provenance_id"]),
            str(record["survey_year"]),
            "failed",
            "download_failed",
            "",
            "",
            "",
            cross_cell,
            error.attempts,
            error.retries,
            error.reason,
        )
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = raw_path.with_name(f"{raw_path.stem}.partial.tif")
    ensure_private_output(root, temporary)
    verify_git_ignored(root, temporary)
    temporary.write_bytes(payload.content)
    try:
        patch = extract_patch(
            [temporary],
            centre=(location.easting, location.northing),
            patch_size_m=128,
            resolution_m=1,
            max_nodata_fraction=policy.maximum_nodata_fraction,
        )
    except (OSError, ValueError) as error:
        quarantine_artifact(temporary, reason="raw_qa_failed", rejected_root=rejected_root)
        return BackgroundResult(
            sample_id,
            str(record["observation_group_id"]),
            str(record["geographic_group_id"]),
            str(record["terrain_provenance_id"]),
            str(record["survey_year"]),
            "failed",
            "raw_qa_failed",
            payload.sha256,
            "",
            "",
            cross_cell,
            payload.attempts,
            payload.retries,
            type(error).__name__,
        )
    temporary.replace(raw_path)
    patch_sha = terrain_content_digest(patch.data, patch.mask)
    representations = terrain_representations(
        patch.data,
        resolution_m=1,
        mask=patch.mask,
        local_relief_radius_m=16,
    )
    repeated = terrain_representations(
        patch.data,
        resolution_m=1,
        mask=patch.mask,
        local_relief_radius_m=16,
    )
    qa = validate_representations(
        representations,
        source_mask=patch.mask,
        deterministic_reference=repeated,
    )
    if not qa.passed:
        return BackgroundResult(
            sample_id,
            str(record["observation_group_id"]),
            str(record["geographic_group_id"]),
            str(record["terrain_provenance_id"]),
            str(record["survey_year"]),
            "failed",
            "processing_failure",
            payload.sha256,
            patch_sha,
            "",
            cross_cell,
            payload.attempts,
            payload.retries,
            ";".join(qa.reasons),
        )
    processed_sha = write_processed_archive(
        processed_path,
        patch=patch,
        representations=representations,
        project_root=root,
    )
    return BackgroundResult(
        sample_id,
        str(record["observation_group_id"]),
        str(record["geographic_group_id"]),
        str(record["terrain_provenance_id"]),
        str(record["survey_year"]),
        "pass",
        "downloaded",
        payload.sha256,
        patch_sha,
        processed_sha,
        cross_cell,
        payload.attempts,
        payload.retries,
        "",
    )


def _index_record(result: BackgroundResult, *, stratum: str) -> BackgroundIndexRecord:
    return BackgroundIndexRecord(
        sample_id=result.sample_id,
        class_label=BACKGROUND_LABEL,
        observation_group_id=result.observation_group_id,
        geographic_group_id=result.geographic_group_id,
        terrain_provenance_id=result.terrain_provenance_id,
        survey_year=result.survey_year,
        source_resolution_m=1.0,
        patch_size_m=128,
        sampling_algorithm_version=BACKGROUND_ALGORITHM_VERSION,
        processing_version=PROCESSING_VERSION,
        sampling_stratum=stratum,
        acquisition_status="verified",
        raw_qa_status="pass",
        representation_qa_status="pass",
        qa_status="pass",
        raw_sha256=result.raw_sha256,
        patch_sha256=result.patch_sha256,
        processed_sha256=result.processed_sha256,
        cross_cell=result.cross_cell,
    )


def _inventory_digest(records: list[BackgroundIndexRecord]) -> str:
    digest = hashlib.sha256()
    for record in sorted(records, key=lambda row: row.sample_id):
        digest.update(
            f"{record.sample_id}:{record.raw_sha256}:{record.patch_sha256}:"
            f"{record.processed_sha256}\n".encode()
        )
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    root = find_project_root()
    policy = BackgroundSamplingPolicy()
    positive_rows = _load_positive_rows(root / "outputs/terrain/e001_terrain_index.csv")
    ordered = _diverse_order(positive_rows)
    target_rows = ordered[: args.target_count]
    location_path = root / "data/private/e001/approved-site-locations.json"
    verify_git_ignored(root, location_path)
    locations = _load_locations(location_path)
    private_root = root / "data/private/e001/backgrounds"
    state_path = private_root / "sampling_state.json"
    state = _load_state(state_path)
    state_records = state["records"]
    assert isinstance(state_records, dict)
    all_positive_centres = tuple(
        (location.easting, location.northing) for location in locations.values()
    )
    selected_records = [
        record
        for record in state_records.values()
        if isinstance(record, dict) and "easting" in record
    ]
    existing_centres = [
        (float(record["easting"]), float(record["northing"])) for record in selected_records
    ]
    started = datetime.now(UTC)
    started_clock = time.perf_counter()

    for completed, positive in enumerate(target_rows, start=1):
        existing = state_records.get(positive.sample_id)
        if isinstance(existing, dict) and "easting" in existing:
            if (float(existing["easting"]), float(existing["northing"])) not in existing_centres:
                existing_centres.append((float(existing["easting"]), float(existing["northing"])))
            continue
        record = _select_candidate(
            positive,
            location=locations[positive.source_id],
            all_positive_centres=all_positive_centres,
            existing_background_centres=tuple(existing_centres),
            state=state,
            root=root,
            state_path=state_path,
            policy=policy,
        )
        existing_centres.append((float(record["easting"]), float(record["northing"])))
        print(
            f"selected={completed}/{args.target_count} sample={record['sample_id']} "
            f"candidate_attempt={record['candidate_attempt']}",
            flush=True,
        )

    results = []
    for completed, positive in enumerate(target_rows, start=1):
        record = state_records[positive.sample_id]
        assert isinstance(record, dict)
        result = _process_background(record, root=root, policy=policy)
        results.append(result)
        record.update(
            {
                "terrain_status": result.status,
                "terrain_action": result.action,
                "raw_sha256": result.raw_sha256,
                "patch_sha256": result.patch_sha256,
                "processed_sha256": result.processed_sha256,
                "cross_cell": result.cross_cell,
                "request_attempts": result.request_attempts,
                "request_retries": result.request_retries,
                "failure_reason": result.failure_reason,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        _write_state(state_path, state, root)
        print(
            f"terrain={completed}/{args.target_count} sample={result.sample_id} "
            f"status={result.status} action={result.action}",
            flush=True,
        )

    passed = [result for result in results if result.status == "pass"]
    failed = [result for result in results if result.status != "pass"]
    index_records = [
        _index_record(
            result,
            stratum=str(state_records[positive.sample_id]["sampling_stratum"]),
        )
        for positive, result in zip(target_rows, results, strict=True)
        if result.status == "pass"
    ]
    output_root = root / "outputs/background"
    write_background_index(index_records, output_root / "e001_background_index.csv")
    stage_name = {10: "pilot10", 40: "pilot40", 261: "full"}[args.target_count]
    action_counts = Counter(result.action for result in results)
    group_counts = Counter(result.geographic_group_id for result in passed)
    provenance_counts = Counter(result.terrain_provenance_id for result in passed)
    year_counts = Counter(result.survey_year for result in passed)
    summary: dict[str, object] = {
        "phase": f"2C unlabelled-background {stage_name}",
        "class_label": BACKGROUND_LABEL,
        "algorithm_version": BACKGROUND_ALGORITHM_VERSION,
        "processing_version": PROCESSING_VERSION,
        "started_at": started.isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "elapsed_seconds": round(time.perf_counter() - started_clock, 3),
        "policy": {
            "backgrounds_per_positive": policy.backgrounds_per_positive,
            "positive_exclusion_buffer_m": policy.positive_exclusion_buffer_m,
            "known_archaeology_exclusion_buffer_m": (policy.known_archaeology_exclusion_buffer_m),
            "minimum_sample_separation_m": policy.minimum_sample_separation_m,
            "sampling_annulus_m": [
                policy.sampling_radius_min_m,
                policy.sampling_radius_max_m,
            ],
            "same_geographic_group_required": True,
            "exact_provenance_match_required": True,
        },
        "known_archaeology_exclusion": {
            "source": KNOWN_ARCHAEOLOGY_SOURCE,
            "service": NHLE_QUERY_URL,
            "access_date": "2026-08-29",
            "interpretation": (
                "Excludes known scheduled monuments only; it does not establish "
                "archaeology-free terrain."
            ),
        },
        "counts": {
            "requested": args.target_count,
            "selected": len(results),
            "terrain_passed": len(passed),
            "terrain_failed": len(failed),
            "representations_passed": len(passed),
            "new_downloads": action_counts["downloaded"],
            "cache_verified": action_counts["cache_verified"],
            "processed_regenerated": action_counts["processed_regenerated"],
            "candidate_attempts_cumulative": int(state["candidate_attempts"]),
            "request_retries": sum(result.request_retries for result in results),
        },
        "candidate_rejections_cumulative": dict(
            sorted((str(key), int(value)) for key, value in state["rejection_counts"].items())
        ),
        "terrain_failures": dict(Counter(result.failure_reason for result in failed)),
        "geographic_groups": dict(sorted(group_counts.items())),
        "terrain_provenance_ids": dict(sorted(provenance_counts.items())),
        "survey_years": dict(sorted(year_counts.items())),
        "source_resolutions_m": {"1.0": len(passed)},
        "inventory_sha256": _inventory_digest(index_records),
        "privacy": {
            "coordinates_tracked": False,
            "sampling_geometry_tracked": False,
            "private_state_ignored": True,
        },
        "scope": {
            "model_trained": False,
            "metrics_computed": False,
            "split_frozen": False,
        },
    }
    assert_coordinate_safe_mapping(summary)
    summary_path = output_root / f"e001_background_{stage_name}_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0 if not failed and len(passed) == args.target_count else 1


if __name__ == "__main__":
    raise SystemExit(main())
