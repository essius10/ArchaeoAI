"""Create the coordinate-safe Phase 4B manuscript evidence manifest."""

from __future__ import annotations

import json
from pathlib import Path

from archaeoai.external_error_analysis import EXPECTED_ANALYSIS_SHA256
from archaeoai.external_evaluation import (
    EXPECTED_DATASET_SHA256,
    EXPECTED_MODEL_STATE_SHA256,
    EXPECTED_PREDICTION_VECTOR_SHA256,
)
from archaeoai.manuscript import (
    EXPECTED_FIGURE_PATHS,
    EXPECTED_PHASE3C_RESULT_SHA256,
    EXPECTED_RF_CONFIG_SHA256,
    MANUSCRIPT_PATH,
    canonical_sha256,
    manuscript_figure_paths,
    manuscript_word_count,
    repository_sha256,
)
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "outputs/manuscript/e001_manuscript_evidence.json"


def freeze() -> dict:
    """Build the deterministic evidence manifest without model or private-data access."""
    manuscript_path = ROOT / MANUSCRIPT_PATH
    text = manuscript_path.read_text(encoding="utf-8")
    if manuscript_figure_paths(text) != EXPECTED_FIGURE_PATHS:
        raise ValueError("manuscript must use exactly the frozen coordinate-safe figure set")
    payload = {
        "schema_version": "e001-phase-4b-manuscript-evidence-v1",
        "phase": "4B manuscript and reproducibility package",
        "status": "READY_FOR_REVIEW",
        "manuscript": {
            "path": MANUSCRIPT_PATH,
            "title": (
                "Geographic generalization of a terrain-only Random Forest for documented "
                "bowl-barrow classification"
            ),
            "repository_sha256": repository_sha256(manuscript_path),
            "word_count": manuscript_word_count(text),
        },
        "frozen_evidence": {
            "phase3c_result_sha256": EXPECTED_PHASE3C_RESULT_SHA256,
            "external_dataset_sha256": EXPECTED_DATASET_SHA256,
            "prediction_vector_sha256": EXPECTED_PREDICTION_VECTOR_SHA256,
            "phase4a_analysis_sha256": EXPECTED_ANALYSIS_SHA256,
            "model_state_sha256": EXPECTED_MODEL_STATE_SHA256,
            "rf_config_sha256": EXPECTED_RF_CONFIG_SHA256,
        },
        "figures": {path: repository_sha256(ROOT / path) for path in sorted(EXPECTED_FIGURE_PATHS)},
        "citation_audit": {
            "status": "CITATION_REVIEW_REQUIRED",
            "unverified_reference_used_as_substantive_evidence": False,
            "peer_review_claimed_for_this_manuscript": False,
            "institutional_affiliation_claimed": False,
        },
        "scientific_boundary": {
            "phase3c_external_test_spent": True,
            "phase4a_label": "POST-HOC / EXPLORATORY",
            "new_model_training_performed": False,
            "confirmatory_result_changed": False,
            "public_release_executed": False,
        },
        "privacy": {
            "aggregate_only": True,
            "coordinates_written": False,
            "sample_identifiers_written": False,
            "private_paths_written": False,
            "sensitive_maps_included": False,
        },
    }
    assert_coordinate_safe_mapping(payload)
    payload["evidence_manifest_sha256"] = canonical_sha256(payload, omit="evidence_manifest_sha256")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(freeze(), indent=2))
