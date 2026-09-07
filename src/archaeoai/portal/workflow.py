"""Application workflow enforcing synthetic-only processing and evidence boundaries."""

from __future__ import annotations

from archaeoai.portal.demo_runtime import SyntheticDemoRuntime
from archaeoai.portal.model_runtime import DisabledApprovedModelRuntime
from archaeoai.portal.repository import PortalRepository
from archaeoai.portal.schemas import DemoRunRequest, EvidenceLevel, ReviewRequest


class PortalWorkflow:
    def __init__(self, repository: PortalRepository):
        self.repository = repository
        self.demo_runtime = SyntheticDemoRuntime()
        self.approved_runtime = DisabledApprovedModelRuntime()

    def run_demo(self, project_id: str, request: DemoRunRequest) -> dict:
        project = self.repository.get_project(project_id)
        if project["status"] != "AUTHORIZED_FOR_DEMO":
            raise ValueError("DEMO_AUTHORIZATION_REQUIRED")
        job = self.repository.create_job(project_id, request.scenario.value)
        results = self.demo_runtime.screen(request.scenario)
        if any(
            item.evidence_level not in {EvidenceLevel.AI_OUTPUT, EvidenceLevel.AI_HYPOTHESIS}
            for item in results
        ):
            raise RuntimeError("MACHINE_EVIDENCE_LEVEL_VIOLATION")
        self.repository.complete_job(project_id, job["id"], results)
        return self.repository.get_job(job["id"], project_id)

    def review(self, result_id: str, request: ReviewRequest) -> dict:
        if request.evidence_level is not EvidenceLevel.HUMAN_VETTED_OBSERVATION:
            raise ValueError("EVIDENCE_PROMOTION_NOT_AUTHORIZED")
        return self.repository.add_review(result_id, request.model_dump(mode="json"))

    def seed_demo(self) -> None:
        if self.repository.list_projects():
            return
        seeds = (
            (
                "prj_demo0000001",
                "Demo Terrain Assessment A",
                "Explore a synthetic terrain screening and human review workflow.",
                "DEMO-A",
                "SESSION_ONLY",
                "MOUND_LIKE",
            ),
            (
                "prj_demo0000002",
                "Infrastructure Screening Demo",
                "Demonstrate bounded mixed mathematical terrain processing.",
                "DEMO-B",
                "SEVEN_DAYS",
                "MIXED_MATHEMATICAL",
            ),
        )
        for project_id, name, purpose, reference, retention, scenario in seeds:
            project = self.repository.create_project(
                {
                    "project_name": name,
                    "organization": "ArchaeoAI Demonstration Workspace",
                    "purpose": purpose,
                    "project_reference": reference,
                    "retention_policy": retention,
                },
                project_id=project_id,
            )
            self.repository.authorize_demo(project["id"])
            self.run_demo(
                project["id"], DemoRunRequest(scenario=scenario, runtime="SYNTHETIC_DEMO")
            )
        self.repository.create_project(
            {
                "project_name": "Heritage Review Demonstration",
                "organization": "ArchaeoAI Demonstration Workspace",
                "purpose": (
                    "Prepare a synthetic project while retaining explicit authorization gates."
                ),
                "project_reference": "DEMO-C",
                "retention_policy": "THIRTY_DAYS",
            },
            project_id="prj_demo0000003",
        )
