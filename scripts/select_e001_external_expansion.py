"""Run the frozen Phase 3B-R1 metadata-only supplementary-geography search.

The tracked receipt is aggregate and coordinate-safe. Record identifiers, titles,
exact coordinates, and record-level terrain metadata are written only below the
Git-ignored private data tree. This script never imports or loads modelling code.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from archaeoai.external_validation import (
    EXTERNAL_CELL_ID,
    EXTERNAL_CELL_SIZE_M,
    coarse_cell_id,
    distance_to_private_domain,
    validate_expansion_fallback_rule,
    validate_expansion_selection_rule,
)
from archaeoai.nhle_audit import (
    NHLE_LAYER_URL,
    TriageCategory,
    fetch_barrow_records,
    triage_title,
)
from archaeoai.terrain_metadata import COMPOSITE_COLLECTION, fetch_terrain_qa

ROOT = Path(__file__).resolve().parents[1]
RULE_PATH = ROOT / "configs/e001-phase-3b-r1-selection-rule.json"
FALLBACK_PATH = ROOT / "configs/e001-phase-3b-r1-multicell-fallback-rule.json"
AMENDMENT_PATH = ROOT / "configs/e001-phase-3b-r1-expansion-amendment.json"
PRIVATE_OUTPUT = ROOT / "data/private/e001/external/expansion/feasibility_manifest.json"
PUBLIC_OUTPUT = ROOT / "outputs/external_validation/e001_phase3b_r1_expansion_feasibility.json"
CELL_PATTERN = re.compile(r"BNG_25KM_E(-?\d+)_N(-?\d+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=6)
    return parser.parse_args()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _cell_indices(cell_id: str) -> tuple[int, int]:
    match = CELL_PATTERN.fullmatch(cell_id)
    if match is None:
        raise ValueError(f"invalid 25 km cell: {cell_id}")
    return int(match.group(1)), int(match.group(2))


def _cell_boundary_distance(cell_id: str, reference_cell: str) -> float:
    easting, northing = _cell_indices(cell_id)
    ref_easting, ref_northing = _cell_indices(reference_cell)
    x_gap = max(abs(easting - ref_easting) - 1, 0) * EXTERNAL_CELL_SIZE_M
    y_gap = max(abs(northing - ref_northing) - 1, 0) * EXTERNAL_CELL_SIZE_M
    return math.hypot(x_gap, y_gap)


def _all_e001_centres() -> tuple[tuple[float, float], ...]:
    positives = _load_json(ROOT / "data/private/e001/approved-site-locations.json")["records"]
    background_state = _load_json(ROOT / "data/private/e001/backgrounds/sampling_state.json")
    backgrounds = background_state["records"].values()
    centres = [(float(record["easting"]), float(record["northing"])) for record in positives]
    centres.extend((float(record["easting"]), float(record["northing"])) for record in backgrounds)
    if len(centres) != 522:
        raise ValueError(f"expected 522 E001 observation centres, found {len(centres)}")
    return tuple(centres)


def _private_domain_extent() -> tuple[float, float, float, float]:
    receipt = _load_json(
        ROOT / "data/private/e001/inference/controlled_domain_001/domain_receipt.json"
    )
    return tuple(float(receipt[key]) for key in ("left", "bottom", "right", "top"))


def _prior_reviewed_ids() -> set[int]:
    with (ROOT / "outputs/feasibility/e001_curated_records.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        e001_ids = {int(row["list_entry"]) for row in csv.DictReader(handle)}
    external = _load_json(ROOT / "data/private/e001/external/curation_manifest.json")
    external_ids = {int(record["list_entry"]) for record in external["records"]}
    if len(e001_ids) != 360 or len(external_ids) != 87:
        raise ValueError("prior reviewed-record counts do not match frozen evidence")
    if e001_ids.intersection(external_ids):
        raise ValueError("prior E001 and first-external review queues overlap")
    return e001_ids | external_ids


def _independent_candidates(records: list[Any], rule: dict[str, Any]) -> dict[str, list[Any]]:
    geography = rule["candidate_cell_definition"]
    minimum = float(geography["minimum_record_separation_from_all_E001_observations_m"])
    centres = _all_e001_centres()
    occupied_cells = {coarse_cell_id(centre) for centre in centres}
    domain = _private_domain_extent()
    prior_ids = _prior_reviewed_ids()
    first_easting, first_northing = _cell_indices(EXTERNAL_CELL_ID)
    minimum_index_difference = int(
        geography["minimum_chebyshev_cell_index_difference_from_first_cell"]
    )

    candidates: dict[str, list[Any]] = defaultdict(list)
    for record in records:
        if record.list_entry in prior_ids:
            continue
        if triage_title(record.name).category is not TriageCategory.PROBABLE_BOWL:
            continue
        if record.easting is None or record.northing is None:
            continue
        point = (record.easting, record.northing)
        cell = coarse_cell_id(point)
        cell_easting, cell_northing = _cell_indices(cell)
        if max(abs(cell_easting - first_easting), abs(cell_northing - first_northing)) < (
            minimum_index_difference
        ):
            continue
        if cell in occupied_cells:
            continue
        if min(math.dist(point, centre) for centre in centres) < minimum:
            continue
        if distance_to_private_domain(point, domain) < minimum:
            continue
        candidates[cell].append(record)
    return dict(candidates)


def _query_terrain(
    candidates: dict[str, list[Any]], *, workers: int
) -> tuple[dict[int, Any], dict[int, str]]:
    terrain: dict[int, Any] = {}
    errors: dict[int, str] = {}
    records = [record for values in candidates.values() for record in values]
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(fetch_terrain_qa, (record.easting, record.northing)): record
            for record in records
        }
        for future in as_completed(futures):
            record = futures[future]
            try:
                terrain[record.list_entry] = future.result()
            except Exception as error:  # network errors remain explicit, never silently pass
                errors[record.list_entry] = f"{type(error).__name__}: {error}"
    return terrain, errors


def _canonical_sha256(payload: dict[str, Any], *, omit: str) -> str:
    content = {key: value for key, value in payload.items() if key != omit}
    encoded = json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def main() -> int:
    args = parse_args()
    if not 1 <= args.workers <= 8:
        raise SystemExit("--workers must be between 1 and 8")
    if AMENDMENT_PATH.exists():
        raise SystemExit("frozen Phase 3B-R1 amendment exists; refusing to overwrite its receipt")
    rule = validate_expansion_selection_rule(RULE_PATH)
    fallback = validate_expansion_fallback_rule(FALLBACK_PATH)
    records = fetch_barrow_records()
    candidate_cells = _independent_candidates(records, rule)
    minimum_per_cell = fallback["deterministic_multicell_rule"][
        "minimum_preterrain_independent_probable_records_per_cell"
    ]
    terrain_cells = {
        cell: values for cell, values in candidate_cells.items() if len(values) >= minimum_per_cell
    }
    terrain, errors = _query_terrain(terrain_cells, workers=args.workers)

    cell_summaries = []
    for cell, values in terrain_cells.items():
        qa_pass = sum(
            terrain.get(record.list_entry) is not None
            and terrain[record.list_entry].coverage_status == "pass"
            and terrain[record.list_entry].provenance_status == "pass"
            and float(terrain[record.list_entry].resolution_m) <= 1.0
            for record in values
        )
        coverage_pass = sum(
            terrain.get(record.list_entry) is not None
            and terrain[record.list_entry].coverage_status == "pass"
            for record in values
        )
        cell_summaries.append(
            {
                "cell_id": cell,
                "independent_probable_records": len(values),
                "terrain_metadata_queries_completed": sum(
                    record.list_entry in terrain for record in values
                ),
                "terrain_metadata_query_errors": sum(
                    record.list_entry in errors for record in values
                ),
                "complete_1m_DTM_patch_coverage": coverage_pass,
                "QA_pass_probable_records": qa_pass,
                "minimum_boundary_separation_from_first_external_cell_m": int(
                    _cell_boundary_distance(cell, EXTERNAL_CELL_ID)
                ),
            }
        )
    ranked = sorted(
        cell_summaries,
        key=lambda cell: (
            -cell["QA_pass_probable_records"],
            -cell["independent_probable_records"],
            -cell["minimum_boundary_separation_from_first_external_cell_m"],
            cell["cell_id"],
        ),
    )
    selected: list[dict[str, Any]] = []
    cumulative = 0
    required = fallback["deterministic_multicell_rule"]["combined_minimum_QA_pass_probable_records"]
    maximum_cells = fallback["deterministic_multicell_rule"]["maximum_cells"]
    for cell in ranked[:maximum_cells]:
        selected.append(cell)
        cumulative += cell["QA_pass_probable_records"]
        if cumulative >= required:
            break
    feasible = cumulative >= required

    accessed_at = datetime.now(UTC).isoformat()
    private_payload = {
        "schema_version": "e001-phase-3b-r1-private-feasibility-v1",
        "warning": "PRIVATE: record metadata and exact coordinates; never commit or publish",
        "accessed_at": accessed_at,
        "selection_rule_sha256": rule["selection_rule_sha256"],
        "fallback_rule_sha256": fallback["fallback_rule_sha256"],
        "records": [
            {
                "list_entry": record.list_entry,
                "title": record.name,
                "easting": record.easting,
                "northing": record.northing,
                "cell_id": cell,
                "terrain_qa": asdict(terrain[record.list_entry])
                if record.list_entry in terrain
                else None,
                "terrain_query_error": errors.get(record.list_entry),
            }
            for cell, values in sorted(terrain_cells.items())
            for record in values
        ],
        "selected_cells": [cell["cell_id"] for cell in selected] if feasible else [],
        "external_RF_scoring_performed": False,
        "external_performance_metrics_computed": False,
    }
    PRIVATE_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE_OUTPUT.write_text(json.dumps(private_payload, indent=2) + "\n", encoding="utf-8")
    private_hash = hashlib.sha256(PRIVATE_OUTPUT.read_bytes()).hexdigest()

    public_payload = {
        "schema_version": "e001-phase-3b-r1-expansion-feasibility-v1",
        "phase": "3B-R1",
        "status": "SUPPLEMENTARY_GEOGRAPHY_FEASIBLE" if feasible else "NO_GO",
        "accessed_at": accessed_at,
        "sources": {
            "labels": NHLE_LAYER_URL,
            "terrain_metadata_collection": COMPOSITE_COLLECTION,
            "terrain_data_downloaded": False,
        },
        "frozen_rules": {
            "selection_rule_sha256": rule["selection_rule_sha256"],
            "fallback_rule_sha256": fallback["fallback_rule_sha256"],
        },
        "candidate_search": {
            "independent_candidate_cells_identified": len(candidate_cells),
            "cells_meeting_preterrain_minimum": len(terrain_cells),
            "single_cell_threshold": 28,
            "largest_single_cell_independent_probable_records": max(
                map(len, candidate_cells.values()), default=0
            ),
            "single_cell_rule_passed": False,
        },
        "candidate_regions": ranked,
        "selection": {
            "method": fallback["deterministic_multicell_rule"]["selection_operation"],
            "selected_cells": [cell["cell_id"] for cell in selected] if feasible else [],
            "selected_cell_count": len(selected) if feasible else 0,
            "aggregate_independent_probable_records": sum(
                cell["independent_probable_records"] for cell in selected
            )
            if feasible
            else 0,
            "aggregate_QA_pass_probable_records": cumulative if feasible else 0,
            "required_QA_pass_probable_records": required,
            "performance_used": False,
        },
        "independence": {
            "all_selected_records_outside_E001_cells_and_15km_buffer": feasible,
            "all_selected_records_outside_Phase2F_private_domain_15km_buffer": feasible,
            "all_selected_cells_at_least_25km_from_first_external_cell_boundary": feasible,
            "all_prior_reviewed_records_excluded": True,
        },
        "privacy": {
            "tracked_record_level_rows": False,
            "coordinates_written_to_tracked_output": False,
            "geometry_written_to_tracked_output": False,
            "private_manifest_git_ignored": True,
            "private_manifest_sha256": private_hash,
            "aggregate_only": True,
        },
        "execution_state": {
            "supplementary_records_curated": False,
            "terrain_rasters_downloaded": False,
            "backgrounds_constructed": False,
            "external_dataset_frozen": False,
            "external_RF_loaded": False,
            "external_RF_scoring_performed": False,
            "external_predictions_generated": False,
            "external_performance_metrics_computed": False,
        },
        "feasibility_receipt_sha256": "PENDING",
    }
    public_payload["feasibility_receipt_sha256"] = _canonical_sha256(
        public_payload, omit="feasibility_receipt_sha256"
    )
    PUBLIC_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_OUTPUT.write_text(json.dumps(public_payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(public_payload, indent=2))
    return 0 if feasible else 2


if __name__ == "__main__":
    raise SystemExit(main())
