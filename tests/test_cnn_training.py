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
