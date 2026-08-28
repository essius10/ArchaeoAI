"""Prepare and summarize deterministic private visual QA for E001 backgrounds."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import warnings
from collections import Counter
from pathlib import Path

import numpy as np
import rasterio
from rasterio.errors import NotGeoreferencedWarning

from archaeoai.paths import find_project_root
from archaeoai.terrain.full_dataset import load_processed_archive
from archaeoai.terrain.privacy import (
    assert_coordinate_safe_mapping,
    ensure_private_output,
    verify_git_ignored,
)
from archaeoai.terrain.qa import write_private_qa_strip

VISUAL_SEED = "E001-phase-2C-background-visual-QA-v1"
VISUAL_SAMPLE_SIZE = 25
ALLOWED_OBSERVATIONS = {
    "technical_ok",
    "track_or_road",
    "field_boundary_or_drainage",
    "forestry_pattern",
    "hard_anthropogenic_relief",
    "major_building_water_or_quarry",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--finalize", action="store_true")
    return parser.parse_args()


def _rank(sample_id: str) -> str:
    return hashlib.sha256(f"{VISUAL_SEED}:{sample_id}".encode()).hexdigest()


def _load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    if len(rows) < VISUAL_SAMPLE_SIZE:
        raise ValueError("background pilot must contain at least 25 QA-passed records")
    return rows


def _select(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    selected: dict[str, dict[str, str]] = {}
    groups: set[str] = set()
    provenances: set[str] = set()
    years: set[str] = set()
    ranked = sorted(rows, key=lambda row: _rank(row["sample_id"]))
    while len(selected) < VISUAL_SAMPLE_SIZE:
        candidates = [row for row in ranked if row["sample_id"] not in selected]
        choice = max(
            candidates,
            key=lambda row: (
                int(row["geographic_group_id"] not in groups)
                + int(row["terrain_provenance_id"] not in provenances)
                + int(row["survey_year"] not in years),
                int(row["geographic_group_id"] not in groups),
                int(row["terrain_provenance_id"] not in provenances),
                _rank(row["sample_id"]),
            ),
        )
        selected[choice["sample_id"]] = choice
        groups.add(choice["geographic_group_id"])
        provenances.add(choice["terrain_provenance_id"])
        years.add(choice["survey_year"])
    return list(selected.values())


def _write_contact_sheets(paths: list[Path], *, qa_root: Path, root: Path) -> None:
    for batch_index, start in enumerate(range(0, len(paths), 5), start=1):
        arrays = []
        for path in paths[start : start + 5]:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", NotGeoreferencedWarning)
                with rasterio.open(path) as dataset:
                    arrays.append(dataset.read(1))
        gutter = 2
        sheet = np.full(
            (
                sum(array.shape[0] for array in arrays) + gutter * (len(arrays) - 1),
                arrays[0].shape[1],
            ),
            255,
            dtype=np.uint8,
        )
        row_offset = 0
        for array in arrays:
            sheet[row_offset : row_offset + array.shape[0], :] = array
            row_offset += array.shape[0] + gutter
        destination = ensure_private_output(
            root, qa_root / "contact_sheets" / f"background-qa-batch-{batch_index:02d}.png"
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


def _prepare_review(path: Path, selected: list[dict[str, str]]) -> None:
    if path.exists():
        return
    payload = {
        "schema_version": "e001-private-background-visual-review-v1",
        "warning": "CONTROLLED: linked to private background terrain; never commit or publish",
        "policy": (
            "Review technical validity and modern confounds only. Do not remove a patch because "
            "it resembles archaeology."
        ),
        "records": [
            {"sample_id": row["sample_id"], "status": "pending", "observations": []}
            for row in selected
        ],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _review_summary(path: Path, selected_ids: set[str]) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("records", [])
    if {row.get("sample_id") for row in rows} != selected_ids:
        raise ValueError("private review does not match the deterministic selection")
    if any(row.get("status") not in {"pending", "pass", "hard_invalid"} for row in rows):
        raise ValueError("unsupported private visual-review status")
    if any(set(row.get("observations", [])) - ALLOWED_OBSERVATIONS for row in rows):
        raise ValueError("unsupported private visual-review observation")
    status_counts = Counter(str(row["status"]) for row in rows)
    observation_counts = Counter(
        observation for row in rows for observation in row.get("observations", [])
    )
    return {
        "reviewed": len(rows) - status_counts["pending"],
        "pending": status_counts["pending"],
        "passed": status_counts["pass"],
        "hard_invalid": status_counts["hard_invalid"],
        "observation_counts": dict(sorted(observation_counts.items())),
    }


def main() -> int:
    args = parse_args()
    root = find_project_root()
    rows = _load_rows(root / "outputs/background/e001_background_index.csv")
    selected = _select(rows)
    qa_root = root / "data/private/e001/backgrounds/qa/pilot40_visual"
    strip_paths = []
    for row in selected:
        archive = root / "data/private/e001/backgrounds/processed" / f"{row['sample_id']}.npz"
        elevation, _mask, representations = load_processed_archive(archive)
        strip_paths.append(
            write_private_qa_strip(
                {"elevation": elevation, **representations},
                destination=qa_root / "strips" / f"{row['sample_id']}.png",
                project_root=root,
            )
        )
    _write_contact_sheets(strip_paths, qa_root=qa_root, root=root)
    selection_path = ensure_private_output(root, qa_root / "selection.json")
    verify_git_ignored(root, selection_path)
    selection_path.write_text(
        json.dumps(
            {
                "schema_version": "e001-private-background-visual-selection-v1",
                "seed": VISUAL_SEED,
                "sample_ids_in_contact_sheet_order": [row["sample_id"] for row in selected],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    review_path = ensure_private_output(root, qa_root / "review.json")
    verify_git_ignored(root, review_path)
    _prepare_review(review_path, selected)
    review = _review_summary(review_path, {row["sample_id"] for row in selected})
    if not args.finalize:
        print(json.dumps({"qa_root": str(qa_root), **review}, indent=2))
        return 2 if review["pending"] else 0
    if review["pending"] or review["hard_invalid"]:
        print(json.dumps(review, indent=2))
        return 2
    summary: dict[str, object] = {
        "phase": "2C unlabelled-background pilot40 visual QA",
        "seed": VISUAL_SEED,
        "sample_size": VISUAL_SAMPLE_SIZE,
        "geographic_groups": len({row["geographic_group_id"] for row in selected}),
        "survey_years": len({row["survey_year"] for row in selected}),
        "provenance_ids": len({row["terrain_provenance_id"] for row in selected}),
        **review,
        "policy": {
            "technical_and_confound_review_only": True,
            "archaeology_resemblance_not_a_rejection_reason": True,
            "private_visuals_ignored": True,
        },
    }
    assert_coordinate_safe_mapping(summary)
    destination = root / "outputs/background/e001_background_pilot40_visual_qa.json"
    destination.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
