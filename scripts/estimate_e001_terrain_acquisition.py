"""Estimate the full E001 terrain workload without downloading additional terrain."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path
from statistics import mean

from archaeoai.paths import find_project_root
from archaeoai.terrain.acquisition import PrivateSiteLocation
from archaeoai.terrain.patches import patch_bounds, required_grid_tiles
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping, verify_git_ignored


def _load_private_locations(path: Path) -> tuple[PrivateSiteLocation, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = tuple(PrivateSiteLocation(**item) for item in payload["records"])
    if payload.get("schema_version") != "e001-private-locations-v1" or len(records) != 261:
        raise ValueError("expected the complete private E001 location cache")
    return records


def _overlap(first: PrivateSiteLocation, second: PrivateSiteLocation) -> bool:
    a = patch_bounds((first.easting, first.northing), patch_size_m=128)
    b = patch_bounds((second.easting, second.northing), patch_size_m=128)
    return a.left < b.right and a.right > b.left and a.bottom < b.top and a.top > b.bottom


def main() -> int:
    root = find_project_root()
    private_path = root / "data/private/e001/approved-site-locations.json"
    verify_git_ignored(root, private_path)
    locations = _load_private_locations(private_path)
    pilot = json.loads(
        (root / "outputs/terrain/e001_pilot_summary.json").read_text(encoding="utf-8")
    )
    passed = [record for record in pilot["records"] if record["qa_status"] == "pass"]
    if len(passed) != 5 or pilot["rejected"] != 0:
        raise ValueError("a successful five-site pilot is required before workload estimation")

    unique_cells: set[str] = set()
    crossing_sites = 0
    duplicate_location_pairs = []
    overlapping_pairs = []
    cross_group_overlaps = []
    coordinate_groups: dict[tuple[float, float], list[int]] = {}
    for location in locations:
        coordinate_groups.setdefault((location.easting, location.northing), []).append(
            location.list_entry
        )
        tiles = required_grid_tiles(
            patch_bounds((location.easting, location.northing), patch_size_m=128)
        )
        unique_cells.update(tile.tile_id for tile in tiles)
        crossing_sites += len(tiles) > 1
    for ids in coordinate_groups.values():
        duplicate_location_pairs.extend(combinations(sorted(ids), 2))
    for first, second in combinations(locations, 2):
        if _overlap(first, second):
            pair = tuple(sorted((first.list_entry, second.list_entry)))
            overlapping_pairs.append(pair)
            if first.geographic_group_id != second.geographic_group_id:
                cross_group_overlaps.append(pair)

    average_raw = mean(record["raw_bytes"] for record in passed)
    average_processed = mean(record["processed_bytes"] for record in passed)
    seconds_per_site = pilot["elapsed_seconds"] / pilot["attempted"]
    site_count = len(locations)
    float_layers = 5  # elevation plus four representations
    per_patch_uncompressed = 128 * 128 * (float_layers * 4 + 1)
    tile_equivalent_uncompressed = len(unique_cells) * 5000 * 5000 * 4
    decision = (
        "GO FOR FULL TERRAIN DATASET"
        if not duplicate_location_pairs and not cross_group_overlaps
        else "CONDITIONAL GO"
    )
    summary: dict[str, object] = {
        "phase": "2B full terrain acquisition gate",
        "generated_at": datetime.now(UTC).isoformat(),
        "decision": decision,
        "strategy": "261 independent 128 m WCS windows; do not download complete 5 km tiles",
        "accepted_sites": site_count,
        "metadata_screened_complete_coverage": site_count,
        "pixel_verified_complete_coverage": len(passed),
        "unique_required_5km_cells_if_tile_route_used": len(unique_cells),
        "sites_crossing_5km_cell_boundaries": crossing_sites,
        "wcs_requests_required": site_count,
        "estimated_raw_wcs_bytes": round(average_raw * site_count),
        "estimated_processed_compressed_bytes": round(average_processed * site_count),
        "estimated_processed_uncompressed_bytes": per_patch_uncompressed * site_count,
        "full_5km_tile_route_uncompressed_bytes": tile_equivalent_uncompressed,
        "estimated_sequential_seconds_at_pilot_rate": round(seconds_per_site * site_count),
        "estimate_basis": {
            "pilot_sites": len(passed),
            "average_raw_bytes": round(average_raw),
            "average_processed_compressed_bytes": round(average_processed),
            "average_seconds_per_site": round(seconds_per_site, 3),
            "warning": (
                "Network/service variability and retries are not represented by five samples."
            ),
        },
        "spatial_integrity": {
            "duplicate_exact_location_pairs": [list(pair) for pair in duplicate_location_pairs],
            "overlapping_128m_patch_pairs": len(overlapping_pairs),
            "cross_group_overlapping_patch_pairs": [list(pair) for pair in cross_group_overlaps],
            "policy": "Overlapping observations must stay grouped and cannot cross a future split.",
        },
        "privacy": {
            "coordinate_list_tracked": False,
            "tile_cell_list_tracked": False,
            "aggregate_counts_only": True,
        },
        "scope": {
            "full_download_started": False,
            "background_generated": False,
            "split_finalized": False,
            "model_trained": False,
        },
    }
    assert_coordinate_safe_mapping(summary)
    output = root / "outputs/terrain/e001_acquisition_estimate.json"
    output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
