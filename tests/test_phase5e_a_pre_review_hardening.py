"""Phase 5E-A internal review-readiness and boundary regression tests."""

from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

import archaeoai.inference_system.single_patch as single_patch
from archaeoai.cli import build_parser
from archaeoai.inference_system import (
    APPROVED_MODEL_ARTIFACT_SHA256,
    approved_private_model_reference,
)
from archaeoai.inference_system.contracts import APPROVED_MODEL_CONFIG_SHA256, ModelIdentifier
from archaeoai.portal.app import create_app
from archaeoai.portal.approved_runtime import ApprovedPrivateRandomForestRuntime
from archaeoai.portal.launch import launch_portal

MUTATION_HEADERS = {"X-ArchaeoAI-Demo": "1"}
FORBIDDEN_PUBLIC_KEYS = {
    "array",
    "bbox",
    "bounds",
    "candidate_location",
    "coordinates",
    "easting",
    "feature_vector",
    "features",
    "file_path",
    "geotiff_path",
    "latitude",
    "longitude",
    "model_path",
    "northing",
    "raster_bounds",
    "terrain_path",
    "transform",
    "url",
}


class _ReviewBoundaryAdapter:
    model_identifier = ModelIdentifier.E001_FROZEN_RANDOM_FOREST
    model_config_sha256 = APPROVED_MODEL_CONFIG_SHA256[model_identifier]
    model_artifact_sha256 = APPROVED_MODEL_ARTIFACT_SHA256

    def score_model_input(self, matrix: np.ndarray) -> float:
        assert matrix.shape == (1, 4096)
        assert matrix.dtype == np.float32
        assert matrix.flags.c_contiguous and not matrix.flags.writeable
        return 0.625


def _walk_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return {str(key).casefold() for key in value} | set().union(
            *(_walk_keys(item) for item in value.values()), set()
        )
    if isinstance(value, list):
        return set().union(*(_walk_keys(item) for item in value), set())
    return set()


def _create_authorized_project(client: TestClient) -> str:
    created = client.post(
        "/api/v1/projects",
        headers=MUTATION_HEADERS,
        json={
            "project_name": "Phase 5E-A synthetic review",
            "organization": "Local review",
            "purpose": "Exercise the internal synthetic-only review boundary.",
            "project_reference": "P5EA-TEST",
            "authorized_data_confirmation": True,
            "retention_policy": "SESSION_ONLY",
            "reviewer_requirement_acknowledgement": True,
        },
    )
    assert created.status_code == 201
    project_id = str(created.json()["id"])
    authorized = client.post(
        f"/api/v1/projects/{project_id}/authorize-demo",
        headers=MUTATION_HEADERS,
        json={
            "authorized_data_confirmation": True,
            "reviewer_requirement_acknowledgement": True,
        },
    )
    assert authorized.status_code == 200
    return project_id


@pytest.mark.parametrize(
    "host",
    ["0.0.0.0", "localhost", "::1", "192.0.2.1", "preview.example"],
)
def test_approved_runtime_rejects_every_noncanonical_bind_before_server(
    monkeypatch: pytest.MonkeyPatch, host: str
) -> None:
    started = False

    def forbidden(*_args: object, **_kwargs: object) -> None:
        nonlocal started
        started = True

    monkeypatch.setattr("uvicorn.run", forbidden)
    assert (
        launch_portal(demo=True, reset=False, port=8000, host=host, approved_model_runtime=True)
        == 2
    )
    assert started is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("terrain", [[1.0]]),
        ("terrain_path", "private.tif"),
        ("geotiff_path", "private.tif"),
        ("coordinates", [0, 0]),
        ("bounds", [0, 0, 1, 1]),
        ("transform", [1, 0, 0, 0, -1, 0]),
        ("array", [[1.0]]),
        ("url", "https://example.invalid/private.tif"),
        ("model_path", "private.pkl"),
    ],
)
def test_approved_request_rejects_real_input_and_model_path_fields(
    tmp_path: Path, field: str, value: object
) -> None:
    runtime = ApprovedPrivateRandomForestRuntime(tmp_path, _ReviewBoundaryAdapter())  # type: ignore[arg-type]
    with TestClient(create_app(tmp_path / "portal.sqlite3", approved_runtime=runtime)) as client:
        project_id = _create_authorized_project(client)
        response = client.post(
            f"/api/v1/projects/{project_id}/run-demo",
            headers=MUTATION_HEADERS,
            json={"scenario": "MOUND_LIKE", "runtime": "APPROVED_PRIVATE_MODEL", field: value},
        )
        assert response.status_code == 422
        assert response.json() == {
            "error": "INVALID_REQUEST",
            "message": "Request did not satisfy the portal contract.",
        }


def test_portal_has_no_upload_or_candidate_location_api(tmp_path: Path) -> None:
    app = create_app(tmp_path / "routes.sqlite3")
    api_paths = {
        route.path.casefold()
        for route in app.routes
        if getattr(route, "path", "").startswith("/api/")
    }
    assert all(
        token not in path
        for path in api_paths
        for token in ("upload", "candidate", "coordinate", "location", "terrain", "raster")
    )
    assert app.openapi_url is None


