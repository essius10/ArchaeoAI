"""Phase 6C functional, safety, privacy, and evidence-boundary tests."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from archaeoai.inference import FEATURE_COUNT, REPRESENTATION_CHANNELS
from archaeoai.inference_system import TerrainInputMetadata, TerrainPatch, transform_single_patch
from archaeoai.portal.app import create_app
from archaeoai.portal.demo_runtime import SyntheticDemoRuntime
from archaeoai.portal.model_runtime import (
    ApprovedModelRuntimeNotAuthorizedError,
    DisabledApprovedModelRuntime,
)
from archaeoai.portal.repository import PortalRepository
from archaeoai.portal.schemas import (
    ApprovedRuntimeRequest,
    DemoRunRequest,
    EvidenceLevel,
    ProjectCreate,
    ReviewRequest,
    SyntheticScenario,
)

MUTATION_HEADERS = {"X-ArchaeoAI-Demo": "1"}
FORBIDDEN_RESPONSE_KEYS = {
    "coordinates",
    "latitude",
    "longitude",
    "bounds",
    "transform",
    "feature_vector",
    "features",
    "raster",
    "raster_values",
    "model_path",
    "file_path",
}


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    database = tmp_path / "portal.sqlite3"
    with TestClient(create_app(database)) as test_client:
        yield test_client


def project_payload(**updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "project_name": "Synthetic Terrain Review",
        "organization": "Demonstration Organization",
        "purpose": "Test the bounded mathematical terrain review workflow.",
        "project_reference": "SYNTH-001",
        "authorized_data_confirmation": True,
        "retention_policy": "SESSION_ONLY",
        "reviewer_requirement_acknowledgement": True,
    }
    payload.update(updates)
    return payload


def create_project(client: TestClient, **updates: object) -> dict[str, object]:
    response = client.post(
        "/api/v1/projects", json=project_payload(**updates), headers=MUTATION_HEADERS
    )
    assert response.status_code == 201
    return response.json()


def authorize_and_run(client: TestClient, project_id: str) -> list[dict[str, object]]:
    acknowledgement = {
        "authorized_data_confirmation": True,
        "reviewer_requirement_acknowledgement": True,
    }
    response = client.post(
        f"/api/v1/projects/{project_id}/authorize-demo",
        json=acknowledgement,
        headers=MUTATION_HEADERS,
    )
    assert response.status_code == 200
    response = client.post(
        f"/api/v1/projects/{project_id}/run-demo",
        json={"scenario": "MOUND_LIKE", "runtime": "SYNTHETIC_DEMO"},
        headers=MUTATION_HEADERS,
    )
    assert response.status_code == 200
    return client.get(f"/api/v1/projects/{project_id}/results").json()


def walk_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        keys.update(str(key).casefold() for key in value)
        for item in value.values():
            keys.update(walk_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.update(walk_keys(item))
    return keys


def test_health_and_session_are_explicitly_local_demo(client: TestClient) -> None:
    health = client.get("/api/v1/health")
    assert health.status_code == 200
    assert health.json() == {
        "status": "READY",
        "portal": "LOCAL_DEMO",
        "demo_runtime": "AVAILABLE",
        "approved_model_runtime": "DISABLED_NOT_AUTHORIZED",
        "storage": "LOCAL_PRIVATE_SQLITE",
    }
    assert client.get("/api/v1/session").json()["authenticated"] is False


def test_security_headers_and_no_openapi(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert client.get("/openapi.json").headers["content-type"].startswith("text/html")


def test_project_lifecycle_create_read_delete(client: TestClient) -> None:
    project = create_project(client)
    assert project["id"].startswith("prj_")
    assert client.get(f"/api/v1/projects/{project['id']}").json()["status"] == "DRAFT"
    deleted = client.delete(f"/api/v1/projects/{project['id']}", headers=MUTATION_HEADERS)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/projects/{project['id']}").status_code == 404


def test_state_change_requires_demo_header(client: TestClient) -> None:
    response = client.post("/api/v1/projects", json=project_payload())
    assert response.status_code == 403
    assert response.json()["error"] == "DEMO_REQUEST_HEADER_REQUIRED"


def test_remote_origin_is_rejected(client: TestClient) -> None:
    headers = {**MUTATION_HEADERS, "Origin": "https://attacker.example"}
    response = client.post("/api/v1/projects", json=project_payload(), headers=headers)
    assert response.status_code == 403
    assert response.json()["error"] == "ORIGIN_NOT_ALLOWED"


def test_processing_requires_authorization(client: TestClient) -> None:
    project = create_project(client)
    response = client.post(
        f"/api/v1/projects/{project['id']}/run-demo",
        json={"scenario": "PLANAR", "runtime": "SYNTHETIC_DEMO"},
        headers=MUTATION_HEADERS,
    )
    assert response.status_code == 409
    assert response.json()["error"] == "DEMO_AUTHORIZATION_REQUIRED"


def test_synthetic_job_completes_without_model_execution(client: TestClient) -> None:
    project = create_project(client)
    results = authorize_and_run(client, str(project["id"]))
    assert len(results) == 6
    assert {item["runtime"] for item in results} == {"SYNTHETIC_DEMO"}
    assert {item["model_execution"] for item in results} == {"NOT_PERFORMED"}
    assert {item["evidence_level"] for item in results} == {"AI_HYPOTHESIS"}


@pytest.mark.parametrize("scenario", list(SyntheticScenario))
def test_synthetic_runtime_is_deterministic(scenario: SyntheticScenario) -> None:
    runtime = SyntheticDemoRuntime()
    first = runtime.screen(scenario)
    second = runtime.screen(scenario)
    assert [item.score for item in first] == [item.score for item in second]
    assert all(0.0 <= item.score <= 1.0 for item in first)


def test_synthetic_surface_uses_canonical_phase5_feature_contract() -> None:
    elevation = SyntheticDemoRuntime.surface(SyntheticScenario.MOUND_LIKE, 2)
    prepared = transform_single_patch(
        TerrainPatch(
            elevation=elevation,
            mask=np.zeros_like(elevation, dtype=bool),
            metadata=TerrainInputMetadata(
                crs="EPSG:27700",
                width=128,
                height=128,
                resolution_m=(1.0, 1.0),
                band_count=1,
                nodata_fraction=0.0,
            ),
        )
    )
    assert elevation.shape == (128, 128)
    assert prepared.feature_vector.shape == (FEATURE_COUNT,)
    assert prepared.feature_vector.dtype == np.float32
    assert prepared.representation_names == REPRESENTATION_CHANNELS


def test_approved_model_runtime_fails_before_artifact_operations(client: TestClient) -> None:
    response = client.post(
        "/api/v1/runtime/approved/check",
        json={"runtime": "APPROVED_MODEL", "model_identifier": "approved-reference"},
        headers=MUTATION_HEADERS,
    )
    assert response.status_code == 403
    assert response.json()["error"] == "APPROVED_MODEL_RUNTIME_NOT_AUTHORIZED"
    with pytest.raises(ApprovedModelRuntimeNotAuthorizedError):
        DisabledApprovedModelRuntime().validate()


@pytest.mark.parametrize(
    "evidence_level",
    [
        EvidenceLevel.AI_OUTPUT,
        EvidenceLevel.AI_HYPOTHESIS,
        EvidenceLevel.ARCHAEOLOGIST_VALIDATED_INTERPRETATION,
        EvidenceLevel.CONFIRMED_ARCHAEOLOGICAL_EVIDENCE,
    ],
)
def test_review_schema_rejects_every_level_except_human_observation(
    evidence_level: EvidenceLevel,
) -> None:
    with pytest.raises(ValidationError):
        ReviewRequest(
            category="ARTEFACT_OR_UNCERTAIN",
            rationale="A bounded synthetic observation.",
            confidence="LOW",
            evidence_level=evidence_level,
        )


def test_human_review_creates_separate_attributable_evidence(client: TestClient) -> None:
    project = create_project(client)
    result = authorize_and_run(client, str(project["id"]))[0]
    response = client.post(
        f"/api/v1/results/{result['id']}/review",
        json={
            "category": "MORPHOLOGY_WARRANTS_FURTHER_ASSESSMENT",
            "rationale": "The mathematical morphology warrants a second human look.",
            "confidence": "MODERATE",
            "evidence_level": "HUMAN_VETTED_OBSERVATION",
        },
        headers=MUTATION_HEADERS,
    )
    assert response.status_code == 200
    evidence = client.get(f"/api/v1/projects/{project['id']}/evidence").json()
    assert {item["actor_type"] for item in evidence} == {"MACHINE", "HUMAN"}
    human = [item for item in evidence if item["actor_type"] == "HUMAN"]
    assert human[0]["actor"] == "Local demo reviewer"
    assert human[0]["evidence_level"] == "HUMAN_VETTED_OBSERVATION"


def test_audit_contains_required_workflow_events(client: TestClient) -> None:
    project = create_project(client)
    authorize_and_run(client, str(project["id"]))
    events = client.get(f"/api/v1/projects/{project['id']}/audit").json()
    event_types = {item["event_type"] for item in events}
    assert {
        "PROJECT_CREATED",
        "DEMO_AUTHORIZATION_RECORDED",
        "SYNTHETIC_DATASET_SELECTED",
        "PROCESSING_STARTED",
        "PROCESSING_COMPLETED",
        "RESULTS_CREATED",
    } <= event_types


def test_report_is_limitations_first_and_coordinate_safe(client: TestClient) -> None:
    project = create_project(client)
    authorize_and_run(client, str(project["id"]))
    response = client.post(f"/api/v1/projects/{project['id']}/report", headers=MUTATION_HEADERS)
    assert response.status_code == 200
    report = response.json()
    assert report["screening_summary"]["model_execution"] == "NOT_PERFORMED"
    assert any(
        "not a professional archaeological assessment" in item for item in report["limitations"]
    )
    assert not (walk_keys(report) & FORBIDDEN_RESPONSE_KEYS)


def test_retention_update_is_controlled_enum(client: TestClient) -> None:
    project = create_project(client)
    response = client.patch(
        f"/api/v1/projects/{project['id']}/retention",
        json={"retention_policy": "SEVEN_DAYS"},
        headers=MUTATION_HEADERS,
    )
    assert response.json()["retention_policy"] == "SEVEN_DAYS"
    rejected = client.patch(
        f"/api/v1/projects/{project['id']}/retention",
        json={"retention_policy": "FOREVER"},
        headers=MUTATION_HEADERS,
    )
    assert rejected.status_code == 422


def test_project_deletion_cascades_all_associated_records(tmp_path: Path) -> None:
    database = tmp_path / "cascade.sqlite3"
    app = create_app(database)
    with TestClient(app) as client:
        project = create_project(client)
        result = authorize_and_run(client, str(project["id"]))[0]
        client.post(
            f"/api/v1/results/{result['id']}/review",
            json={
                "category": "ARTEFACT_OR_UNCERTAIN",
                "rationale": "Synthetic morphology remains uncertain.",
                "confidence": "LOW",
                "evidence_level": "HUMAN_VETTED_OBSERVATION",
            },
            headers=MUTATION_HEADERS,
        )
        client.post(f"/api/v1/projects/{project['id']}/report", headers=MUTATION_HEADERS)
        client.delete(f"/api/v1/projects/{project['id']}", headers=MUTATION_HEADERS)
    counts = PortalRepository(database).counts()
    assert counts == {name: 0 for name in counts}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("project_name", "<script>alert(1)</script>"),
        ("project_name", "../../model.pkl"),
        ("organization", "file:///private/model.pkl"),
        ("purpose", "https://attacker.example/collect"),
        ("purpose", r"C:\private\model.pkl"),
        ("purpose", "/etc/passwd"),
        ("project_name", "x" * 81),
    ],
)
def test_dangerous_or_oversized_project_metadata_is_rejected(
    client: TestClient, field: str, value: str
) -> None:
    response = client.post(
        "/api/v1/projects",
        json=project_payload(**{field: value}),
        headers=MUTATION_HEADERS,
    )
    assert response.status_code == 422
    assert response.json() == {
        "error": "INVALID_REQUEST",
        "message": "Request did not satisfy the portal contract.",
    }


@pytest.mark.parametrize(
    "unexpected",
    [
        {"coordinates": [1, 2]},
        {"metadata": {"bounds": [0, 1, 2, 3]}},
        {"model_path": "../../model.pkl"},
        {"runtime": "APPROVED_MODEL"},
    ],
)
def test_unexpected_dangerous_metadata_fails_closed(
    client: TestClient, unexpected: dict[str, object]
) -> None:
    payload = project_payload()
    payload.update(unexpected)
    response = client.post("/api/v1/projects", json=payload, headers=MUTATION_HEADERS)
    assert response.status_code == 422


@pytest.mark.parametrize("identifier", ["not-an-id", "prj_ABC", "prj_00000000000x.exe"])
def test_malformed_project_ids_fail_with_controlled_response(
    client: TestClient, identifier: str
) -> None:
    response = client.get(f"/api/v1/projects/{identifier}")
    assert response.status_code == 404
    assert "Traceback" not in response.text


def test_path_like_routes_cannot_read_arbitrary_files(client: TestClient) -> None:
    for route in ("/../../model.pkl", "/file:///private/model.pkl", "/C:/private/model.pkl"):
        response = client.get(route)
        assert response.status_code in {200, 404}
        assert "pickle" not in response.text.casefold()
        assert "traceback" not in response.text.casefold()


def test_api_payloads_have_no_private_spatial_or_feature_fields(client: TestClient) -> None:
    project = create_project(client)
    authorize_and_run(client, str(project["id"]))
    payloads = [
        client.get("/api/v1/overview").json(),
        client.get("/api/v1/projects").json(),
        client.get(f"/api/v1/projects/{project['id']}/results").json(),
        client.get(f"/api/v1/projects/{project['id']}/evidence").json(),
        client.get(f"/api/v1/projects/{project['id']}/audit").json(),
    ]
    assert not (
        set().union(*(walk_keys(payload) for payload in payloads)) & FORBIDDEN_RESPONSE_KEYS
    )
    serialized = json.dumps(payloads).casefold()
    assert "c:\\" not in serialized
    assert "/users/" not in serialized


def test_database_schema_has_no_spatial_path_raster_or_feature_columns(tmp_path: Path) -> None:
    database = tmp_path / "schema.sqlite3"
    PortalRepository(database)
    with sqlite3.connect(database) as connection:
        tables = [
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        ]
        columns = {
            row[1].casefold()
            for table in tables
            for row in connection.execute(f"PRAGMA table_info({table})")
        }
    assert not (columns & FORBIDDEN_RESPONSE_KEYS)


def test_approved_runtime_schema_rejects_paths_urls_and_unknown_fields() -> None:
    for value in ("../../model.pkl", "file:///model.pkl", "https://example.test/model"):
        with pytest.raises(ValidationError):
            ApprovedRuntimeRequest(runtime="APPROVED_MODEL", model_identifier=value)
    with pytest.raises(ValidationError):
        ApprovedRuntimeRequest(
            runtime="APPROVED_MODEL", model_identifier="safe-id", model_path="private.pkl"
        )


def test_arbitrary_runtime_name_is_rejected() -> None:
    with pytest.raises(ValidationError):
        DemoRunRequest(scenario="PLANAR", runtime="APPROVED_MODEL")


def test_project_acknowledgements_are_mandatory() -> None:
    for field in ("authorized_data_confirmation", "reviewer_requirement_acknowledgement"):
        values = project_payload(**{field: False})
        with pytest.raises(ValidationError):
            ProjectCreate(**values)


def test_static_portal_contains_required_navigation_and_safe_language(client: TestClient) -> None:
    html = client.get("/").text
    javascript = client.get("/static/portal.js").text
    stylesheet = client.get("/static/portal.css").text
    for label in ("Overview", "Projects", "Review Queue", "Reports", "Audit", "Settings"):
        assert label in html
    assert "DEMO MODE — SYNTHETIC DATA" in html
    assert "Import authorized terrain" in html
    assert "Live terrain ingestion is not enabled" in html
    assert "HUMAN_VETTED_OBSERVATION" in html
    assert "window.print()" in javascript
    assert "escapeHtml" in javascript
    assert "@media print" in stylesheet
    assert "@media (max-width:" in stylesheet


def test_portal_source_has_no_model_deserialization_or_upload_endpoint() -> None:
    root = Path(__file__).parents[1] / "src" / "archaeoai" / "portal"
    python_source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    lowered = python_source.casefold()
    assert "pickle.load" not in lowered
    assert "joblib.load" not in lowered
    assert "torch.load" not in lowered
    assert "uploadfile" not in lowered
    assert 'post("/public/infer"' not in lowered


def test_demo_database_path_is_ignored_by_git() -> None:
    gitignore = (Path(__file__).parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert "data/private/" in gitignore
