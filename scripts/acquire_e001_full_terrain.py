"""Resume, acquire, validate, and index all accepted E001 positive terrain patches."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from statistics import median

from archaeoai.paths import find_project_root
from archaeoai.terrain.acquisition import (
    ACQUISITION_VERSION,
    EA_DTM_DATASET_ID,
    PrivateSiteLocation,
    WcsRequestError,
    fetch_wcs_payload,
    load_accepted_sites,
    opaque_sample_id,
)
from archaeoai.terrain.full_dataset import (
    REPRESENTATION_NAMES,
    inspect_cached_artifacts,
    quarantine_artifact,
    terrain_content_digest,
    validate_representations,
    write_processed_archive,
)
from archaeoai.terrain.index import TerrainIndexRecord, overlap_components, write_index
from archaeoai.terrain.patches import patch_bounds, required_grid_tiles
from archaeoai.terrain.privacy import (
    assert_coordinate_safe_mapping,
    ensure_private_output,
    verify_git_ignored,
)
from archaeoai.terrain.raster import extract_patch
from archaeoai.terrain.representations import terrain_representations

PROCESSING_VERSION = "e001-terrain-v1"
STATE_SCHEMA = "e001-full-acquisition-state-v1"


@dataclass(frozen=True, slots=True)
class SiteResult:
    sample_id: str
    nhle_list_entry: int
    geographic_group_id: str
    terrain_provenance_id: str
    survey_year: str
    survey_program: str
    source_resolution_m: float
    cross_cell: bool
    status: str
    action: str
    raw_qa_status: str
    representation_qa_status: str
    failure_reasons: tuple[str, ...]
    raw_sha256: str
    patch_sha256: str
    processed_sha256: str
    raw_bytes: int
    processed_bytes: int
    nodata_fraction: float | None
    minimum_elevation_m: float | None
    maximum_elevation_m: float | None
    request_attempts: int
    request_retries: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=range(1, 5), default=2)
    return parser.parse_args()


def _load_private_locations(path: Path) -> dict[int, PrivateSiteLocation]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = {int(item["list_entry"]): PrivateSiteLocation(**item) for item in payload["records"]}
    if payload.get("schema_version") != "e001-private-locations-v1" or len(records) != 261:
        raise ValueError("private location cache must contain all 261 approved sites")
    return records


def _provenance_id(location: PrivateSiteLocation) -> str:
    fields = (
        location.terrain_year,
        location.source_resolution_m,
        location.survey_program,
        EA_DTM_DATASET_ID,
    )
    return "EAP-" + hashlib.sha256("|".join(fields).encode()).hexdigest()[:12]


def _load_state(path: Path) -> dict[str, object]:
    if not path.exists():
        return {"schema_version": STATE_SCHEMA, "records": {}}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != STATE_SCHEMA or not isinstance(
        payload.get("records"), dict
    ):
        raise ValueError("unsupported private acquisition state")
    return payload


def _write_state(path: Path, state: dict[str, object], root: Path) -> None:
    destination = ensure_private_output(root, path)
    verify_git_ignored(root, destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".partial.json")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)


def _failure_result(
    location: PrivateSiteLocation,
    *,
    cross_cell: bool,
    action: str,
    reasons: tuple[str, ...],
    raw_qa_status: str,
    representation_qa_status: str,
    raw_sha256: str = "",
    patch_sha256: str = "",
    attempts: int = 0,
    retries: int = 0,
) -> SiteResult:
    return SiteResult(
        sample_id=opaque_sample_id(location.list_entry),
        nhle_list_entry=location.list_entry,
        geographic_group_id=location.geographic_group_id,
        terrain_provenance_id=_provenance_id(location),
        survey_year=location.terrain_year,
        survey_program=location.survey_program,
        source_resolution_m=1.0,
        cross_cell=cross_cell,
        status="rejected",
        action=action,
        raw_qa_status=raw_qa_status,
        representation_qa_status=representation_qa_status,
        failure_reasons=reasons,
        raw_sha256=raw_sha256,
        patch_sha256=patch_sha256,
        processed_sha256="",
        raw_bytes=0,
        processed_bytes=0,
        nodata_fraction=None,
        minimum_elevation_m=None,
        maximum_elevation_m=None,
        request_attempts=attempts,
        request_retries=retries,
    )


def _process_site(
    location: PrivateSiteLocation,
    *,
    root: Path,
    expected_raw_sha256: str | None,
) -> SiteResult:
    sample_id = opaque_sample_id(location.list_entry)
    private_root = root / "data/private/e001/terrain"
    raw_path = private_root / "raw" / f"{sample_id}.tif"
    processed_path = private_root / "processed" / f"{sample_id}.npz"
    rejected_root = private_root / "rejected"
    bounds = patch_bounds((location.easting, location.northing), patch_size_m=128, resolution_m=1)
    cross_cell = len(required_grid_tiles(bounds)) > 1
    inspection = inspect_cached_artifacts(
        raw_path=raw_path,
        processed_path=processed_path,
        location=location,
        expected_raw_sha256=expected_raw_sha256,
    )
    if inspection.status == "valid":
        assert inspection.patch is not None and inspection.representations is not None
        patch = inspection.patch
        return SiteResult(
            sample_id=sample_id,
            nhle_list_entry=location.list_entry,
            geographic_group_id=location.geographic_group_id,
            terrain_provenance_id=_provenance_id(location),
            survey_year=location.terrain_year,
            survey_program=location.survey_program,
            source_resolution_m=1.0,
            cross_cell=cross_cell,
            status="pass",
            action="cache_verified",
            raw_qa_status="pass",
            representation_qa_status="pass",
            failure_reasons=(),
            raw_sha256=inspection.raw_sha256,
            patch_sha256=inspection.patch_sha256,
            processed_sha256=inspection.processed_sha256,
            raw_bytes=raw_path.stat().st_size,
            processed_bytes=processed_path.stat().st_size,
            nodata_fraction=patch.qa.nodata_fraction,
            minimum_elevation_m=patch.qa.minimum_elevation_m,
            maximum_elevation_m=patch.qa.maximum_elevation_m,
            request_attempts=0,
            request_retries=0,
        )

    if inspection.status in {"processed_missing", "processed_invalid"}:
        assert inspection.patch is not None and inspection.representations is not None
        if inspection.status == "processed_invalid":
            quarantine_artifact(
                processed_path, reason="processed_qa_failed", rejected_root=rejected_root
            )
        try:
            processed_sha256 = write_processed_archive(
                processed_path,
                patch=inspection.patch,
                representations=inspection.representations,
                project_root=root,
            )
        except (OSError, ValueError) as error:
            return _failure_result(
                location,
                cross_cell=cross_cell,
                action="processed_regeneration_failed",
                reasons=(type(error).__name__,),
                raw_qa_status="pass",
                representation_qa_status="failed",
                raw_sha256=inspection.raw_sha256,
                patch_sha256=inspection.patch_sha256,
            )
        patch = inspection.patch
        return SiteResult(
            sample_id=sample_id,
            nhle_list_entry=location.list_entry,
            geographic_group_id=location.geographic_group_id,
            terrain_provenance_id=_provenance_id(location),
            survey_year=location.terrain_year,
            survey_program=location.survey_program,
            source_resolution_m=1.0,
            cross_cell=cross_cell,
            status="pass",
            action="processed_regenerated",
            raw_qa_status="pass",
            representation_qa_status="pass",
            failure_reasons=(),
            raw_sha256=inspection.raw_sha256,
            patch_sha256=inspection.patch_sha256,
            processed_sha256=processed_sha256,
            raw_bytes=raw_path.stat().st_size,
            processed_bytes=processed_path.stat().st_size,
            nodata_fraction=patch.qa.nodata_fraction,
            minimum_elevation_m=patch.qa.minimum_elevation_m,
            maximum_elevation_m=patch.qa.maximum_elevation_m,
            request_attempts=0,
            request_retries=0,
        )

    if inspection.status == "representation_invalid":
        return _failure_result(
            location,
            cross_cell=cross_cell,
            action="representation_generation_failed",
            reasons=inspection.reasons,
            raw_qa_status="pass",
            representation_qa_status="failed",
            raw_sha256=inspection.raw_sha256,
            patch_sha256=inspection.patch_sha256,
        )

    if inspection.status == "raw_invalid":
        if raw_path.exists():
            quarantine_artifact(raw_path, reason=inspection.reasons[0], rejected_root=rejected_root)
        if processed_path.exists():
            quarantine_artifact(
                processed_path, reason="source_raw_invalid", rejected_root=rejected_root
            )

    try:
        payload = fetch_wcs_payload(bounds)
    except WcsRequestError as error:
        return _failure_result(
            location,
            cross_cell=cross_cell,
            action="download_failed",
            reasons=(error.reason,),
            raw_qa_status="not_run",
            representation_qa_status="not_run",
            attempts=error.attempts,
            retries=error.retries,
        )
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_raw = raw_path.with_name(f"{raw_path.stem}.partial.tif")
    ensure_private_output(root, temporary_raw)
    verify_git_ignored(root, temporary_raw)
    temporary_raw.write_bytes(payload.content)
    try:
        patch = extract_patch(
            [temporary_raw],
            centre=(location.easting, location.northing),
            patch_size_m=128,
            resolution_m=1,
            max_nodata_fraction=0.2,
        )
    except (OSError, ValueError) as error:
        quarantine_artifact(
            temporary_raw, reason="downloaded_raw_qa_failed", rejected_root=rejected_root
        )
        return _failure_result(
            location,
            cross_cell=cross_cell,
            action="downloaded_raw_rejected",
            reasons=(type(error).__name__,),
            raw_qa_status="failed",
            representation_qa_status="not_run",
            raw_sha256=payload.sha256,
            attempts=payload.attempts,
            retries=payload.retries,
        )
    temporary_raw.replace(raw_path)
    patch_sha256 = terrain_content_digest(patch.data, patch.mask)
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
    representation_qa = validate_representations(
        representations,
        source_mask=patch.mask,
        expected_shape=patch.data.shape,
        deterministic_reference=repeated,
    )
    if not representation_qa.passed:
        return _failure_result(
            location,
            cross_cell=cross_cell,
            action="representation_generation_failed",
            reasons=representation_qa.reasons,
            raw_qa_status="pass",
            representation_qa_status="failed",
            raw_sha256=payload.sha256,
            patch_sha256=patch_sha256,
            attempts=payload.attempts,
            retries=payload.retries,
        )
    try:
        processed_sha256 = write_processed_archive(
            processed_path,
            patch=patch,
            representations=representations,
            project_root=root,
        )
    except (OSError, ValueError) as error:
        return _failure_result(
            location,
            cross_cell=cross_cell,
            action="processed_write_failed",
            reasons=(type(error).__name__,),
            raw_qa_status="pass",
            representation_qa_status="failed",
            raw_sha256=payload.sha256,
            patch_sha256=patch_sha256,
            attempts=payload.attempts,
            retries=payload.retries,
        )
    return SiteResult(
        sample_id=sample_id,
        nhle_list_entry=location.list_entry,
        geographic_group_id=location.geographic_group_id,
        terrain_provenance_id=_provenance_id(location),
        survey_year=location.terrain_year,
        survey_program=location.survey_program,
        source_resolution_m=1.0,
        cross_cell=cross_cell,
        status="pass",
        action="downloaded",
        raw_qa_status="pass",
        representation_qa_status="pass",
        failure_reasons=(),
        raw_sha256=payload.sha256,
        patch_sha256=patch_sha256,
        processed_sha256=processed_sha256,
        raw_bytes=raw_path.stat().st_size,
        processed_bytes=processed_path.stat().st_size,
        nodata_fraction=patch.qa.nodata_fraction,
        minimum_elevation_m=patch.qa.minimum_elevation_m,
        maximum_elevation_m=patch.qa.maximum_elevation_m,
        request_attempts=payload.attempts,
        request_retries=payload.retries,
    )


def _index_record(result: SiteResult, *, overlap_group_id: str) -> TerrainIndexRecord:
    passed = result.status == "pass"
    return TerrainIndexRecord(
        sample_id=result.sample_id,
        nhle_list_entry=result.nhle_list_entry,
        geographic_group_id=result.geographic_group_id,
        terrain_provenance_id=result.terrain_provenance_id,
        survey_year=result.survey_year,
        source_resolution_m=result.source_resolution_m,
        processing_version=PROCESSING_VERSION,
        patch_size_m=128,
        acquisition_status="verified" if result.raw_qa_status == "pass" else "failed",
        raw_qa_status=result.raw_qa_status,
        representation_qa_status=result.representation_qa_status,
        representations=";".join(REPRESENTATION_NAMES) if passed else "",
        qa_status="pass" if passed else "rejected",
        raw_sha256=result.raw_sha256,
        patch_sha256=result.patch_sha256,
        processed_sha256=result.processed_sha256,
        cross_cell=result.cross_cell,
        overlap_group_id=overlap_group_id,
    )


def _inventory_digest(results: list[SiteResult]) -> str:
    digest = hashlib.sha256()
    for result in sorted(
        (row for row in results if row.status == "pass"), key=lambda row: row.sample_id
    ):
        digest.update(
            f"{result.sample_id}:{result.raw_sha256}:{result.patch_sha256}:{result.processed_sha256}\n".encode()
        )
    return digest.hexdigest()


def _distribution(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "minimum": None, "median": None, "maximum": None}
    return {
        "count": len(values),
        "minimum": min(values),
        "median": median(values),
        "maximum": max(values),
    }


def main() -> int:
    args = parse_args()
    root = find_project_root()
    private_root = root / "data/private/e001"
    location_path = private_root / "approved-site-locations.json"
    verify_git_ignored(root, location_path)
    locations = _load_private_locations(location_path)
    accepted = load_accepted_sites(root / "outputs/feasibility/e001_curated_records.csv")
    if set(locations) != {record.list_entry for record in accepted}:
        raise ValueError("accepted catalogue and private location cache differ")

    state_path = private_root / "terrain/full_acquisition_state.json"
    state = _load_state(state_path)
    state_records = state["records"]
    assert isinstance(state_records, dict)
    pilot = json.loads(
        (root / "outputs/terrain/e001_pilot_summary.json").read_text(encoding="utf-8")
    )
    pilot_hashes = {
        row["sample_id"]: row["raw_sha256"]
        for row in pilot["records"]
        if row["qa_status"] == "pass"
    }
    pilot_ids = set(pilot_hashes)
    started_at = datetime.now(UTC)
    started_clock = time.perf_counter()
    results: list[SiteResult] = []
    total = len(accepted)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {}
        for record in accepted:
            location = locations[record.list_entry]
            sample_id = opaque_sample_id(record.list_entry)
            state_row = state_records.get(sample_id, {})
            expected_sha = (
                state_row.get("raw_sha256") if isinstance(state_row, dict) else None
            ) or pilot_hashes.get(sample_id)
            futures[
                executor.submit(
                    _process_site,
                    location,
                    root=root,
                    expected_raw_sha256=expected_sha,
                )
            ] = sample_id
        for completed, future in enumerate(as_completed(futures), start=1):
            sample_id = futures[future]
            try:
                result = future.result()
            except Exception as error:  # retain a safe failure state; never accept silently
                location = locations[
                    next(
                        record.list_entry
                        for record in accepted
                        if opaque_sample_id(record.list_entry) == sample_id
                    )
                ]
                result = _failure_result(
                    location,
                    cross_cell=False,
                    action="unexpected_failure",
                    reasons=(type(error).__name__,),
                    raw_qa_status="not_run",
                    representation_qa_status="not_run",
                )
            results.append(result)
            state_records[result.sample_id] = {
                **asdict(result),
                "updated_at": datetime.now(UTC).isoformat(),
            }
            state["last_updated_at"] = datetime.now(UTC).isoformat()
            _write_state(state_path, state, root)
            if completed % 10 == 0 or result.status != "pass" or completed == total:
                print(
                    f"progress={completed}/{total} sample={result.sample_id} "
                    f"status={result.status} action={result.action} "
                    f"retries={result.request_retries}",
                    flush=True,
                )

    results.sort(key=lambda row: row.sample_id)
    finished_at = datetime.now(UTC)
    elapsed_seconds = time.perf_counter() - started_clock
    overlap_mapping, _ = overlap_components(tuple(locations.values()), patch_size_m=128)
    index_records = [
        _index_record(
            result,
            overlap_group_id=overlap_mapping.get(result.nhle_list_entry, ""),
        )
        for result in results
    ]
    output_root = root / "outputs/terrain"
    write_index(index_records, output_root / "e001_terrain_index.csv")
    failures = [result for result in results if result.status != "pass"]
    with (output_root / "e001_full_terrain_failures.csv").open(
        "w", encoding="utf-8", newline=""
    ) as file:
        fields = [
            "sample_id",
            "nhle_list_entry",
            "geographic_group_id",
            "action",
            "failure_reasons",
            "request_attempts",
            "request_retries",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for result in failures:
            writer.writerow(
                {
                    "sample_id": result.sample_id,
                    "nhle_list_entry": result.nhle_list_entry,
                    "geographic_group_id": result.geographic_group_id,
                    "action": result.action,
                    "failure_reasons": ";".join(result.failure_reasons),
                    "request_attempts": result.request_attempts,
                    "request_retries": result.request_retries,
                }
            )

    passed = [result for result in results if result.status == "pass"]
    raw_root = private_root / "terrain/raw"
    processed_root = private_root / "terrain/processed"
    qa_root = private_root / "terrain/qa"
    group_counts = Counter(result.geographic_group_id for result in passed)
    year_counts = Counter(result.survey_year for result in passed)
    programme_counts = Counter(result.survey_program for result in passed)
    provenance_counts = Counter(result.terrain_provenance_id for result in passed)
    action_counts = Counter(result.action for result in results)
    failure_counts = Counter(reason for result in failures for reason in result.failure_reasons)
    patch_digest_counts = Counter(result.patch_sha256 for result in passed)
    duplicate_patch_digests = sum(count > 1 for count in patch_digest_counts.values())
    safe_summary: dict[str, object] = {
        "phase": "2B.5 full positive terrain acquisition",
        "processing_version": PROCESSING_VERSION,
        "acquisition_version": ACQUISITION_VERSION,
        "source_dataset_id": EA_DTM_DATASET_ID,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "elapsed_seconds": round(elapsed_seconds, 3),
        "workers": args.workers,
        "counts": {
            "accepted_labels": total,
            "pilot_present_before_run": len(pilot_ids),
            "remaining_before_run": total - len(pilot_ids),
            "terrain_attempted": total,
            "new_wcs_downloads": action_counts["downloaded"],
            "cache_verified": action_counts["cache_verified"],
            "processed_regenerated": action_counts["processed_regenerated"],
            "terrain_passed": len(passed),
            "terrain_failed": len(failures),
            "representations_passed": sum(
                result.representation_qa_status == "pass" for result in results
            ),
            "request_attempts": sum(result.request_attempts for result in results),
            "request_retries": sum(result.request_retries for result in results),
            "request_failures": sum(result.action == "download_failed" for result in results),
        },
        "failure_reasons": dict(sorted(failure_counts.items())),
        "raw_qa": {
            "nodata_fraction": _distribution(
                [
                    float(result.nodata_fraction)
                    for result in passed
                    if result.nodata_fraction is not None
                ]
            ),
            "minimum_elevation_m": _distribution(
                [
                    float(result.minimum_elevation_m)
                    for result in passed
                    if result.minimum_elevation_m is not None
                ]
            ),
            "maximum_elevation_m": _distribution(
                [
                    float(result.maximum_elevation_m)
                    for result in passed
                    if result.maximum_elevation_m is not None
                ]
            ),
        },
        "cross_cell": {
            "total": sum(result.cross_cell for result in results),
            "passed": sum(result.cross_cell and result.status == "pass" for result in results),
            "failed": sum(result.cross_cell and result.status != "pass" for result in results),
        },
        "integrity": {
            "unique_sample_ids": len({result.sample_id for result in results}),
            "unique_source_ids": len({result.nhle_list_entry for result in results}),
            "duplicate_exact_patch_digests": duplicate_patch_digests,
            "all_four_representations_for_passed": all(
                result.representation_qa_status == "pass" for result in passed
            ),
        },
        "geographic_groups": dict(sorted(group_counts.items())),
        "survey_years": dict(sorted(year_counts.items())),
        "survey_programmes": dict(sorted(programme_counts.items())),
        "terrain_provenance_ids": dict(sorted(provenance_counts.items())),
        "source_resolutions_m": {"1.0": len(passed)},
        "inventory_sha256": _inventory_digest(results),
        "storage_bytes_at_run_end": {
            "raw_geotiff": sum(path.stat().st_size for path in raw_root.glob("*.tif")),
            "processed_npz": sum(path.stat().st_size for path in processed_root.glob("*.npz")),
            "private_qa": sum(path.stat().st_size for path in qa_root.glob("*") if path.is_file()),
            "location_cache": location_path.stat().st_size,
        },
        "privacy": {
            "coordinate_rows_tracked": False,
            "georeferenced_rasters_tracked": False,
            "private_state_git_ignored": True,
        },
        "gates": {
            "cpython_312_reproduced": False,
            "independent_human_review": "outstanding",
            "background_generated": False,
            "split_finalized": False,
            "model_trained": False,
        },
    }
    assert_coordinate_safe_mapping(safe_summary)
    (output_root / "e001_full_terrain_summary.json").write_text(
        json.dumps(safe_summary, indent=2) + "\n", encoding="utf-8"
    )
    failure_log = qa_root / "e001_full_service_failures.json"
    verify_git_ignored(root, failure_log)
    failure_log.write_text(
        json.dumps(
            {
                "generated_at": finished_at.isoformat(),
                "records": [
                    {
                        "sample_id": result.sample_id,
                        "reasons": result.failure_reasons,
                        "attempts": result.request_attempts,
                        "retries": result.request_retries,
                    }
                    for result in failures
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "accepted": total,
                "passed": len(passed),
                "failed": len(failures),
                "downloaded": action_counts["downloaded"],
                "cache_verified": action_counts["cache_verified"],
                "retries": safe_summary["counts"]["request_retries"],
                "elapsed_seconds": round(elapsed_seconds, 3),
            },
            indent=2,
        )
    )
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
