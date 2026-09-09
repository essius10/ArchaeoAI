"""Phase 6D tests for the hash-bound private Random Forest adapter."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier

import archaeoai.inference_system.private_model_adapter as private_adapter
from archaeoai.inference import FEATURE_COUNT
from archaeoai.inference_system import (
    APPROVED_MODEL_ARTIFACT_SHA256,
    FROZEN_MODEL_STATE_SHA256,
    ApprovedPrivateModelLoadError,
    ApprovedPrivateRandomForestAdapter,
    ModelIdentifier,
    approved_private_model_reference,
    load_approved_private_random_forest,
)


def _project_with_private_placeholder(tmp_path: Path) -> Path:
    target = tmp_path / "data/private/e001/inference/e001_phase2f_random_forest.pkl"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"inert-test-placeholder")
    return tmp_path


def _patch_preload_gates(
    monkeypatch: pytest.MonkeyPatch,
    *,
    estimator: object,
) -> list[str]:
    calls: list[str] = []

    def ignored(_root: Path, _path: Path) -> None:
        calls.append("ignored")

    def verified(_root: Path, _reference: object) -> str:
        calls.append("artifact_verified")
        return APPROVED_MODEL_ARTIFACT_SHA256

    def loaded(*_args: object, **_kwargs: object) -> object:
        calls.append("deserialized")
        return estimator

    monkeypatch.setattr(private_adapter, "verify_git_ignored", ignored)
    monkeypatch.setattr(private_adapter, "verify_approved_model_artifact", verified)
    monkeypatch.setattr(private_adapter, "load_private_model", loaded)
    return calls


def test_approved_reference_is_fixed_and_accepts_no_model_path(tmp_path: Path) -> None:
    reference = approved_private_model_reference(tmp_path)
    assert reference.model_identifier is ModelIdentifier.E001_FROZEN_RANDOM_FOREST
    assert reference.model_config_sha256 == (
        "20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"
    )
    assert (
        reference.path
        == (tmp_path / "data/private/e001/inference/e001_phase2f_random_forest.pkl").resolve()
    )


def test_artifact_mismatch_stops_before_deserialization(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _project_with_private_placeholder(tmp_path)
    loaded = False
    monkeypatch.setattr(private_adapter, "verify_git_ignored", lambda *_args: None)
    monkeypatch.setattr(
        private_adapter,
        "verify_approved_model_artifact",
        lambda *_args: (_ for _ in ()).throw(ValueError("mismatch")),
    )

    def forbidden_load(*_args: object, **_kwargs: object) -> object:
        nonlocal loaded
        loaded = True
        return object()

    monkeypatch.setattr(private_adapter, "load_private_model", forbidden_load)
    with pytest.raises(ApprovedPrivateModelLoadError, match="APPROVED_PRIVATE_MODEL_UNAVAILABLE"):
        load_approved_private_random_forest(root)
    assert loaded is False


def test_missing_artifact_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(private_adapter, "verify_git_ignored", lambda *_args: None)
    with pytest.raises(ApprovedPrivateModelLoadError, match="APPROVED_PRIVATE_MODEL_UNAVAILABLE"):
        load_approved_private_random_forest(tmp_path)


def test_unexpected_estimator_class_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _project_with_private_placeholder(tmp_path)
    calls = _patch_preload_gates(monkeypatch, estimator=object())
    with pytest.raises(ApprovedPrivateModelLoadError):
        load_approved_private_random_forest(root)
    assert calls == ["ignored", "artifact_verified", "deserialized"]


def test_model_state_mismatch_fails_closed(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = _project_with_private_placeholder(tmp_path)
    estimator = RandomForestClassifier()
    _patch_preload_gates(monkeypatch, estimator=estimator)
    monkeypatch.setattr(private_adapter, "model_state_sha256", lambda _model: "0" * 64)
    with pytest.raises(ApprovedPrivateModelLoadError):
        load_approved_private_random_forest(root)


def test_valid_load_order_and_adapter_identity(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _project_with_private_placeholder(tmp_path)
    estimator = RandomForestClassifier()
    calls = _patch_preload_gates(monkeypatch, estimator=estimator)
    monkeypatch.setattr(
        private_adapter, "model_state_sha256", lambda _model: FROZEN_MODEL_STATE_SHA256
    )
    adapter = load_approved_private_random_forest(root)
    assert calls == ["ignored", "artifact_verified", "deserialized"]
    assert adapter.model_identifier is ModelIdentifier.E001_FROZEN_RANDOM_FOREST
    assert adapter.model_artifact_sha256 == APPROVED_MODEL_ARTIFACT_SHA256


def test_adapter_rejects_config_identity_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    estimator = RandomForestClassifier()
    monkeypatch.setattr(
        private_adapter, "model_state_sha256", lambda _model: FROZEN_MODEL_STATE_SHA256
    )
    with pytest.raises(ValueError, match="configuration identity mismatch"):
        ApprovedPrivateRandomForestAdapter(estimator, model_config_sha256="0" * 64)


def test_adapter_preserves_exact_read_only_model_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    estimator = RandomForestClassifier()
    monkeypatch.setattr(
        private_adapter, "model_state_sha256", lambda _model: FROZEN_MODEL_STATE_SHA256
    )
    observed: dict[str, object] = {}

    def score(_model: RandomForestClassifier, matrix: np.ndarray) -> np.ndarray:
        observed.update(shape=matrix.shape, dtype=matrix.dtype, writeable=matrix.flags.writeable)
        return np.asarray([0.625], dtype=np.float64)

    monkeypatch.setattr(private_adapter, "score_frozen_feature_matrix", score)
    adapter = ApprovedPrivateRandomForestAdapter(estimator)
    matrix = np.zeros((1, FEATURE_COUNT), dtype=np.float32)
    matrix.setflags(write=False)
    assert adapter.score_model_input(matrix) == 0.625
    assert observed == {
        "shape": (1, FEATURE_COUNT),
        "dtype": np.dtype("float32"),
        "writeable": False,
    }


@pytest.mark.parametrize("score", [float("nan"), -0.1, 1.1])
def test_invalid_model_output_is_rejected(monkeypatch: pytest.MonkeyPatch, score: float) -> None:
    estimator = RandomForestClassifier()
    monkeypatch.setattr(
        private_adapter, "model_state_sha256", lambda _model: FROZEN_MODEL_STATE_SHA256
    )
    monkeypatch.setattr(
        private_adapter,
        "score_frozen_feature_matrix",
        lambda _model, _matrix: np.asarray([score], dtype=np.float64),
    )
    adapter = ApprovedPrivateRandomForestAdapter(estimator)
    matrix = np.zeros((1, FEATURE_COUNT), dtype=np.float32)
    matrix.setflags(write=False)
    with pytest.raises(ValueError):
        adapter.score_model_input(matrix)
