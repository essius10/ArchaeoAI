"""Revalidate, visually sample, and freeze the complete E001 positive terrain dataset."""

from __future__ import annotations

import csv
import json
import warnings
from collections import Counter
from dataclasses import replace
from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import NotGeoreferencedWarning

from archaeoai.paths import find_project_root
from archaeoai.terrain.acquisition import (
    PrivateSiteLocation,
    opaque_sample_id,
)
from archaeoai.terrain.audit import (
    cross_cell_seams,
    deterministic_rank,
    extract_described_diameter,
)
from archaeoai.terrain.full_dataset import inspect_cached_artifacts
from archaeoai.terrain.index import (
    TerrainIndexRecord,
    overlap_components,
    write_index,
)
from archaeoai.terrain.patches import patch_bounds, required_grid_tiles
from archaeoai.terrain.privacy import (
    assert_coordinate_safe_mapping,
    ensure_private_output,
    verify_git_ignored,
)
from archaeoai.terrain.qa import write_private_qa_strip

VISUAL_SAMPLE_SIZE = 25
VISUAL_SEED = "E001-phase-2B5-visual-QA-v1"
OVERLAP_DECISIONS = {
    (1008509, 1008526): "separate_mounds_with_distinct_dimensions_in_same_woodland",
    (1008910, 1008911): "separate_mounds_on_opposite_sides_of_named_watercourse",
    (1009114, 1009115): "separate_adjacent_mounds_with_distinct_dimensions",
    (1009479, 1013406): "separate_mounds_with_distinct_dimensions_on_same_ridge",
    (1010634, 1010636): "official_descriptions_identify_a_pair_of_separate_barrows",
    (1010643, 1010645): "official_descriptions_identify_members_of_a_four_barrow_line",
    (1011274, 1011282): "separate_mounds_with_distinct_size_and_form",
}


