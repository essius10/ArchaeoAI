"""Phase 6D portal authorization, execution, and disclosure-boundary tests."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

import archaeoai.inference_system.single_patch as single_patch
from archaeoai.cli import build_parser
from archaeoai.inference import FEATURE_COUNT
from archaeoai.inference_system import APPROVED_MODEL_ARTIFACT_SHA256, ApprovedPrivateModelLoadError
from archaeoai.inference_system.contracts import (
    APPROVED_MODEL_CONFIG_SHA256,
    ModelIdentifier,
)
from archaeoai.portal.app import create_app
from archaeoai.portal.approved_runtime import ApprovedPrivateRandomForestRuntime
from archaeoai.portal.demo_runtime import SyntheticDemoRuntime
from archaeoai.portal.launch import launch_portal

HEADERS = {"X-ArchaeoAI-Demo": "1"}
FORBIDDEN = {
    "coordinates",
    "bounds",
    "transform",
    "features",
    "feature_vector",
    "model_path",
    "file_path",
    "artifact_bytes",
}


class RecordingAdapter:
    model_identifier = ModelIdentifier.E001_FROZEN_RANDOM_FOREST
    model_config_sha256 = APPROVED_MODEL_CONFIG_SHA256[model_identifier]
    model_artifact_sha256 = APPROVED_MODEL_ARTIFACT_SHA256

    def __init__(self, score: float = 0.72):
        self.score = score
        self.calls: list[tuple[tuple[int, ...], np.dtype, bool]] = []

    def score_model_input(self, feature_matrix: np.ndarray) -> float:
        self.calls.append(
            (feature_matrix.shape, feature_matrix.dtype, feature_matrix.flags.writeable)
        )
        return self.score


def _walk_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return {str(key).casefold() for key in value} | set().union(
            *(_walk_keys(item) for item in value.values()), set()
        )
    if isinstance(value, list):
        return set().union(*(_walk_keys(item) for item in value), set())
    return set()


def _approved_client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, score: float = 0.72
) -> tuple[TestClient, RecordingAdapter]:
    monkeypatch.setattr(single_patch, "verify_approved_model_artifact", lambda *_args: "verified")
    adapter = RecordingAdapter(score)
    runtime = ApprovedPrivateRandomForestRuntime(tmp_path, adapter)  # type: ignore[arg-type]
    return TestClient(create_app(tmp_path / "portal.sqlite3", approved_runtime=runtime)), adapter


def _create_authorized_project(client: TestClient) -> str:
    created = client.post(
        "/api/v1/projects",
        headers=HEADERS,
        json={
            "project_name": "Approved runtime synthetic check",
            "organization": "Local test",
            "purpose": "Verify the bounded approved runtime over mathematical terrain.",
            "project_reference": "P6D-TEST",
            "authorized_data_confirmation": True,
            "retention_policy": "SESSION_ONLY",
            "reviewer_requirement_acknowledgement": True,
        },
    )
    project_id = created.json()["id"]
    authorized = client.post(
        f"/api/v1/projects/{project_id}/authorize-demo",
        headers=HEADERS,
        json={
            "authorized_data_confirmation": True,
            "reviewer_requirement_acknowledgement": True,
        },
    )
    assert authorized.status_code == 200
    return str(project_id)


def test_approved_cli_flag_is_explicit_and_default_is_disabled() -> None:
    default = build_parser().parse_args(["portal", "--demo"])
    approved = build_parser().parse_args(["portal", "--demo", "--approved-model-runtime"])
    assert default.approved_model_runtime is False
    assert approved.approved_model_runtime is True


def test_approved_runtime_rejects_public_bind_before_server(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    called = False

    def forbidden(*_args: object, **_kwargs: object) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("uvicorn.run", forbidden)
    assert (
        launch_portal(
            demo=True,
            reset=False,
            port=8000,
            host="0.0.0.0",
            approved_model_runtime=True,
        )
        == 2
    )
    assert called is False
    assert "restricted to 127.0.0.1" in capsys.readouterr().out


def test_missing_approved_artifact_stops_launcher_without_fallback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    server_started = False

    def unavailable(_root: Path) -> object:
        raise ApprovedPrivateModelLoadError(ApprovedPrivateModelLoadError.code)

    def forbidden_server(*_args: object, **_kwargs: object) -> None:
        nonlocal server_started
        server_started = True

    monkeypatch.setattr(
        "archaeoai.inference_system.load_approved_private_random_forest", unavailable
    )
    monkeypatch.setattr("archaeoai.portal.launch.default_database_path", lambda: tmp_path / "db")
    monkeypatch.setattr("uvicorn.run", forbidden_server)
    assert (
        launch_portal(
            demo=True,
            reset=False,
            port=8000,
            approved_model_runtime=True,
        )
        == 2
    )
    assert server_started is False
    output = capsys.readouterr().out
    assert "unavailable or failed verification" in output
    assert str(tmp_path) not in output


def test_verified_approved_runtime_reaches_local_server_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, object] = {}
    adapter = RecordingAdapter()
    monkeypatch.setattr(
        "archaeoai.inference_system.load_approved_private_random_forest",
        lambda _root: adapter,
    )
    monkeypatch.setattr("archaeoai.portal.launch.find_project_root", lambda: tmp_path)
    monkeypatch.setattr("archaeoai.portal.launch.default_database_path", lambda: tmp_path / "db")
    monkeypatch.setattr("uvicorn.run", lambda _app, **kwargs: captured.update(kwargs))
    assert (
        launch_portal(
            demo=True,
            reset=False,
            port=8000,
            approved_model_runtime=True,
        )
        == 0
    )
    assert captured["host"] == "127.0.0.1"
    assert captured["access_log"] is False
    assert captured["log_level"] == "warning"
    output = capsys.readouterr().out
    assert "REAL FROZEN MODEL · SYNTHETIC TERRAIN · LOCAL PRIVATE" in output
    assert "not archaeological probability" in output


def test_api_request_cannot_authorize_disabled_runtime(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "disabled.sqlite3")) as client:
        project_id = _create_authorized_project(client)
        response = client.post(
            f"/api/v1/projects/{project_id}/run-demo",
            headers=HEADERS,
            json={"scenario": "PLANAR", "runtime": "APPROVED_PRIVATE_MODEL"},
        )
        assert response.status_code == 403
        assert response.json()["error"] == "APPROVED_MODEL_RUNTIME_NOT_AUTHORIZED"
        assert client.get(f"/api/v1/projects/{project_id}/jobs").json() == []


def test_approved_status_is_safe_and_server_injected(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _adapter = _approved_client(monkeypatch, tmp_path)
    with client:
        status = client.get("/api/v1/health").json()["runtime_status"]
        assert status == {
            "runtime_mode": "APPROVED_PRIVATE_MODEL",
            "approved_runtime_enabled": True,
            "artifact_verified": True,
            "model_execution_available": True,
            "model_identifier": "e001-frozen-random-forest",
            "model_config_sha256": (
                "20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"
            ),
            "model_state_sha256": (
                "e3b0c072f437e889f09a2a2cf5a37f19b2f483eb5188e102b132a89ee76d1939"
            ),
            "input_mode": "SYNTHETIC_ONLY",
        }
        serialized = json.dumps(status).casefold()
        assert "c:\\" not in serialized
        assert "/users/" not in serialized
        assert "data/private" not in serialized


def test_approved_runtime_uses_canonical_features_and_real_adapter_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, adapter = _approved_client(monkeypatch, tmp_path)
    monkeypatch.setattr(
        SyntheticDemoRuntime,
        "_demonstration_score",
        lambda *_args: (_ for _ in ()).throw(AssertionError("fallback scorer called")),
    )
    with client:
        project_id = _create_authorized_project(client)
        response = client.post(
            f"/api/v1/projects/{project_id}/run-demo",
            headers=HEADERS,
            json={"scenario": "MOUND_LIKE", "runtime": "APPROVED_PRIVATE_MODEL"},
        )
        assert response.status_code == 200
        results = client.get(f"/api/v1/projects/{project_id}/results").json()
        assert len(adapter.calls) == len(results) == 6
        assert set(adapter.calls) == {((1, FEATURE_COUNT), np.dtype("float32"), False)}
        assert {item["evidence_level"] for item in results} == {"AI_OUTPUT"}
        assert {item["runtime"] for item in results} == {"APPROVED_PRIVATE_RANDOM_FOREST"}
        assert {item["model_execution"] for item in results} == {"PERFORMED_APPROVED_PRIVATE_MODEL"}
        assert all(item["score"] == pytest.approx(0.72) for item in results)
        assert not (_walk_keys(results) & FORBIDDEN)


def test_approved_report_preserves_safe_model_provenance(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _adapter = _approved_client(monkeypatch, tmp_path)
    with client:
        project_id = _create_authorized_project(client)
        client.post(
            f"/api/v1/projects/{project_id}/run-demo",
            headers=HEADERS,
            json={"scenario": "MIXED_MATHEMATICAL", "runtime": "APPROVED_PRIVATE_MODEL"},
        )
        report = client.post(f"/api/v1/projects/{project_id}/report", headers=HEADERS).json()
        assert report["screening_summary"] == {
            "synthetic_hypotheses": 6,
            "reviewed": 0,
            "model_execution": "PERFORMED_APPROVED_PRIVATE_MODEL",
            "runtime": "APPROVED_PRIVATE_RANDOM_FOREST",
            "automatic_evidence_level": "AI_OUTPUT",
        }
        assert any("does not establish" in item for item in report["limitations"])
        assert not (_walk_keys(report) & FORBIDDEN)


@pytest.mark.parametrize("score", [float("nan"), -0.01, 1.01])
def test_invalid_approved_score_returns_only_safe_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, score: float
) -> None:
    client, _adapter = _approved_client(monkeypatch, tmp_path, score=score)
    with client:
        project_id = _create_authorized_project(client)
        response = client.post(
            f"/api/v1/projects/{project_id}/run-demo",
            headers=HEADERS,
            json={"scenario": "PLANAR", "runtime": "APPROVED_PRIVATE_MODEL"},
        )
        assert response.status_code == 503
        assert response.json() == {
            "error": "APPROVED_MODEL_RUNTIME_EXECUTION_FAILED",
            "message": "Approved runtime failed safely.",
        }


@pytest.mark.parametrize(
    "runtime",
    ["../../model.pkl", "APPROVED_PRIVATE_MODEL/../../x", "RANDOM_FOREST", "approved"],
)
def test_runtime_injection_and_traversal_are_rejected(tmp_path: Path, runtime: str) -> None:
    with TestClient(create_app(tmp_path / "strict.sqlite3")) as client:
        project_id = _create_authorized_project(client)
        response = client.post(
            f"/api/v1/projects/{project_id}/run-demo",
            headers=HEADERS,
            json={"scenario": "PLANAR", "runtime": runtime},
        )
        assert response.status_code == 422
        assert response.json()["error"] == "INVALID_REQUEST"


def test_http_contract_never_accepts_model_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    client, _adapter = _approved_client(monkeypatch, tmp_path)
    with client:
        project_id = _create_authorized_project(client)
        response = client.post(
            f"/api/v1/projects/{project_id}/run-demo",
            headers=HEADERS,
            json={
                "scenario": "PLANAR",
                "runtime": "APPROVED_PRIVATE_MODEL",
                "model_path": "../../private.pkl",
            },
        )
        assert response.status_code == 422


def test_static_routes_do_not_expose_private_artifacts(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "routes.sqlite3")) as client:
        for route in (
            "/static/model.pkl",
            "/data/private/e001/inference/e001_phase2f_random_forest.pkl",
            "/api/v1/model/download",
        ):
            response = client.get(route)
            assert APPROVED_MODEL_ARTIFACT_SHA256 not in response.text
            assert not response.content.startswith(b"\x80\x05")


def test_no_cors_wildcard_or_network_dependency(tmp_path: Path) -> None:
    with TestClient(create_app(tmp_path / "network.sqlite3")) as client:
        response = client.get("/api/v1/health")
        assert response.headers.get("access-control-allow-origin") != "*"
        assert "http" not in json.dumps(response.json()).casefold()
