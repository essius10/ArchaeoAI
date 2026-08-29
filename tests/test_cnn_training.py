import csv
import json
from pathlib import Path

import numpy as np
import pytest
import torch

from archaeoai.cnn_training import (
    CLASSIFICATION_THRESHOLD,
    binary_metrics,
    model_state_sha256,
    validate_training_contract,
)
from archaeoai.deep_learning import CompactTerrainCNN, validate_cnn_protocol
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

ROOT = Path(__file__).resolve().parents[1]


def test_executable_training_contract_matches_frozen_protocol() -> None:
    protocol = validate_cnn_protocol(ROOT / "outputs/deep_learning/e001_cnn_protocol.json")
    validate_training_contract(protocol)
    assert CLASSIFICATION_THRESHOLD == 0.5


def test_training_contract_fails_closed_on_scientific_change() -> None:
    protocol = validate_cnn_protocol(ROOT / "outputs/deep_learning/e001_cnn_protocol.json").copy()
    protocol["batch_size"] = 32
    with pytest.raises(ValueError, match="batch size"):
        validate_training_contract(protocol)


def test_binary_metrics_and_confusion_inputs_are_deterministic() -> None:
    labels = np.asarray([0, 0, 1, 1], dtype=np.int8)
    scores = np.asarray([0.1, 0.6, 0.4, 0.9], dtype=np.float64)
    predictions = (scores >= CLASSIFICATION_THRESHOLD).astype(np.int8)
    metrics = binary_metrics(labels, predictions, scores)
    assert metrics["balanced_accuracy"] == 0.5
    assert metrics["accuracy"] == 0.5
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5


def test_model_state_checksum_is_stable_and_sensitive() -> None:
    torch.manual_seed(7)
    first = CompactTerrainCNN().state_dict()
    first_hash = model_state_sha256(first)
    assert first_hash == model_state_sha256(first)
    changed = {name: value.clone() for name, value in first.items()}
    changed["head.3.bias"][0] += 1
    assert model_state_sha256(changed) != first_hash


def test_frozen_cnn_results_contain_all_primary_runs() -> None:
    path = ROOT / "outputs/deep_learning/e001_cnn_fold_results.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    expected = {
        (f"fold_{fold}", seed) for fold in range(1, 6) for seed in (20260829, 20260830, 20260831)
    }
    assert len(rows) == 15
    assert {(row["fold"], int(row["seed"])) for row in rows} == expected


def test_frozen_cnn_summary_matches_verified_aggregate() -> None:
    path = ROOT / "outputs/deep_learning/e001_cnn_summary.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    assert_coordinate_safe_mapping(summary)
    assert summary["status"] == "COMPLETE"
    assert summary["primary_runs_completed"] == 15
    assert summary["no_retuning_declaration"] is True
    assert summary["fold_mean_balanced_accuracy"]["mean"] == pytest.approx(0.7008655951549033)
    assert summary["aggregate_confusion_across_15_runs"] == {
        "tn": 532,
        "fp": 251,
        "fn": 217,
        "tp": 566,
    }
    assert summary["technical_failures"] == []
    assert summary["secondary_conditions_run"] == []
    assert summary["stronger_model_classification"] == "CNN NOT JUSTIFIED AT CURRENT DATA SCALE"
    assert summary["phase_2f_recommendation"] == "USE RANDOM FOREST FOR PHASE 2F"


def test_frozen_cnn_comparison_preserves_protocol_and_fold_hashes() -> None:
    path = ROOT / "outputs/deep_learning/e001_cnn_vs_rf.json"
    comparison = json.loads(path.read_text(encoding="utf-8"))
    assert_coordinate_safe_mapping(comparison)
    assert comparison["protocol_sha256"] == (
        "6007a2b62157195c26a05474935d88f1e3ed7b6c6780572f35c1162ab08d39c0"
    )
    assert comparison["fold_assignment_sha256"] == (
        "825eb1088a53f764f991bf6bb22f2c9fe6eeb868916a5abab92012eed85d90ab"
    )
    assert comparison["cnn_mean_balanced_accuracy"] == pytest.approx(0.7008655951549033)
    assert comparison["rf_mean_balanced_accuracy"] == pytest.approx(0.823406)
    assert comparison["cnn_minus_rf"] == pytest.approx(-0.12254040484509665)
    assert [row["cnn_mean_balanced_accuracy"] for row in comparison["folds"]] == (
        pytest.approx(
            [
                0.7561728395061729,
                0.660377358490566,
                0.69,
                0.6944444444444445,
                0.7033333333333333,
            ]
        )
    )
