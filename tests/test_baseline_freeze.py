import json
from pathlib import Path

from archaeoai.model_data import authorize_final_test, validate_frozen_primary_config
from archaeoai.modelling import DevelopmentResult, select_primary
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "outputs/modelling"


def test_development_matrix_is_complete_and_contains_no_final_result() -> None:
    payload = json.loads(
        (OUTPUT_ROOT / "e001_phase_2d_a_development_results.json").read_text(encoding="utf-8")
    )
    assert_coordinate_safe_mapping(payload)

    assert payload["partitions_accessed"] == ["train", "development"]
    assert payload["final_test_accessed"] is False
    assert payload["random_condition_evaluated"] is False
    assert len(payload["results"]) == 15
    assert {(row["model"], row["representation"]) for row in payload["results"]} == {
        (model, representation)
        for model in ("dummy", "logistic_regression", "random_forest")
        for representation in (
            "normalized_elevation",
            "slope",
            "hillshade",
            "local_relief",
            "all_four",
        )
    }
    assert payload["scope"] == {
        "final_accuracy_computed": False,
        "final_f1_computed": False,
        "final_roc_auc_computed": False,
        "predictions_inspected": False,
    }


def test_recorded_primary_follows_frozen_selection_rule() -> None:
    payload = json.loads(
        (OUTPUT_ROOT / "e001_phase_2d_a_development_results.json").read_text(encoding="utf-8")
    )
    results = [DevelopmentResult(**row) for row in payload["results"]]
    selected = select_primary(results)

    assert payload["selected"] == {
        "model": selected.model,
        "representation": selected.representation,
        "feature_count": selected.feature_count,
        "balanced_accuracy": selected.balanced_accuracy,
        "roc_auc": selected.roc_auc,
    }
    assert selected.model == "random_forest"
    assert selected.representation == "all_four"


def test_frozen_primary_hash_and_future_final_guard_are_valid() -> None:
    config_path = OUTPUT_ROOT / "e001_primary_baseline_config.json"
    config = validate_frozen_primary_config(config_path)
    manifest_path = ROOT / "outputs/dataset/e001_geographic_split_manifest.json"

    assert config["final_test_evaluated"] is False
    assert config["classification_threshold"] == 0.5
    assert config["feature_count"] == 4096
    assert (
        authorize_final_test(config_path, manifest_path, condition="geographic")["config_sha256"]
        == config["config_sha256"]
    )


def test_metadata_shortcut_and_permutation_audits_are_recorded() -> None:
    payload = json.loads(
        (OUTPUT_ROOT / "e001_phase_2d_a_development_results.json").read_text(encoding="utf-8")
    )
    differences = [
        audit["maximum_absolute_class_count_difference"]
        for fields in payload["metadata_shortcut_audit"].values()
        for audit in fields.values()
    ]
    assert differences == [0] * 8
    assert payload["permutation_sanity_summary"]["runs"] == 5
    assert payload["permutation_sanity_summary"]["selected_score_exceeds_all_permutations"] is True
    assert payload["permutation_sanity_summary"]["used_for_selection"] is False
