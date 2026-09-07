"""Local-only portal launch command."""

from __future__ import annotations

from pathlib import Path

from archaeoai.paths import find_project_root

ALLOWED_PORTAL_HOSTS = ("127.0.0.1", "0.0.0.0")


def default_database_path() -> Path:
    return find_project_root() / "data" / "private" / "portal" / "archaeoai_portal.sqlite3"


def launch_portal(
    *,
    demo: bool,
    reset: bool,
    port: int,
    host: str = "127.0.0.1",
    approved_model_runtime: bool = False,
) -> int:
    if not demo:
        print("ERROR: Phase 6C authorizes only --demo mode.")
        return 2
    if host not in ALLOWED_PORTAL_HOSTS:
        print("ERROR: portal host must be 127.0.0.1 or 0.0.0.0.")
        return 2
    if approved_model_runtime and host != "127.0.0.1":
        print("ERROR: approved private model runtime is restricted to 127.0.0.1.")
        return 2
    if not 1024 <= port <= 65535:
        print("ERROR: portal port must be between 1024 and 65535.")
        return 2
    try:
        import uvicorn
    except ModuleNotFoundError:
        print('ERROR: install portal dependencies with: python -m pip install -e ".[portal]"')
        return 2

    from archaeoai.portal.app import create_app
    from archaeoai.portal.approved_runtime import ApprovedPrivateRandomForestRuntime
    from archaeoai.portal.repository import PortalRepository
    from archaeoai.portal.workflow import PortalWorkflow

    approved_runtime = None
    if approved_model_runtime:
        from archaeoai.inference_system import (
            ApprovedPrivateModelLoadError,
            load_approved_private_random_forest,
        )

        try:
            project_root = find_project_root()
            adapter = load_approved_private_random_forest(project_root)
            approved_runtime = ApprovedPrivateRandomForestRuntime(project_root, adapter)
            approved_runtime.validate()
        except ApprovedPrivateModelLoadError:
            print("ERROR: approved private model is unavailable or failed verification.")
            return 2

    database = default_database_path()
    repository = PortalRepository(database)
    if reset:
        repository.reset()
        PortalWorkflow(repository, approved_runtime=approved_runtime).seed_demo()
    if host == "127.0.0.1":
        print(f"ArchaeoAI portal: http://127.0.0.1:{port}")
    else:
        print(f"ArchaeoAI portal listening on 0.0.0.0:{port}")
        print(f"Web Preview: expose/open port {port}")
    if approved_runtime is None:
        print("DEMO MODE — SYNTHETIC DATA · approved model runtime disabled")
    else:
        print("REAL FROZEN MODEL · SYNTHETIC TERRAIN · LOCAL PRIVATE")
        print("Score semantics: bounded terrain-pattern similarity; not archaeological probability")
    uvicorn.run(
        create_app(database, approved_runtime=approved_runtime),
        host=host,
        port=port,
        access_log=False,
        log_level="warning",
    )
    return 0
