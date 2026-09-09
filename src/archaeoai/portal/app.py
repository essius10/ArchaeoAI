"""FastAPI application for the local synthetic professional portal."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from archaeoai.portal.model_runtime import (
    ApprovedModelRuntimeExecutionError,
    ApprovedModelRuntimeNotAuthorizedError,
    ScreeningRuntime,
)
from archaeoai.portal.repository import (
    DEMO_ORGANIZATION_ID,
    DEMO_USER_ID,
    DEMO_USER_NAME,
    DEMO_USER_ROLE,
    PortalRepository,
)
from archaeoai.portal.schemas import (
    PROJECT_ID_PATTERN,
    RESULT_ID_PATTERN,
    ApprovedRuntimeRequest,
    DemoAuthorization,
    DemoRunRequest,
    ProjectCreate,
    RetentionUpdate,
    ReviewRequest,
)
from archaeoai.portal.workflow import PortalWorkflow

MAX_JSON_REQUEST_BYTES = 64 * 1024


class PortalApiError(RuntimeError):
    def __init__(self, code: str, status_code: int = 400):
        self.code = code
        self.status_code = status_code
        super().__init__(code)


def _default_database_path() -> Path:
    return Path.cwd() / "data" / "private" / "portal" / "archaeoai_portal.sqlite3"


def _safe_id(value: str, pattern, code: str) -> str:  # type: ignore[no-untyped-def]
    if pattern.fullmatch(value) is None:
        raise PortalApiError(code, 404)
    return value


def _safe_project(repository: PortalRepository, project_id: str) -> dict:
    try:
        return repository.get_project(_safe_id(project_id, PROJECT_ID_PATTERN, "PROJECT_NOT_FOUND"))
    except KeyError as exc:
        raise PortalApiError("PROJECT_NOT_FOUND", 404) from exc


def create_app(
    database_path: Path | None = None,
    *,
    approved_runtime: ScreeningRuntime | None = None,
) -> FastAPI:
    """Create an offline portal bound to one local demo organization."""
    repository = PortalRepository(database_path or _default_database_path())
    workflow = PortalWorkflow(repository, approved_runtime=approved_runtime)
    static_root = Path(__file__).with_name("static")
    app = FastAPI(
        title="ArchaeoAI professional portal demonstration",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.repository = repository
    app.state.workflow = workflow
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "testserver"],
    )

    @app.middleware("http")
    async def request_boundary(request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.method in {"POST", "PATCH", "DELETE"} and request.url.path.startswith("/api/"):
            if request.headers.get("x-archaeoai-demo") != "1":
                return JSONResponse(
                    {"error": "DEMO_REQUEST_HEADER_REQUIRED", "message": "Request rejected."},
                    status_code=403,
                )
            origin = request.headers.get("origin")
            if origin:
                parsed = urlsplit(origin)
                if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
                    return JSONResponse(
                        {"error": "ORIGIN_NOT_ALLOWED", "message": "Request rejected."},
                        status_code=403,
                    )
            content_length = request.headers.get("content-length")
            if content_length:
                try:
                    too_large = int(content_length) > MAX_JSON_REQUEST_BYTES
                except ValueError:
                    too_large = True
                if too_large:
                    return JSONResponse(
                        {"error": "REQUEST_TOO_LARGE", "message": "Request rejected."},
                        status_code=413,
                    )
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.exception_handler(RequestValidationError)
    async def validation_error(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            {"error": "INVALID_REQUEST", "message": "Request did not satisfy the portal contract."},
            status_code=422,
        )

    @app.exception_handler(PortalApiError)
    async def portal_error(_request: Request, exc: PortalApiError) -> JSONResponse:
        return JSONResponse(
            {
                "error": exc.code,
                "message": "The requested portal operation could not be completed.",
            },
            status_code=exc.status_code,
        )

    @app.exception_handler(ApprovedModelRuntimeNotAuthorizedError)
    async def approved_not_authorized(
        _request: Request, exc: ApprovedModelRuntimeNotAuthorizedError
    ) -> JSONResponse:
        return JSONResponse(
            {"error": exc.code, "message": "Approved runtime is not server-authorized."},
            status_code=403,
        )

    @app.exception_handler(ApprovedModelRuntimeExecutionError)
    async def approved_execution_failed(
        _request: Request, exc: ApprovedModelRuntimeExecutionError
    ) -> JSONResponse:
        return JSONResponse(
            {"error": exc.code, "message": "Approved runtime failed safely."},
            status_code=503,
        )

    @app.exception_handler(ValueError)
    async def state_error(_request: Request, exc: ValueError) -> JSONResponse:
        allowed = {
            "DEMO_AUTHORIZATION_REQUIRED",
            "INVALID_PROJECT_STATE",
            "INVALID_REVIEW_STATE",
            "EVIDENCE_PROMOTION_NOT_AUTHORIZED",
        }
        code = str(exc) if str(exc) in allowed else "INVALID_OPERATION"
        return JSONResponse(
            {"error": code, "message": "The requested state transition is not permitted."},
            status_code=409,
        )

    @app.get("/api/v1/health")
    def health() -> dict[str, object]:
        runtime_status = workflow.runtime_status()
        return {
            "status": "READY",
            "portal": "LOCAL_DEMO",
            "demo_runtime": "AVAILABLE",
            "approved_model_runtime": (
                "VERIFIED_LOCAL_SYNTHETIC_ONLY"
                if runtime_status["model_execution_available"]
                else "DISABLED_NOT_AUTHORIZED"
            ),
            "storage": "LOCAL_PRIVATE_SQLITE",
            "runtime_status": runtime_status,
        }

    @app.get("/api/v1/session")
    def session() -> dict[str, object]:
        runtime_status = workflow.runtime_status()
        return {
            "session_type": "LOCAL_DEMONSTRATION_ONLY",
            "authenticated": False,
            "user": {"id": DEMO_USER_ID, "name": DEMO_USER_NAME, "role": DEMO_USER_ROLE},
            "organization": {
                "id": DEMO_ORGANIZATION_ID,
                "name": "ArchaeoAI Demonstration Workspace",
            },
            "model_runtime": runtime_status["runtime_mode"],
            "runtime_status": runtime_status,
        }

    @app.get("/api/v1/overview")
    def overview() -> dict[str, object]:
        projects = repository.list_projects()
        results = repository.list_results()
        return {
            "active_projects": len(projects),
            "awaiting_review": sum(
                r["review_state"] in {"UNREVIEWED", "IN_REVIEW"} for r in results
            ),
            "reports_ready": sum(p["status"] == "REPORT_READY" for p in projects),
            "recent_projects": projects[:5],
            "model_execution": (
                "AVAILABLE_ON_SYNTHETIC_INPUT"
                if workflow.runtime_status()["model_execution_available"]
                else "NOT_PERFORMED"
            ),
        }

    @app.get("/api/v1/projects")
    def projects() -> list[dict]:
        return repository.list_projects()

    @app.post("/api/v1/projects", status_code=201)
    def create_project(payload: ProjectCreate) -> dict:
        return repository.create_project(payload.model_dump(mode="json"))

    @app.get("/api/v1/projects/{project_id}")
    def project(project_id: str) -> dict:
        return _safe_project(repository, project_id)

    @app.delete("/api/v1/projects/{project_id}", status_code=204)
    def delete_project(project_id: str) -> None:
        project = _safe_project(repository, project_id)
        repository.delete_project(project["id"])

    @app.post("/api/v1/projects/{project_id}/authorize-demo")
    def authorize_demo(project_id: str, _payload: DemoAuthorization) -> dict:
        project = _safe_project(repository, project_id)
        return repository.authorize_demo(project["id"])

    @app.post("/api/v1/projects/{project_id}/run-demo")
    def run_demo(project_id: str, payload: DemoRunRequest) -> dict:
        project = _safe_project(repository, project_id)
        return workflow.run_demo(project["id"], payload)

    @app.get("/api/v1/projects/{project_id}/jobs")
    def jobs(project_id: str) -> list[dict]:
        project = _safe_project(repository, project_id)
        return repository.list_jobs(project["id"])

    @app.get("/api/v1/projects/{project_id}/results")
    def results(project_id: str) -> list[dict]:
        project = _safe_project(repository, project_id)
        return repository.list_results(project["id"])

    @app.get("/api/v1/results/{result_id}")
    def result(result_id: str) -> dict:
        try:
            return repository.get_result(_safe_id(result_id, RESULT_ID_PATTERN, "RESULT_NOT_FOUND"))
        except KeyError as exc:
            raise PortalApiError("RESULT_NOT_FOUND", 404) from exc

    @app.post("/api/v1/results/{result_id}/review/start")
    def start_review(result_id: str) -> dict:
        try:
            return repository.start_review(
                _safe_id(result_id, RESULT_ID_PATTERN, "RESULT_NOT_FOUND")
            )
        except KeyError as exc:
            raise PortalApiError("RESULT_NOT_FOUND", 404) from exc

    @app.post("/api/v1/results/{result_id}/review")
    def review(result_id: str, payload: ReviewRequest) -> dict:
        try:
            _safe_id(result_id, RESULT_ID_PATTERN, "RESULT_NOT_FOUND")
            return workflow.review(result_id, payload)
        except KeyError as exc:
            raise PortalApiError("RESULT_NOT_FOUND", 404) from exc

    @app.get("/api/v1/review-queue")
    def review_queue() -> list[dict]:
        return [r for r in repository.list_results() if r["review_state"] != "REVIEWED"]

    @app.get("/api/v1/projects/{project_id}/evidence")
    def evidence(project_id: str) -> list[dict]:
        project = _safe_project(repository, project_id)
        return repository.list_evidence(project["id"])

    @app.get("/api/v1/projects/{project_id}/audit")
    def audit(project_id: str) -> list[dict]:
        project = _safe_project(repository, project_id)
        return repository.list_audit(project["id"])

    @app.get("/api/v1/projects/{project_id}/report")
    def report(project_id: str) -> dict:
        project = _safe_project(repository, project_id)
        return repository.report(project["id"])

    @app.post("/api/v1/projects/{project_id}/report")
    def generate_report(project_id: str) -> dict:
        project = _safe_project(repository, project_id)
        return repository.generate_report(project["id"])

    @app.patch("/api/v1/projects/{project_id}/retention")
    def update_retention(project_id: str, payload: RetentionUpdate) -> dict:
        project = _safe_project(repository, project_id)
        return repository.update_retention(project["id"], payload.retention_policy.value)

    @app.post("/api/v1/runtime/approved/check")
    def approved_runtime_check(_payload: ApprovedRuntimeRequest) -> dict[str, object]:
        try:
            workflow.approved_runtime.validate()
        except ApprovedModelRuntimeNotAuthorizedError as exc:
            raise PortalApiError(exc.code, 403) from exc
        return workflow.runtime_status()

    app.mount("/static", StaticFiles(directory=static_root), name="static")

    @app.get("/{path:path}", include_in_schema=False)
    def index(path: str) -> FileResponse:
        del path
        return FileResponse(static_root / "index.html")

    return app
