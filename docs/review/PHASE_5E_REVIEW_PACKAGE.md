# Phase 5E external-review package

Status: **READY FOR EXTERNAL REVIEW — PHASE 5E NOT COMPLETED**

The scientific/runtime evidence package sent to reviewers is pinned to
`2eab2716af01c7cf007b84342058483bfd1414a0`. The Phase 5E-B review PR starts from
`430ed346c49fb7fa89d778d1b7483fe5be4a2216`; the intervening PR #13 changed only GitHub discovery
and contributor documentation. Review the Phase 5E-B PR head for the disclosure, completion gate,
and handoff. This remains internal preparation, not evidence that independent review occurred. The
controlling status is `RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW`.

The current implementation includes the Phase 5A–5D inference foundations, the Phase 6C local
FastAPI/SQLite workflow, and the Phase 6D approved private Random Forest runtime over generated
mathematical terrain. Real/customer terrain, uploads, remote model execution, candidate publication,
Phase 5F, and pilot/production deployment remain unauthorized.

## Common reviewer setup

From a supported clean checkout:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,portal]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
.\scripts\validate_project.ps1
.\scripts\doctor.ps1
python scripts\doctor.py
python -m pip check
```

A public checkout cannot execute the approved model because its private pickle is intentionally
absent. Reviewers without separately authorized private access should assess the public loader,
failure paths, tests, documentation, and CI; they must not substitute another artifact.

For a five-minute orientation, start with the
[reviewer handoff](PHASE_5E_REVIEWER_HANDOFF.md), then read the
[AI assistance disclosure](AI_ASSISTANCE_AND_AUTHORSHIP_DISCLOSURE.md) and
[completion gate](PHASE_5E_COMPLETION_GATE.md).

## Track 1 — Security / threat

- **Expertise:** Python application security, FastAPI/Uvicorn, local-service boundaries,
  deserialization/supply-chain risk, and adversarial file handling.
- **Inspect:** `SECURITY.md`; `src/archaeoai/inference_system/private_model_adapter.py`;
  `src/archaeoai/portal/app.py`; `src/archaeoai/portal/launch.py`;
  `docs/product/COMMERCIAL_THREAT_MODEL.md`.
- **Tests:** `tests/test_phase5c_offline_cli.py`; `tests/test_phase5d_bounded_batch.py`;
  `tests/test_phase6d_private_model_adapter.py`; `tests/test_phase6d_portal_runtime.py`;
  `tests/test_phase5e_a_pre_review_hardening.py`.
- **Focused command:** `python -m pytest tests/test_phase6d_private_model_adapter.py tests/test_phase6d_portal_runtime.py tests/test_phase5e_a_pre_review_hardening.py`.
- **Known limitations:** no penetration test or fuzz campaign; no production authentication,
  sandbox, secret-management, deployment, monitoring, or incident system. SHA-256 does not establish
  pickle trust or benignness.
- **Intentionally private:** model bytes, artifact custody evidence, host configuration, and secrets.

## Track 2 — Privacy / retention

- **Expertise:** privacy engineering, archaeological sensitivity, application logging, SQLite
  retention/deletion, and data-lifecycle review.
- **Inspect:** `docs/product/PRODUCT_PRIVACY_AND_DATA_LIFECYCLE.md`;
  `src/archaeoai/portal/repository.py`; `src/archaeoai/portal/schemas.py`;
  `src/archaeoai/portal/static/`; `.gitignore`; `SECURITY.md`.
- **Tests:** `tests/test_phase6c_commercial_portal.py`;
  `tests/test_phase5e_a_pre_review_hardening.py`.
- **Focused command:** `python -m pytest tests/test_phase6c_commercial_portal.py tests/test_phase5e_a_pre_review_hardening.py`.
- **Known limitations:** deletion is logical SQLite cascade or database-file replacement, not proven
  forensic erasure; retention timers are labels, not a scheduler; no real/customer data is authorized.
- **Intentionally private:** coordinates, private terrain, candidate locations, private review data,
  and the local SQLite database.

## Track 3 — Archaeological / scientific workflow

- **Expertise:** landscape archaeology/heritage practice, LiDAR interpretation, spatial validation,
  uncertainty communication, and research methods.
- **Inspect:** `docs/review/REVIEWER_GUIDE.md`; `docs/review/PHASE_4D_RQ1_AUDIT.md`;
  `docs/claims-register.md`; `docs/manuscript/archaeoai-e001-manuscript.md`;
  `docs/product/PRODUCT_EVIDENCE_AND_HUMAN_REVIEW.md`; `docs/CURRENT_STATUS.md`.
- **Tests:** `tests/test_phase4d_rq1_audit.py`; `tests/test_manuscript_package.py`;
  `tests/test_phase6d_portal_runtime.py`; `tests/test_phase5e_a_pre_review_hardening.py`.
- **Focused command:** `python -m pytest tests/test_phase4d_rq1_audit.py tests/test_manuscript_package.py tests/test_phase6d_portal_runtime.py`.
- **Known limitations:** bowl-barrow-only scope, `unlabelled_background`, bounded geographic evidence,
  spent external test, and no claim of discovery, field confirmation, or general archaeological
  probability.
- **Intentionally private:** row-level labels/predictions, exact locations, terrain, and candidate data.

## Track 4 — Licensing / data / model

- **Expertise:** software and data licensing, public-sector data terms, model-artifact ownership,
  redistribution, and intended commercial-use review. This package is not legal advice.
- **Inspect:** `docs/licensing-and-attribution.md`; `docs/reproducibility.md`; `pyproject.toml`;
  `README.md`; data-source decision records; model identity documentation; and the
  [exact licensing questions](PHASE_5E_LICENSING_QUESTIONS.md).
- **Tests:** `tests/test_review_readiness.py`; `tests/test_manuscript_package.py`; project validator.
- **Focused command:** `python -m pytest tests/test_review_readiness.py tests/test_manuscript_package.py; .\scripts\validate_project.ps1`.
- **Known limitations:** repository licensing, dependency distribution, source-data attribution,
  private-model authority, derived-output rights, and commercial-use implications require an
  appropriately qualified reviewer. Unresolved questions must not be marked `PASS`.
- **Intentionally private:** restricted source records, private terrain, model artifact, and private
  provenance/custody evidence.

## Review procedure and disposition

1. Record scope and expertise in the
   [Phase 5E checklist](PHASE_5E_EXTERNAL_REVIEW_CHECKLIST.md).
2. Mark every examined item `PASS`, `CONCERN`, or `NOT REVIEWED`; do not infer approval outside scope.
3. Record findings in the [feedback register](FEEDBACK_REGISTER.md) without sensitive material.
4. Copy substantive findings to the
   [owner disposition register](PHASE_5E_OWNER_DISPOSITION.md), then resolve or explicitly accept
   them with evidence and a named owner decision.
5. Hold a separate authorization gate. Review completion alone does not authorize Phase 5F.

No reviewer names, decisions, endorsements, or completed `PASS` statuses are asserted here.
