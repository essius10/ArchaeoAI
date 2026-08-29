import json
from pathlib import Path

import numpy as np
import pytest

from archaeoai.final_evaluation import (
    FinalIndexRow,
    LoadedFinalPartition,
    group_bootstrap_intervals,
    metric_values,
    protocol_hash,
    validate_final_protocol,
)
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping


def _row(sample: str, group: str, label: str) -> FinalIndexRow:
    return FinalIndexRow(
        sample, label, group, "", "block", "provenance", "2020", "1.0", "a" * 64, "pass"
    )


def test_final_metrics_use_positive_bowl_barrow_as_positive_class() -> None:
    labels = np.asarray([0, 0, 1, 1], dtype=np.int8)
    predictions = np.asarray([0, 1, 0, 1], dtype=np.int8)
    probabilities = np.asarray([0.1, 0.8, 0.4, 0.9])
    metrics = metric_values(labels, predictions, probabilities)

    assert metrics["balanced_accuracy"] == 0.5
    assert metrics["accuracy"] == 0.5
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5
    assert metrics["confusion_matrix"] == {
        "true_unlabelled_background_predicted_unlabelled_background": 1,
        "true_unlabelled_background_predicted_positive_bowl_barrow": 1,
        "true_positive_bowl_barrow_predicted_unlabelled_background": 1,
        "true_positive_bowl_barrow_predicted_positive_bowl_barrow": 1,
    }


def test_group_bootstrap_is_deterministic_and_keeps_units() -> None:
    rows = (
        _row("a", "pair-a", "unlabelled_background"),
        _row("b", "pair-a", "positive_bowl_barrow"),
        _row("c", "pair-b", "unlabelled_background"),
        _row("d", "pair-b", "positive_bowl_barrow"),
    )
    final = LoadedFinalPartition(
        np.zeros((4, 1), dtype=np.float32),
        np.asarray([0, 1, 0, 1], dtype=np.int8),
        rows,
        tuple({} for _row_item in rows),
    )
    predictions = np.asarray([0, 1, 1, 0], dtype=np.int8)
    probabilities = np.asarray([0.1, 0.9, 0.8, 0.2])
    first = group_bootstrap_intervals(final, predictions, probabilities, iterations=100, seed=42)
    second = group_bootstrap_intervals(final, predictions, probabilities, iterations=100, seed=42)

    assert first == second
    assert first["unit_count"] == 2
    assert all(item["valid_replicates"] == 100 for item in first["intervals"].values())


def test_protocol_hash_rejects_tampering(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    protocol = json.loads(
        (root / "configs/e001-phase-2d-b-final-protocol.json").read_text(encoding="utf-8")
    )
    config = json.loads(
        (root / "outputs/modelling/e001_primary_baseline_config.json").read_text(encoding="utf-8")
    )
    protocol["protocol_sha256"] = protocol_hash(protocol)
    protocol_path = tmp_path / "protocol.json"
    config_path = tmp_path / "config.json"
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    config_path.write_text(json.dumps(config), encoding="utf-8")
    validate_final_protocol(protocol_path, config_path)

    protocol["classification_threshold"] = 0.4
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_final_protocol(protocol_path, config_path)


def test_frozen_final_result_receipt_is_coordinate_safe_and_complete() -> None:
    root = Path(__file__).resolve().parents[1]
    result = json.loads(
        (root / "outputs/modelling/e001_random_vs_geographic.json").read_text(encoding="utf-8")
    )
    assert_coordinate_safe_mapping(result)

    assert result["final_test_evaluated"] is True
    assert result["selection_commit"] == "790ac9f4b99da94e8f9bab2a6aed70b34ac88558"
    assert result["primary_config_sha256"] == (
        "20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"
    )
    assert result["secondary_final_baselines"] == []
    assert result["no_retuning_declaration"] is True
    assert result["conditions"]["random"]["counts"] == {
        "total": 62,
        "positive_bowl_barrow": 31,
        "unlabelled_background": 31,
    }
    assert result["conditions"]["geographic"]["counts"] == {
        "total": 62,
        "positive_bowl_barrow": 31,
        "unlabelled_background": 31,
    }


def test_final_audit_records_zero_missingness_and_no_sample_outputs() -> None:
    root = Path(__file__).resolve().parents[1]
    audit = json.loads(
        (root / "outputs/modelling/e001_final_model_audit.json").read_text(encoding="utf-8")
    )
    assert_coordinate_safe_mapping(audit)
    assert audit["privacy"] == {
        "aggregate_only": True,
        "coordinates_in_output": False,
        "sample_identifiers_in_output": False,
        "maps_created": False,
    }
    assert all(
        condition["terrain_summary_by_correctness"][status]["missing_fraction"]
        == {"mean": 0.0, "median": 0.0}
        for condition in audit["conditions"].values()
        for status in ("correct", "error")
    )
