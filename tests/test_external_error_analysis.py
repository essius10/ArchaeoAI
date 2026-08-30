"""Regression tests for the frozen post-hoc Phase 4A analysis."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from archaeoai.external_error_analysis import (
    EXPECTED_ANALYSIS_SHA256,
    EXPECTED_ERROR_GROUPS,
    EXPECTED_FIGURE_REPOSITORY_SHA256,
    analysis_sha256,
    validate_external_error_analysis,
    verify_phase3c_unchanged,
    verify_phase4a_figure_files,
)
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

ROOT = Path(__file__).resolve().parents[1]
RESULT_PATH = ROOT / "outputs/external_validation/e001_phase4a_error_analysis.json"


@pytest.fixture(scope="module")
def result() -> dict:
    return validate_external_error_analysis(RESULT_PATH)


def test_phase4a_result_is_hash_bound_and_exploratory(result: dict) -> None:
    assert analysis_sha256(result) == EXPECTED_ANALYSIS_SHA256
    assert result["analysis_label"] == "POST-HOC / EXPLORATORY"
    assert result["external_test_spent"] is True
    assert result["confirmatory_result_unchanged"] is True


def test_phase4a_reproduces_frozen_confusion_groups(result: dict) -> None:
    assert result["error_groups"] == EXPECTED_ERROR_GROUPS
    assert sum(result["error_groups"].values()) == 120
    assert {
        group: summary["count"] for group, summary in result["model_score_distributions"].items()
    } == {"TP": 49, "TN": 52, "FP": 8, "FN": 11}


def test_phase4a_preserves_phase3c_confirmatory_result(result: dict) -> None:
    verify_phase3c_unchanged(ROOT, result)
    source = result["source_bindings"]
    assert source["phase3c_balanced_accuracy"] == 0.8416666666666667
    assert (source["phase3c_lower_95"], source["phase3c_upper_95"]) == (0.775, 0.9)


def test_phase4a_public_payload_is_coordinate_safe(result: dict) -> None:
    assert_coordinate_safe_mapping(result)
    assert result["privacy"] == {
        "aggregate_only": True,
        "coordinates_written": False,
        "sample_identifiers_written": False,
        "private_prediction_rows_written": False,
        "maps_created": False,
        "private_panels_tracked": False,
    }


def test_phase4a_figures_are_hash_bound_and_coordinate_safe(result: dict) -> None:
    verify_phase4a_figure_files(ROOT, result)
    assert len(result["figures"]) == 5
    assert set(result["figures"]) == set(EXPECTED_FIGURE_REPOSITORY_SHA256)


def test_phase4a_figure_hashes_accept_only_frozen_lf_repository_form(
    result: dict, tmp_path: Path
) -> None:
    for relative in result["figures"]:
        source = ROOT / relative
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes().replace(b"\r\n", b"\n"))
    verify_phase4a_figure_files(tmp_path, result)


def test_phase4a_regional_results_flag_small_strata(result: dict) -> None:
    regions = result["regional_descriptive_results"]
    assert len(regions) == 5
    assert regions["BNG_25KM_E16_N5"]["high_uncertainty_small_stratum"] is False
    assert all(
        row["high_uncertainty_small_stratum"]
        for name, row in regions.items()
        if name != "BNG_25KM_E16_N5"
    )
    assert all(row["analysis_label"] == "POST-HOC / EXPLORATORY" for row in regions.values())


def test_phase4a_provenance_is_descriptive_only(result: dict) -> None:
    provenance = result["provenance_descriptive_results"]
    assert provenance["causal_interpretation_allowed"] is False
    assert provenance["survey_program_counts"] == {"National LIDAR Programme": 120}
    assert provenance["source_resolution_m_counts"] == {"1.0": 120}
    assert set(provenance["survey_year"]) == {"2019", "2020", "2021"}


def test_phase4a_no_data_does_not_distinguish_groups(result: dict) -> None:
    for summary in result["nodata_fraction_by_error_group"].values():
        assert summary["minimum"] == 0.0
        assert summary["maximum"] == 0.0


def test_phase4a_preserves_no_training_no_rescoring_boundary(result: dict) -> None:
    science = result["scientific_status"]
    assert science["preferred_current_model"] == "frozen E001 Random Forest"
    assert science["phase3_external_data_used_for_current_model_training"] is False
    assert science["future_model_using_phase3_data_is_new_model_generation"] is True
    assert science["new_independent_evaluation_required_for_future_model"] is True
    assert science["retraining_performed"] is False
    assert science["rescoring_performed"] is False
    assert science["threshold_changed"] is False
    assert science["observations_removed_or_relabelled"] is False


def test_phase4a_script_contains_no_model_training_or_prediction_call() -> None:
    source = (ROOT / "scripts/analyze_e001_external_errors.py").read_text(encoding="utf-8")
    prohibited = (
        ".fit(",
        "RandomForestClassifier",
        "predict(",
        "predict_proba(",
        "load_private_model",
        "score_feature_matrix",
    )
    assert not any(token in source for token in prohibited)


def test_phase4a_private_panels_remain_ignored_and_metadata_free_if_present(result: dict) -> None:
    ignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "data/private/" in ignore_text
    panel_root = ROOT / "data/private/e001/external/error_analysis/panels"
    if not panel_root.exists():
        pytest.skip("private exploratory panels are intentionally absent from this checkout")
    panels = sorted(panel_root.glob("*.png"))
    assert [path.name for path in panels] == [
        "FN_01.png",
        "FN_02.png",
        "FP_01.png",
        "FP_02.png",
        "TN_01.png",
        "TN_02.png",
        "TP_01.png",
        "TP_02.png",
    ]
    assert all(path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") for path in panels)
    assert result["private_exemplars"]["count"] == 8


def test_phase4a_frozen_hash_rejects_mutation(result: dict, tmp_path: Path) -> None:
    mutated = json.loads(json.dumps(result))
    mutated["error_groups"]["FN"] = 10
    path = tmp_path / "mutated.json"
    path.write_text(json.dumps(mutated), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_external_error_analysis(path)
