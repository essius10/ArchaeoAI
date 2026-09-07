"""Local SQLite repository with project-scoped queries and cascade deletion."""

from __future__ import annotations

import secrets
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

SCHEMA_VERSION = 1
DEMO_ORGANIZATION_ID = "org_archaeoai_demo"
DEMO_USER_ID = "usr_local_demo"
DEMO_USER_NAME = "Local demo reviewer"
DEMO_USER_ROLE = "DEMO_REVIEWER"


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def opaque_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(6)}"


class PortalRepository:
    """Small explicit repository; no raster, coordinate, path, or feature columns exist."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        try:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    version INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS organizations (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, name TEXT NOT NULL,
                    role TEXT NOT NULL, FOREIGN KEY (organization_id) REFERENCES organizations(id)
                );
                CREATE TABLE IF NOT EXISTS projects (
                    id TEXT PRIMARY KEY, organization_id TEXT NOT NULL, name TEXT NOT NULL,
                    organization_name TEXT NOT NULL, purpose TEXT NOT NULL,
                    project_reference TEXT NOT NULL,
                    owner TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
                    status TEXT NOT NULL, review_status TEXT NOT NULL,
                    retention_policy TEXT NOT NULL,
                    processing_mode TEXT NOT NULL, authorization_state TEXT NOT NULL,
                    FOREIGN KEY (organization_id) REFERENCES organizations(id)
                );
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL, scenario TEXT NOT NULL,
                    status TEXT NOT NULL, created_at TEXT NOT NULL, completed_at TEXT,
                    model_execution TEXT NOT NULL, runtime TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS results (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL, job_id TEXT NOT NULL,
                    score REAL NOT NULL, priority TEXT NOT NULL, evidence_level TEXT NOT NULL,
                    review_state TEXT NOT NULL, thumbnail_id TEXT NOT NULL,
                    warning_code TEXT NOT NULL, limitation_code TEXT NOT NULL,
                    runtime TEXT NOT NULL, model_execution TEXT NOT NULL, created_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS reviews (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL, result_id TEXT NOT NULL,
                    reviewer TEXT NOT NULL, reviewer_role TEXT NOT NULL, category TEXT NOT NULL,
                    rationale TEXT NOT NULL, confidence TEXT NOT NULL, evidence_level TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (result_id) REFERENCES results(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS evidence (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL, result_id TEXT,
                    actor TEXT NOT NULL, actor_type TEXT NOT NULL, evidence_level TEXT NOT NULL,
                    source TEXT NOT NULL, rationale TEXT NOT NULL, status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY (result_id) REFERENCES results(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS reports (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL UNIQUE,
                    generated_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY, project_id TEXT NOT NULL, actor TEXT NOT NULL,
                    event_type TEXT NOT NULL, created_at TEXT NOT NULL, safe_detail TEXT NOT NULL,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_projects_org_updated
                    ON projects(organization_id, updated_at);
                CREATE INDEX IF NOT EXISTS idx_results_project_state
                    ON results(project_id, review_state);
                CREATE INDEX IF NOT EXISTS idx_audit_project_created
                    ON audit_events(project_id, created_at);
                """
            )
            if db.execute("SELECT COUNT(*) FROM schema_meta").fetchone()[0] == 0:
                db.execute("INSERT INTO schema_meta(version) VALUES (?)", (SCHEMA_VERSION,))
            db.execute(
                "INSERT OR IGNORE INTO organizations(id, name) VALUES (?, ?)",
                (DEMO_ORGANIZATION_ID, "ArchaeoAI Demonstration Workspace"),
            )
            db.execute(
                "INSERT OR IGNORE INTO users(id, organization_id, name, role) VALUES (?, ?, ?, ?)",
                (DEMO_USER_ID, DEMO_ORGANIZATION_ID, DEMO_USER_NAME, DEMO_USER_ROLE),
            )
            db.execute("PRAGMA optimize")

    def reset(self) -> None:
        if self.path.exists():
            self.path.unlink()
        self.initialize()

    @staticmethod
    def rows(rows: Iterable[sqlite3.Row]) -> list[dict[str, object]]:
        return [dict(row) for row in rows]

    def add_audit(self, db: sqlite3.Connection, project_id: str, event: str, detail: str) -> None:
        db.execute(
            "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?)",
            (opaque_id("aud"), project_id, DEMO_USER_NAME, event, utc_now(), detail),
        )

    def create_project(self, values: dict[str, object], *, project_id: str | None = None) -> dict:
        now = utc_now()
        identifier = project_id or opaque_id("prj")
        with self.connect() as db:
            db.execute(
                """INSERT INTO projects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    identifier,
                    DEMO_ORGANIZATION_ID,
                    values["project_name"],
                    values["organization"],
                    values["purpose"],
                    values["project_reference"],
                    DEMO_USER_NAME,
                    now,
                    now,
                    "DRAFT",
                    "NOT_STARTED",
                    values["retention_policy"],
                    "SYNTHETIC_DEMO",
                    "PENDING_DEMO_AUTHORIZATION",
                ),
            )
            self.add_audit(
                db, identifier, "PROJECT_CREATED", "Synthetic demonstration project created"
            )
        return self.get_project(identifier)

    def list_projects(self) -> list[dict]:
        with self.connect() as db:
            return self.rows(
                db.execute(
                    "SELECT * FROM projects WHERE organization_id=? ORDER BY updated_at DESC, id",
                    (DEMO_ORGANIZATION_ID,),
                )
            )

    def get_project(self, project_id: str) -> dict:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM projects WHERE id=? AND organization_id=?",
                (project_id, DEMO_ORGANIZATION_ID),
            ).fetchone()
        if row is None:
            raise KeyError("PROJECT_NOT_FOUND")
        return dict(row)

    def update_project_state(
        self, project_id: str, status: str, review_status: str | None = None
    ) -> None:
        self.get_project(project_id)
        with self.connect() as db:
            if review_status is None:
                db.execute(
                    "UPDATE projects SET status=?, updated_at=? WHERE id=?",
                    (status, utc_now(), project_id),
                )
            else:
                db.execute(
                    "UPDATE projects SET status=?, review_status=?, updated_at=? WHERE id=?",
                    (status, review_status, utc_now(), project_id),
                )

    def authorize_demo(self, project_id: str) -> dict:
        project = self.get_project(project_id)
        if project["status"] != "DRAFT":
            raise ValueError("INVALID_PROJECT_STATE")
        with self.connect() as db:
            now = utc_now()
            db.execute(
                """UPDATE projects
                SET status='AUTHORIZED_FOR_DEMO',
                    authorization_state='ATTESTED_FOR_SYNTHETIC_DEMO', updated_at=?
                WHERE id=?""",
                (now, project_id),
            )
            self.add_audit(
                db,
                project_id,
                "DEMO_AUTHORIZATION_RECORDED",
                "Synthetic-only authorization recorded",
            )
        return self.get_project(project_id)

    def create_job(self, project_id: str, scenario: str, runtime: str) -> dict:
        identifier = opaque_id("job")
        now = utc_now()
        with self.connect() as db:
            db.execute(
                """INSERT INTO jobs
                VALUES (?, ?, ?, 'QUEUED', ?, NULL, 'PENDING', ?)""",
                (identifier, project_id, scenario, now, runtime),
            )
            self.add_audit(
                db,
                project_id,
                "SYNTHETIC_DATASET_SELECTED",
                "Mathematical terrain scenario selected",
            )
            self.add_audit(
                db, project_id, "PROCESSING_STARTED", "Synthetic demonstration processing started"
            )
        self.update_project_state(project_id, "PROCESSING")
        return self.get_job(identifier, project_id)

    def get_job(self, job_id: str, project_id: str) -> dict:
        with self.connect() as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE id=? AND project_id=?", (job_id, project_id)
            ).fetchone()
        if row is None:
            raise KeyError("JOB_NOT_FOUND")
        return dict(row)

    def list_jobs(self, project_id: str) -> list[dict]:
        self.get_project(project_id)
        with self.connect() as db:
            return self.rows(
                db.execute(
                    "SELECT * FROM jobs WHERE project_id=? ORDER BY created_at", (project_id,)
                )
            )

    def complete_job(self, project_id: str, job_id: str, results: tuple) -> None:
        runtimes = {item.runtime for item in results}
        executions = {item.model_execution for item in results}
        if len(runtimes) != 1 or len(executions) != 1:
            raise ValueError("runtime provenance must be consistent within a job")
        runtime = runtimes.pop()
        model_execution = executions.pop()
        approved_execution = model_execution == "PERFORMED_APPROVED_PRIVATE_MODEL"
        with self.connect() as db:
            now = utc_now()
            for item in results:
                result_id = opaque_id("res")
                db.execute(
                    "INSERT INTO results VALUES (?, ?, ?, ?, ?, ?, 'UNREVIEWED', ?, ?, ?, ?, ?, ?)",
                    (
                        result_id,
                        project_id,
                        job_id,
                        item.score,
                        item.priority,
                        item.evidence_level.value,
                        item.thumbnail_id,
                        item.warning_code,
                        item.limitation_code,
                        item.runtime,
                        item.model_execution,
                        now,
                    ),
                )
                db.execute(
                    """INSERT INTO evidence
                    VALUES (?, ?, ?, ?, 'MACHINE', ?,
                    'MATHEMATICAL_TERRAIN',
                    'Terrain morphology prioritized for specialist review', 'ACTIVE', ?)""",
                    (
                        opaque_id("evd"),
                        project_id,
                        result_id,
                        "Frozen E001 Random Forest"
                        if approved_execution
                        else "Synthetic demo runtime",
                        item.evidence_level.value,
                        now,
                    ),
                )
            db.execute(
                """UPDATE jobs SET status='COMPLETED', completed_at=?,
                model_execution=?, runtime=? WHERE id=? AND project_id=?""",
                (now, model_execution, runtime, job_id, project_id),
            )
            self.add_audit(
                db,
                project_id,
                "PROCESSING_COMPLETED",
                (
                    "Frozen E001 model executed on synthetic mathematical terrain"
                    if approved_execution
                    else (
                        "Canonical synthetic feature preparation completed; "
                        "model execution not performed"
                    )
                ),
            )
            self.add_audit(
                db,
                project_id,
                "RESULTS_CREATED",
                (
                    "Bounded synthetic AI outputs created for human review"
                    if approved_execution
                    else "Bounded synthetic hypotheses created"
                ),
            )
        self.update_project_state(project_id, "REVIEW_REQUIRED", "AWAITING_REVIEW")

    def list_results(self, project_id: str | None = None) -> list[dict]:
        with self.connect() as db:
            if project_id is None:
                cursor = db.execute(
                    """SELECT r.* FROM results r JOIN projects p ON p.id=r.project_id
                    WHERE p.organization_id=? ORDER BY r.score DESC, r.id""",
                    (DEMO_ORGANIZATION_ID,),
                )
            else:
                self.get_project(project_id)
                cursor = db.execute(
                    "SELECT * FROM results WHERE project_id=? ORDER BY score DESC, id",
                    (project_id,),
                )
            return self.rows(cursor)

    def get_result(self, result_id: str) -> dict:
        with self.connect() as db:
            row = db.execute(
                """SELECT r.* FROM results r JOIN projects p ON p.id=r.project_id
                WHERE r.id=? AND p.organization_id=?""",
                (result_id, DEMO_ORGANIZATION_ID),
            ).fetchone()
        if row is None:
            raise KeyError("RESULT_NOT_FOUND")
        return dict(row)

    def start_review(self, result_id: str) -> dict:
        result = self.get_result(result_id)
        if result["review_state"] != "UNREVIEWED":
            raise ValueError("INVALID_REVIEW_STATE")
        with self.connect() as db:
            db.execute("UPDATE results SET review_state='IN_REVIEW' WHERE id=?", (result_id,))
            self.add_audit(db, result["project_id"], "REVIEW_STARTED", "Human review started")
        return self.get_result(result_id)

    def add_review(self, result_id: str, values: dict[str, object]) -> dict:
        result = self.get_result(result_id)
        if result["review_state"] not in {"UNREVIEWED", "IN_REVIEW"}:
            raise ValueError("INVALID_REVIEW_STATE")
        now = utc_now()
        state = (
            "ESCALATED"
            if values["category"] == "ESCALATE_TO_QUALIFIED_ARCHAEOLOGICAL_INTERPRETATION"
            else "REVIEWED"
        )
        review_id = opaque_id("rev")
        with self.connect() as db:
            db.execute(
                "INSERT INTO reviews VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    review_id,
                    result["project_id"],
                    result_id,
                    DEMO_USER_NAME,
                    DEMO_USER_ROLE,
                    values["category"],
                    values["rationale"],
                    values["confidence"],
                    values["evidence_level"],
                    now,
                ),
            )
            db.execute("UPDATE results SET review_state=? WHERE id=?", (state, result_id))
            db.execute(
                """INSERT INTO evidence
                VALUES (?, ?, ?, ?, 'HUMAN', ?, 'HUMAN_REVIEW', ?, 'ACTIVE', ?)""",
                (
                    opaque_id("evd"),
                    result["project_id"],
                    result_id,
                    DEMO_USER_NAME,
                    values["evidence_level"],
                    values["rationale"],
                    now,
                ),
            )
            self.add_audit(
                db,
                result["project_id"],
                "HUMAN_OBSERVATION_RECORDED",
                "Attributed human observation recorded separately",
            )
        remaining = [
            r
            for r in self.list_results(result["project_id"])
            if r["review_state"] in {"UNREVIEWED", "IN_REVIEW"}
        ]
        if not remaining:
            self.update_project_state(result["project_id"], "REVIEWED", "REVIEW_COMPLETE")
        return self.get_result(result_id)

    def list_evidence(self, project_id: str) -> list[dict]:
        self.get_project(project_id)
        with self.connect() as db:
            return self.rows(
                db.execute(
                    "SELECT * FROM evidence WHERE project_id=? ORDER BY created_at, id",
                    (project_id,),
                )
            )

    def list_audit(self, project_id: str) -> list[dict]:
        self.get_project(project_id)
        with self.connect() as db:
            return self.rows(
                db.execute(
                    "SELECT * FROM audit_events WHERE project_id=? ORDER BY created_at, id",
                    (project_id,),
                )
            )

    def generate_report(self, project_id: str) -> dict:
        project = self.get_project(project_id)
        now = utc_now()
        with self.connect() as db:
            db.execute(
                """INSERT INTO reports VALUES (?, ?, ?, 'READY')
                ON CONFLICT(project_id) DO UPDATE
                SET generated_at=excluded.generated_at, status='READY'""",
                (opaque_id("rpt"), project_id, now),
            )
            self.add_audit(
                db, project_id, "REPORT_GENERATED", "Synthetic demonstration report generated"
            )
        self.update_project_state(project_id, "REPORT_READY", project["review_status"])
        return self.report(project_id)

    def report(self, project_id: str) -> dict:
        project = self.get_project(project_id)
        results = self.list_results(project_id)
        evidence = self.list_evidence(project_id)
        with self.connect() as db:
            report_row = db.execute(
                "SELECT * FROM reports WHERE project_id=?", (project_id,)
            ).fetchone()
        runtimes = {result["runtime"] for result in results}
        executions = {result["model_execution"] for result in results}
        runtime = next(iter(runtimes)) if len(runtimes) == 1 else "NOT_RUN"
        model_execution = next(iter(executions)) if len(executions) == 1 else "NOT_PERFORMED"
        approved_execution = model_execution == "PERFORMED_APPROVED_PRIVATE_MODEL"
        limitations = [
            "Synthetic demonstration — not a professional archaeological assessment.",
            "Scores are terrain-pattern similarity values, not archaeological probabilities.",
        ]
        if approved_execution:
            limitations.append(
                "The frozen E001 model was executed on synthetic mathematical terrain. This "
                "demonstration does not establish the presence or absence of archaeology."
            )
        else:
            limitations.append("No approved private model or real terrain was used.")
        return {
            "status": "READY" if report_row else "NOT_GENERATED",
            "generated_at": report_row["generated_at"] if report_row else None,
            "project": project,
            "screening_summary": {
                "synthetic_hypotheses": len(results),
                "reviewed": sum(r["review_state"] in {"REVIEWED", "ESCALATED"} for r in results),
                "model_execution": model_execution,
                "runtime": runtime,
            },
            "human_observations": [e for e in evidence if e["actor_type"] == "HUMAN"],
            "limitations": limitations,
            "provenance": (
                "Deterministic mathematical terrain; canonical Phase 5 feature preparation; "
                "features discarded"
            ),
            "audit_reference": f"audit:{project_id}",
            "retention_statement": project["retention_policy"],
        }

    def update_retention(self, project_id: str, retention_policy: str) -> dict:
        self.get_project(project_id)
        with self.connect() as db:
            db.execute(
                "UPDATE projects SET retention_policy=?, updated_at=? WHERE id=?",
                (retention_policy, utc_now(), project_id),
            )
            self.add_audit(db, project_id, "RETENTION_CHANGED", "Project retention policy changed")
        return self.get_project(project_id)

    def delete_project(self, project_id: str) -> None:
        self.get_project(project_id)
        with self.connect() as db:
            db.execute(
                "DELETE FROM projects WHERE id=? AND organization_id=?",
                (project_id, DEMO_ORGANIZATION_ID),
            )

    def counts(self) -> dict[str, int]:
        with self.connect() as db:
            return {
                "projects": db.execute("SELECT COUNT(*) FROM projects").fetchone()[0],
                "jobs": db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
                "results": db.execute("SELECT COUNT(*) FROM results").fetchone()[0],
                "reviews": db.execute("SELECT COUNT(*) FROM reviews").fetchone()[0],
                "evidence": db.execute("SELECT COUNT(*) FROM evidence").fetchone()[0],
                "reports": db.execute("SELECT COUNT(*) FROM reports").fetchone()[0],
                "audit_events": db.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0],
            }
