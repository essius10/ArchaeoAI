"""Local-only portal launch command."""

from __future__ import annotations

from pathlib import Path

from archaeoai.paths import find_project_root


def default_database_path() -> Path:
    return find_project_root() / "data" / "private" / "portal" / "archaeoai_portal.sqlite3"


def launch_portal(*, demo: bool, reset: bool, port: int) -> int:
    if not demo:
        print("ERROR: Phase 6C authorizes only --demo mode.")
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
    from archaeoai.portal.repository import PortalRepository
    from archaeoai.portal.workflow import PortalWorkflow

    database = default_database_path()
    repository = PortalRepository(database)
    if reset:
        repository.reset()
        PortalWorkflow(repository).seed_demo()
    print(f"ArchaeoAI portal: http://127.0.0.1:{port}")
    print("DEMO MODE — SYNTHETIC DATA · approved model runtime disabled")
    uvicorn.run(
        create_app(database),
        host="127.0.0.1",
        port=port,
        access_log=False,
        log_level="warning",
    )
    return 0
