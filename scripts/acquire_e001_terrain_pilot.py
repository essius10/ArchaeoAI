"""Acquire, validate, and index a one-to-five-site private E001 terrain pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from archaeoai.paths import find_project_root
from archaeoai.terrain.acquisition import (
    ACQUISITION_VERSION,
    EA_DTM_COVERAGE_ID,
    EA_DTM_DATASET_ID,
    EA_DTM_WCS_URL,
    PrivateSiteLocation,
    download_wcs_geotiff,
    load_accepted_sites,
    opaque_sample_id,
    select_diverse_pilot,
)
from archaeoai.terrain.index import TerrainIndexRecord, write_index
from archaeoai.terrain.patches import patch_bounds, required_grid_tiles
from archaeoai.terrain.privacy import (
    assert_coordinate_safe_mapping,
    ensure_private_output,
    verify_git_ignored,
)
from archaeoai.terrain.qa import write_private_qa_png
from archaeoai.terrain.raster import extract_patch, sha256_file
from archaeoai.terrain.representations import terrain_representations
from archaeoai.terrain.validation import TerrainValidationError
from archaeoai.terrain_metadata import fetch_terrain_qa

PROCESSING_VERSION = "e001-terrain-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, choices=range(1, 6), default=5)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="redownload the same bounded pilot windows for acquisition timing",
    )
    return parser.parse_args()


def _load_private_locations(path: Path) -> dict[int, PrivateSiteLocation]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "e001-private-locations-v1":
        raise ValueError("unsupported private location cache schema")
    records = {int(item["list_entry"]): PrivateSiteLocation(**item) for item in payload["records"]}
    if len(records) != 261:
        raise ValueError("private location cache must contain all 261 approved sites")
    return records


def _content_digest(data: np.ndarray, mask: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(data.astype("<f4")).tobytes())
    digest.update(np.ascontiguousarray(mask.astype(np.uint8)).tobytes())
    return digest.hexdigest()


def _provenance_id(location: PrivateSiteLocation) -> str:
    fields = (
        location.terrain_year,
        location.source_resolution_m,
        location.survey_program,
        EA_DTM_DATASET_ID,
    )
    return "EAP-" + hashlib.sha256("|".join(fields).encode()).hexdigest()[:12]


def _inventory_digest(rows: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for row in sorted(rows, key=lambda item: str(item["sample_id"])):
        digest.update(f"{row['sample_id']}:{row['raw_sha256']}\n".encode())
    return digest.hexdigest()


def main() -> int:
    args = parse_args()
    root = find_project_root()
    private_root = root / "data/private/e001"
    location_path = private_root / "approved-site-locations.json"
    ensure_private_output(root, location_path)
    verify_git_ignored(root, location_path)
    locations = _load_private_locations(location_path)
    accepted = load_accepted_sites(root / "outputs/feasibility/e001_curated_records.csv")
    selected = select_diverse_pilot(accepted, count=args.count)

    raw_root = private_root / "terrain/raw"
    processed_root = private_root / "terrain/processed"
    qa_root = private_root / "terrain/qa"
    receipt_rows: list[dict[str, object]] = []
    safe_rows: list[dict[str, object]] = []
    index_rows: list[TerrainIndexRecord] = []
    started = time.perf_counter()
    generated_at = datetime.now(UTC)

    for selected_site in selected:
        location = locations[selected_site.list_entry]
        sample_id = opaque_sample_id(location.list_entry)
        bounds = patch_bounds(
            (location.easting, location.northing), patch_size_m=128, resolution_m=1
        )
        tiles = required_grid_tiles(bounds)
        raw_path = raw_root / f"{sample_id}.tif"
        try:
            metadata_qa = fetch_terrain_qa((location.easting, location.northing), patch_size_m=128)
            if metadata_qa.coverage_status != "pass" or metadata_qa.provenance_status != "pass":
                raise RuntimeError("current EA metadata gate did not pass")
            existing_download = raw_path.exists()
            if existing_download and not args.refresh:
                raw_sha256 = sha256_file(raw_path)
                raw_bytes = raw_path.stat().st_size
                acquisition_action = "reused_validated_private_download"
            else:
                _path, raw_sha256, raw_bytes = download_wcs_geotiff(
                    bounds,
                    destination=raw_path,
                    project_root=root,
                )
                acquisition_action = "refreshed_download" if existing_download else "downloaded"
            patch = extract_patch(
                [raw_path],
                centre=(location.easting, location.northing),
                patch_size_m=128,
                resolution_m=1,
                max_nodata_fraction=0.2,
            )
            representations = terrain_representations(
                patch.data,
                resolution_m=1,
                mask=patch.mask,
                local_relief_radius_m=16,
            )
            processed_path = processed_root / f"{sample_id}.npz"
            ensure_private_output(root, processed_path)
            verify_git_ignored(root, processed_path)
            processed_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                processed_path,
                elevation=patch.data,
                mask=patch.mask,
                **representations,
            )
            qa_path = write_private_qa_png(
                representations,
                destination=qa_root / f"{sample_id}.png",
                project_root=root,
            )
            patch_digest = _content_digest(patch.data, patch.mask)
            representations_available = ";".join(representations)
            index_rows.append(
                TerrainIndexRecord(
                    sample_id=sample_id,
                    nhle_list_entry=location.list_entry,
                    geographic_group_id=location.geographic_group_id,
                    terrain_provenance_id=_provenance_id(location),
                    survey_year=location.terrain_year,
                    source_resolution_m=1.0,
                    processing_version=PROCESSING_VERSION,
                    patch_size_m=128,
                    acquisition_status="verified",
                    raw_qa_status="pass",
                    representation_qa_status="pass",
                    representations=representations_available,
                    qa_status="pass",
                    raw_sha256=raw_sha256,
                    patch_sha256=patch_digest,
                    processed_sha256=hashlib.sha256(processed_path.read_bytes()).hexdigest(),
                    cross_cell=len(tiles) > 1,
                )
            )
            safe_rows.append(
                {
                    "sample_id": sample_id,
                    "nhle_list_entry": location.list_entry,
                    "geographic_group_id": location.geographic_group_id,
                    "terrain_provenance_id": _provenance_id(location),
                    "survey_year": location.terrain_year,
                    "survey_program": location.survey_program,
                    "required_5km_cells": len(tiles),
                    "crosses_5km_boundary": len(tiles) > 1,
                    "raw_bytes": raw_bytes,
                    "raw_sha256": raw_sha256,
                    "processed_bytes": processed_path.stat().st_size,
                    "patch_sha256": patch_digest,
                    "crs": patch.crs,
                    "resolution_m": 1.0,
                    "dimensions": [patch.data.shape[0], patch.data.shape[1]],
                    "nodata_fraction": patch.qa.nodata_fraction,
                    "minimum_elevation_m": patch.qa.minimum_elevation_m,
                    "maximum_elevation_m": patch.qa.maximum_elevation_m,
                    "representations": list(representations),
                    "qa_status": "pass",
                    "acquisition_action": acquisition_action,
                }
            )
            receipt_rows.append(
                {
                    **safe_rows[-1],
                    "requested_bounds": asdict(bounds),
                    "wcs_url": EA_DTM_WCS_URL,
                    "coverage_id": EA_DTM_COVERAGE_ID,
                    "raw_path": str(raw_path),
                    "processed_path": str(processed_path),
                    "qa_path": str(qa_path),
                }
            )
        except Exception as error:
            reasons = (
                [str(reason) for reason in error.reasons]
                if isinstance(error, TerrainValidationError)
                else [type(error).__name__]
            )
            safe_rows.append(
                {
                    "sample_id": sample_id,
                    "nhle_list_entry": location.list_entry,
                    "geographic_group_id": location.geographic_group_id,
                    "qa_status": "rejected",
                    "failure_reasons": reasons,
                }
            )

    elapsed = time.perf_counter() - started
    safe_summary: dict[str, object] = {
        "phase": "2B bounded real-terrain pilot",
        "processing_version": PROCESSING_VERSION,
        "acquisition_version": ACQUISITION_VERSION,
        "generated_at": generated_at.isoformat(),
        "source_dataset_id": EA_DTM_DATASET_ID,
        "source_access_method": "Environment Agency WCS 2.0.1 bounded GetCoverage",
        "patch_specification": {
            "size_m": 128,
            "resolution_m": 1.0,
            "dimensions": [128, 128],
            "local_relief_radius_m": 16,
        },
        "attempted": len(selected),
        "passed": len(index_rows),
        "rejected": len(selected) - len(index_rows),
        "elapsed_seconds": round(elapsed, 3),
        "inventory_sha256": _inventory_digest(
            [row for row in safe_rows if row["qa_status"] == "pass"]
        ),
        "records": safe_rows,
        "privacy": {
            "stored_coordinates_in_tracked_output": False,
            "stored_geometry_in_tracked_output": False,
            "private_artifacts_git_ignored": True,
        },
        "claims": {
            "model_trained": False,
            "model_result": False,
            "archaeological_discovery": False,
        },
    }
    assert_coordinate_safe_mapping(safe_summary)
    output_root = root / "outputs/terrain"
    output_root.mkdir(parents=True, exist_ok=True)
    (output_root / "e001_pilot_summary.json").write_text(
        json.dumps(safe_summary, indent=2) + "\n", encoding="utf-8"
    )
    write_index(index_rows, output_root / "e001_terrain_index.csv")

    receipt_path = qa_root / "e001_pilot_private_receipt.json"
    ensure_private_output(root, receipt_path)
    verify_git_ignored(root, receipt_path)
    receipt_path.write_text(
        json.dumps({"generated_at": generated_at.isoformat(), "records": receipt_rows}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "attempted": len(selected),
                "passed": len(index_rows),
                "rejected": len(selected) - len(index_rows),
                "elapsed_seconds": round(elapsed, 3),
                "safe_sample_ids": [row.sample_id for row in index_rows],
            },
            indent=2,
        )
    )
    return 0 if len(index_rows) == len(selected) else 1


if __name__ == "__main__":
    raise SystemExit(main())