def _load_locations(path: Path) -> tuple[PrivateSiteLocation, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = tuple(PrivateSiteLocation(**item) for item in payload["records"])
    if payload.get("schema_version") != "e001-private-locations-v1" or len(records) != 261:
        raise ValueError("expected the approved 261-site private location cache")
    return records


def _load_index(path: Path) -> list[TerrainIndexRecord]:
    records: list[TerrainIndexRecord] = []
    with path.open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            records.append(
                TerrainIndexRecord(
                    sample_id=row["sample_id"],
                    nhle_list_entry=int(row["nhle_list_entry"]),
                    geographic_group_id=row["geographic_group_id"],
                    terrain_provenance_id=row["terrain_provenance_id"],
                    survey_year=row["survey_year"],
                    source_resolution_m=float(row["source_resolution_m"]),
                    processing_version=row["processing_version"],
                    patch_size_m=int(row["patch_size_m"]),
                    acquisition_status=row["acquisition_status"],
                    raw_qa_status=row["raw_qa_status"],
                    representation_qa_status=row["representation_qa_status"],
                    representations=row["representations"],
                    qa_status=row["qa_status"],
                    raw_sha256=row["raw_sha256"],
                    patch_sha256=row["patch_sha256"],
                    processed_sha256=row["processed_sha256"],
                    cross_cell=row["cross_cell"].casefold() == "true",
                    overlap_group_id=row.get("overlap_group_id", ""),
                )
            )
    return records


def _select_visual_sample(
    records: list[TerrainIndexRecord],
    *,
    cross_cell_ids: set[str],
    overlap_pairs: tuple[tuple[int, int], ...],
    diameters: dict[int, float],
) -> list[TerrainIndexRecord]:
    by_source = {record.nhle_list_entry: record for record in records}
    selected: dict[str, TerrainIndexRecord] = {
        record.sample_id: record for record in records if record.sample_id in cross_cell_ids
    }
    for pair in overlap_pairs:
        candidate = min(
            (by_source[source_id] for source_id in pair),
            key=lambda record: deterministic_rank(record.sample_id, seed=VISUAL_SEED),
        )
        selected[candidate.sample_id] = candidate
    diameter_records = sorted(
        (record for record in records if record.nhle_list_entry in diameters),
        key=lambda record: (diameters[record.nhle_list_entry], record.sample_id),
    )
    for record in (*diameter_records[:3], *diameter_records[-3:]):
        selected[record.sample_id] = record

    groups = {record.geographic_group_id for record in selected.values()}
    years = {record.survey_year for record in selected.values()}
    provenances = {record.terrain_provenance_id for record in selected.values()}
    ranked = sorted(
        records,
        key=lambda record: deterministic_rank(record.sample_id, seed=VISUAL_SEED),
    )
    while len(selected) < VISUAL_SAMPLE_SIZE:
        candidates = [record for record in ranked if record.sample_id not in selected]
        choice = max(
            candidates,
            key=lambda record: (
                int(record.geographic_group_id not in groups)
                + int(record.survey_year not in years)
                + int(record.terrain_provenance_id not in provenances),
                int(record.geographic_group_id not in groups),
                int(record.survey_year not in years),
                deterministic_rank(record.sample_id, seed=VISUAL_SEED),
            ),
        )
        selected[choice.sample_id] = choice
        groups.add(choice.geographic_group_id)
        years.add(choice.survey_year)
        provenances.add(choice.terrain_provenance_id)
    return sorted(selected.values(), key=lambda record: record.sample_id)[:VISUAL_SAMPLE_SIZE]


def _write_contact_sheets(strip_paths: list[Path], *, qa_root: Path, root: Path) -> None:
    contact_root = qa_root / "contact_sheets"
    for batch_index, start in enumerate(range(0, len(strip_paths), 5), start=1):
        batch = strip_paths[start : start + 5]
        arrays = []
        for path in batch:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", NotGeoreferencedWarning)
                with rasterio.open(path) as dataset:
                    arrays.append(dataset.read(1))
        width = arrays[0].shape[1]
        gutter = 2
        sheet = np.full(
            (sum(array.shape[0] for array in arrays) + gutter * (len(arrays) - 1), width),
            255,
            dtype=np.uint8,
        )
        row = 0
        for array in arrays:
            sheet[row : row + array.shape[0], :] = array
            row += array.shape[0] + gutter
        destination = ensure_private_output(
            root, contact_root / f"visual-qa-batch-{batch_index:02d}.png"
        )
        verify_git_ignored(root, destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", NotGeoreferencedWarning)
            with rasterio.open(
                destination,
                "w",
                driver="PNG",
                width=sheet.shape[1],
                height=sheet.shape[0],
                count=1,
                dtype="uint8",
            ) as dataset:
                dataset.write(sheet, 1)


def _sum_files(path: Path) -> int:
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def _visual_review_summary(
    path: Path, selected_ids: set[str], *, cross_cell_ids: set[str]
) -> dict[str, object]:
    if not path.exists():
        payload = {
            "schema_version": "e001-private-visual-review-v1",
            "warning": "CONTROLLED: linked to private site terrain; never commit or publish",
            "records": [
                {
                    "sample_id": sample_id,
                    "status": "pending",
                    "observations": [],
                    "cross_cell_seam": "pending",
                }
                for sample_id in sorted(selected_ids)
            ],
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("records", [])
    if {row.get("sample_id") for row in rows} != selected_ids:
        raise ValueError("private visual review does not match deterministic selection")
    allowed_statuses = {"pending", "pass", "manual_review_required", "fail"}
    if any(row.get("status") not in allowed_statuses for row in rows):
        raise ValueError("private visual review contains an unsupported status")
    for row in rows:
        expected_seam = (
            {"pending", "not_observed", "observed"}
            if row["sample_id"] in cross_cell_ids
            else {"pending", "not_applicable"}
        )
        if row.get("cross_cell_seam") not in expected_seam:
            raise ValueError("private visual review has inconsistent cross-cell status")
    status_counts = Counter(row.get("status", "missing") for row in rows)
    observation_counts = Counter(
        observation for row in rows for observation in row.get("observations", [])
    )
    seam_counts = Counter(row.get("cross_cell_seam", "missing") for row in rows)
    return {
        "reviewed": len(rows) - status_counts["pending"],
        "pending": status_counts["pending"],
        "technical_failures": status_counts["fail"],
        "manual_review_required": status_counts["manual_review_required"],
        "status_counts": dict(sorted(status_counts.items())),
        "observation_counts": dict(sorted(observation_counts.items())),
        "cross_cell_seam_counts": dict(sorted(seam_counts.items())),
    }


def main() -> int:
    root = find_project_root()
    private_root = root / "data/private/e001"
    location_path = private_root / "approved-site-locations.json"
    review_cache_path = root / "data/private/e001_full_entry_reviews.json"
    for path in (location_path, review_cache_path):
        verify_git_ignored(root, path)
    locations = _load_locations(location_path)
    by_source = {location.list_entry: location for location in locations}
    index_path = root / "outputs/terrain/e001_terrain_index.csv"
    index_records = _load_index(index_path)
    if len(index_records) != 261:
        raise ValueError("full terrain index must contain 261 rows")

    overlap_mapping, overlap_pairs = overlap_components(locations, patch_size_m=128)
    if set(overlap_pairs) != set(OVERLAP_DECISIONS):
        raise ValueError("real overlap pairs differ from the reviewed seven-pair decision set")
    index_records = [
        replace(
            record,
            overlap_group_id=overlap_mapping.get(record.nhle_list_entry, ""),
        )
        for record in index_records
    ]
    write_index(index_records, index_path)

    raw_root = private_root / "terrain/raw"
    processed_root = private_root / "terrain/processed"
    expected_raw_names = {f"{record.sample_id}.tif" for record in index_records}
    expected_processed_names = {f"{record.sample_id}.npz" for record in index_records}
    actual_raw_names = {path.name for path in raw_root.glob("*.tif")}
    actual_processed_names = {path.name for path in processed_root.glob("*.npz")}
    partial_artifacts = tuple(private_root.glob("terrain/**/*.partial.*"))
    if actual_raw_names != expected_raw_names:
        raise ValueError("raw cache inventory differs from the 261-row index")
    if actual_processed_names != expected_processed_names:
        raise ValueError("processed cache inventory differs from the 261-row index")
    if partial_artifacts:
        raise ValueError("partial terrain artifacts remain in the controlled cache")
    cross_diagnostics = []
    valid_by_sample = {}
    failures: list[str] = []
    for record in index_records:
        location = by_source[record.nhle_list_entry]
        inspection = inspect_cached_artifacts(
            raw_path=raw_root / f"{record.sample_id}.tif",
            processed_path=processed_root / f"{record.sample_id}.npz",
            location=location,
            expected_raw_sha256=record.raw_sha256,
        )
        matches_index = (
            inspection.status == "valid"
            and inspection.patch_sha256 == record.patch_sha256
            and inspection.processed_sha256 == record.processed_sha256
        )
        if not matches_index:
            failures.append(record.sample_id)
            continue
        valid_by_sample[record.sample_id] = inspection
        bounds = patch_bounds(
            (location.easting, location.northing), patch_size_m=128, resolution_m=1
        )
        cross_cell = len(required_grid_tiles(bounds)) > 1
        if cross_cell != record.cross_cell:
            failures.append(record.sample_id)
            continue
        if cross_cell:
            assert inspection.patch is not None and inspection.representations is not None
            diagnostics = cross_cell_seams(
                inspection.patch.data,
                inspection.representations["slope_degrees"],
                inspection.representations["local_relief_r16m"],
                bounds=bounds,
            )
            if not diagnostics:
                failures.append(record.sample_id)
            cross_diagnostics.extend(diagnostics)
    if failures:
        raise ValueError(f"full cache revalidation failed for {len(failures)} records")

    reviews = {
        int(item["list_entry"]): item
        for item in json.loads(review_cache_path.read_text(encoding="utf-8"))
    }
    diameters = {
        source_id: diameter
        for source_id, review in reviews.items()
        if source_id in by_source
        and (diameter := extract_described_diameter(review["details"])) is not None
    }
    cross_cell_ids = {record.sample_id for record in index_records if record.cross_cell}
    visual_sample = _select_visual_sample(
        index_records,
        cross_cell_ids=cross_cell_ids,
        overlap_pairs=overlap_pairs,
        diameters=diameters,
    )
    qa_root = private_root / "terrain/qa/full_visual"
    strip_paths = []
    for record in visual_sample:
        inspection = valid_by_sample[record.sample_id]
        assert inspection.patch is not None and inspection.representations is not None
        strip_paths.append(
            write_private_qa_strip(
                {"elevation": inspection.patch.data, **inspection.representations},
                destination=qa_root / "strips" / f"{record.sample_id}.png",
                project_root=root,
            )
        )
    _write_contact_sheets(strip_paths, qa_root=qa_root, root=root)
    visual_receipt = qa_root / "selection.json"
    verify_git_ignored(root, visual_receipt)
    visual_receipt.write_text(
        json.dumps(
            {
                "schema_version": "e001-private-visual-selection-v1",
                "seed": VISUAL_SEED,
                "panel_order": [
                    "raw_elevation",
                    "median_normalized_elevation",
                    "slope_degrees",
                    "hillshade_315_45",
                    "local_relief_r16m",
                ],
                "records": [
                    {
                        "sample_id": record.sample_id,
                        "geographic_group_id": record.geographic_group_id,
                        "survey_year": record.survey_year,
                        "terrain_provenance_id": record.terrain_provenance_id,
                        "cross_cell": record.cross_cell,
                        "overlap_group_id": record.overlap_group_id,
                        "described_diameter_m": diameters.get(record.nhle_list_entry),
                    }
                    for record in visual_sample
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    visual_review_path = qa_root / "review.json"
    verify_git_ignored(root, visual_review_path)
    visual_summary = _visual_review_summary(
        visual_review_path,
        {record.sample_id for record in visual_sample},
        cross_cell_ids=cross_cell_ids,
    )

    overlap_path = root / "outputs/terrain/e001_overlap_decisions.csv"
    with overlap_path.open("w", encoding="utf-8", newline="") as file:
        fields = [
            "first_sample_id",
            "second_sample_id",
            "overlap_group_id",
            "geographic_group_id",
            "decision",
            "evidence_basis",
            "future_split_policy",
        ]
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        for first, second in overlap_pairs:
            first_location = by_source[first]
            if first_location.geographic_group_id != by_source[second].geographic_group_id:
                raise ValueError("reviewed overlap pair crosses provisional geographic groups")
            writer.writerow(
                {
                    "first_sample_id": opaque_sample_id(first),
                    "second_sample_id": opaque_sample_id(second),
                    "overlap_group_id": overlap_mapping[first],
                    "geographic_group_id": first_location.geographic_group_id,
                    "decision": "retain_grouped",
                    "evidence_basis": OVERLAP_DECISIONS[(first, second)],
                    "future_split_policy": "assign_entire_overlap_group_to_one_partition",
                }
            )

    acquisition = json.loads(
        (root / "outputs/terrain/e001_full_terrain_summary.json").read_text(encoding="utf-8")
    )
    qa_image_root = private_root / "terrain/qa"
    state_path = private_root / "terrain/full_acquisition_state.json"
    pilot_receipt_path = qa_image_root / "e001_pilot_private_receipt.json"
    cache_bytes = sum(
        path.stat().st_size
        for path in (location_path, review_cache_path, state_path, pilot_receipt_path)
        if path.exists()
    )
    controlled_total = _sum_files(private_root) + review_cache_path.stat().st_size
    raw_bytes = _sum_files(raw_root)
    processed_bytes = _sum_files(processed_root)
    qa_bytes = sum(path.stat().st_size for path in qa_image_root.rglob("*.png") if path.is_file())
    automatic_cross_passes = sum(
        not diagnostic.duplicate_edge and diagnostic.elevation_step_percentile <= 99
        for diagnostic in cross_diagnostics
    )
    summary: dict[str, object] = {
        "phase": "2B.5 full positive terrain freeze audit",
        "cache_revalidation": {
            "expected": 261,
            "raw_files_present": len(actual_raw_names),
            "processed_archives_present": len(actual_processed_names),
            "partial_artifacts": len(partial_artifacts),
            "passed": len(valid_by_sample),
            "failed": len(failures),
            "raw_checksum_matches": len(valid_by_sample),
            "patch_checksum_matches": len(valid_by_sample),
            "processed_checksum_matches": len(valid_by_sample),
            "four_representations_complete": len(valid_by_sample),
        },
        "cross_cell": {
            "patches": len(cross_cell_ids),
            "patches_passed": len(cross_cell_ids),
            "correct_dimensions": len(cross_cell_ids),
            "correct_transforms": len(cross_cell_ids),
            "representations_passed": len(cross_cell_ids),
            "internal_boundaries_checked": len(cross_diagnostics),
            "automatic_boundary_checks_passed": automatic_cross_passes,
            "duplicate_rows_or_columns": sum(
                diagnostic.duplicate_edge for diagnostic in cross_diagnostics
            ),
            "maximum_median_boundary_step_m": max(
                diagnostic.elevation_median_step for diagnostic in cross_diagnostics
            ),
            "maximum_boundary_step_percentile": max(
                diagnostic.elevation_step_percentile for diagnostic in cross_diagnostics
            ),
            "visual_review_included": len(cross_cell_ids),
        },
        "overlap_review": {
            "pairs": len(overlap_pairs),
            "components": len(set(overlap_mapping.values())),
            "retain_grouped": len(overlap_pairs),
            "merge_or_drop_candidate": 0,
            "manual_review_required": 0,
            "all_within_one_provisional_group": True,
            "split_constraint_recorded_in_index": True,
        },
        "visual_qa": {
            "sample_size": len(visual_sample),
            "geographic_groups": len({record.geographic_group_id for record in visual_sample}),
            "survey_years": len({record.survey_year for record in visual_sample}),
            "provenance_ids": len({record.terrain_provenance_id for record in visual_sample}),
            "cross_cell_patches": sum(record.cross_cell for record in visual_sample),
            "overlap_components": len(
                {record.overlap_group_id for record in visual_sample if record.overlap_group_id}
            ),
            "description_diameter_extremes_included": 6,
            **visual_summary,
        },
        "storage_bytes": {
            "raw_terrain": raw_bytes,
            "processed_terrain": processed_bytes,
            "private_qa_images": qa_bytes,
            "controlled_metadata_caches": cache_bytes,
            "total_controlled_dataset": controlled_total,
        },
        "estimate_comparison": {
            "raw_estimated_bytes": 17214255,
            "raw_actual_difference_bytes": raw_bytes - 17214255,
            "processed_estimated_bytes": 60241097,
            "processed_actual_difference_bytes": processed_bytes - 60241097,
            "sequential_seconds_estimated": 702,
            "two_worker_actual_seconds": acquisition["elapsed_seconds"],
        },
        "integrity": {
            "unique_samples": len({record.sample_id for record in index_records}),
            "unique_sources": len({record.nhle_list_entry for record in index_records}),
            "unique_raw_checksums": len({record.raw_sha256 for record in index_records}),
            "unique_patch_checksums": len({record.patch_sha256 for record in index_records}),
            "unique_processed_checksums": len(
                {record.processed_sha256 for record in index_records}
            ),
            "geographic_groups": len({record.geographic_group_id for record in index_records}),
            "provenance_ids": len({record.terrain_provenance_id for record in index_records}),
        },
        "privacy": {
            "visual_outputs_private": True,
            "coordinate_fields_tracked": False,
            "georeferenced_outputs_tracked": False,
            "precise_boundary_diagnostics_private": True,
        },
    }
    assert_coordinate_safe_mapping(summary)
    (root / "outputs/terrain/e001_full_terrain_audit.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    visual_gate_passed = (
        visual_summary["pending"] == 0
        and visual_summary["technical_failures"] == 0
        and visual_summary["manual_review_required"] == 0
        and visual_summary["cross_cell_seam_counts"]
        == {
            "not_applicable": 17,
            "not_observed": 8,
        }
    )
    return 0 if visual_gate_passed else 2


if __name__ == "__main__":
    raise SystemExit(main())