def test_approved_public_and_sqlite_surfaces_exclude_private_spatial_features(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(single_patch, "verify_approved_model_artifact", lambda *_args: "verified")
    database = tmp_path / "portal.sqlite3"
    runtime = ApprovedPrivateRandomForestRuntime(tmp_path, _ReviewBoundaryAdapter())  # type: ignore[arg-type]
    with TestClient(create_app(database, approved_runtime=runtime)) as client:
        project_id = _create_authorized_project(client)
        run = client.post(
            f"/api/v1/projects/{project_id}/run-demo",
            headers=MUTATION_HEADERS,
            json={"scenario": "MOUND_LIKE", "runtime": "APPROVED_PRIVATE_MODEL"},
        )
        assert run.status_code == 200
        surfaces = [
            client.get("/api/v1/health").json(),
            client.get("/api/v1/session").json(),
            client.get(f"/api/v1/projects/{project_id}").json(),
            client.get(f"/api/v1/projects/{project_id}/jobs").json(),
            client.get(f"/api/v1/projects/{project_id}/results").json(),
            client.get(f"/api/v1/projects/{project_id}/evidence").json(),
            client.get(f"/api/v1/projects/{project_id}/audit").json(),
            client.post(f"/api/v1/projects/{project_id}/report", headers=MUTATION_HEADERS).json(),
        ]
    assert not (set().union(*(_walk_keys(item) for item in surfaces)) & FORBIDDEN_PUBLIC_KEYS)
    serialized = json.dumps(surfaces).casefold()
    assert "data/private" not in serialized and str(tmp_path).casefold() not in serialized

    with sqlite3.connect(database) as db:
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        columns = {
            str(row[1]).casefold()
            for table in tables
            for row in db.execute(f'PRAGMA table_info("{table}")')
        }
    assert not (columns & FORBIDDEN_PUBLIC_KEYS)


def test_project_delete_is_logical_cascade_not_physical_erasure(tmp_path: Path) -> None:
    database = tmp_path / "delete.sqlite3"
    app = create_app(database)
    repository = app.state.repository
    with TestClient(app) as client:
        project_id = _create_authorized_project(client)
        client.post(
            f"/api/v1/projects/{project_id}/run-demo",
            headers=MUTATION_HEADERS,
            json={"scenario": "PLANAR", "runtime": "SYNTHETIC_DEMO"},
        )
        result = client.get(f"/api/v1/projects/{project_id}/results").json()[0]
        client.post(
            f"/api/v1/results/{result['id']}/review",
            headers=MUTATION_HEADERS,
            json={
                "category": "ARTEFACT_OR_UNCERTAIN",
                "rationale": "Synthetic workflow deletion test.",
                "confidence": "LOW",
                "evidence_level": "HUMAN_VETTED_OBSERVATION",
            },
        )
        client.post(f"/api/v1/projects/{project_id}/report", headers=MUTATION_HEADERS)
        before = repository.counts()
        assert all(before[name] > 0 for name in before)
        assert (
            client.delete(f"/api/v1/projects/{project_id}", headers=MUTATION_HEADERS).status_code
            == 204
        )
    assert repository.counts() == {name: 0 for name in before}
    assert database.exists()  # Logical row deletion is not a physical-media erasure claim.


def test_private_model_reference_is_fixed_ignored_and_not_cli_controlled() -> None:
    root = Path(__file__).resolve().parents[1]
    reference = approved_private_model_reference(root)
    expected = root / "data/private/e001/inference/e001_phase2f_random_forest.pkl"
    assert reference.path == expected.resolve()
    parser = build_parser()
    destinations = {action.dest for action in parser._actions}
    destinations |= {
        action.dest
        for subparser in parser._subparsers._group_actions  # type: ignore[attr-defined]
        for choice in subparser.choices.values()
        for action in choice._actions
    }
    assert "model_path" not in destinations and "artifact_path" not in destinations
    ignored = subprocess.run(
        ["git", "check-ignore", str(expected)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    tracked = subprocess.run(
        ["git", "ls-files", "--", str(expected.relative_to(root))],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0 and tracked.stdout.strip() == ""


def test_phase5e_review_state_and_rq1_status_remain_unadvanced() -> None:
    root = Path(__file__).resolve().parents[1]
    review_text = "\n".join(
        (root / path).read_text(encoding="utf-8")
        for path in (
            "docs/CURRENT_STATUS.md",
            "docs/review/README.md",
            "docs/review/PHASE_5E_EXTERNAL_REVIEW_CHECKLIST.md",
            "docs/review/PHASE_5E_REVIEW_PACKAGE.md",
        )
    )
    assert "RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW" in review_text
    assert "Phase 5E" in review_text and "NOT COMPLETED" in review_text
    assert "Phase 5F" in review_text and "NOT AUTHORIZED" in review_text
    assert "READY FOR EXTERNAL REVIEW" in review_text
    assert "independent review status: completed" not in review_text.casefold()


def test_portal_language_has_no_prohibited_archaeological_claims() -> None:
    root = Path(__file__).resolve().parents[1]
    portal_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (root / "src/archaeoai/portal").rglob("*")
        if path.is_file() and path.suffix in {".py", ".html", ".js"}
    ).casefold()
    for prohibited in (
        "probability of a site",
        "discovery probability",
        "confirmed archaeology",
        "safe to build",
        "safe to develop",
    ):
        assert prohibited not in portal_text
