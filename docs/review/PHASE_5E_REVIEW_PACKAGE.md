# Phase 5E external-review package

Status: **READY FOR EXTERNAL REVIEW — PHASE 5E NOT COMPLETED**

The scientific/runtime evidence package originally sent to reviewers is pinned to
`2eab2716af01c7cf007b84342058483bfd1414a0`. Phase 5E-C starts from merged Phase 5E-B commit
`8ac77c0c313a2966a0de54210a0e2dfd4f7a43f9`. A new review must name the exact commit actually
examined; use the deterministic bundle manifest rather than assuming that either historical SHA was
reviewed. This infrastructure is not evidence that independent review occurred. The controlling
status is `RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW`.

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

## Version-bound execution workflow

1. From a clean committed checkout, run `python scripts/build_phase5e_review_bundle.py --commit HEAD`.
2. Record the generated directory and `manifest.sha256`; verify it with
   `python scripts/validate_phase5e_review.py --verify-bundle <bundle-directory>`.
3. Inspect only the assigned track and the files labelled for it in `manifest.json`. Do not request
   private material unless the owner separately authorizes a bounded private process.
4. Copy `templates/phase5e_review.template.json` outside the repository. Use a stable review ID,
   one domain, the manifest's full commit SHA, and complete every declaration.
5. Validate with `python scripts/validate_phase5e_review.py --review <completed-review.json>`.
   Record the returned review SHA-256 when handing the public-safe record to the owner.
6. The owner places accepted public-safe evidence under `docs/review/evidence/`, records every
   finding disposition, and runs `python scripts/validate_phase5e_review.py`.

The validator enforces four independent domain records, strict attribution and declarations, safe
repository references, stable finding IDs, and exact hashes. The same JSON record cannot satisfy
multiple domains. One person may cover more than one domain only through separate records with
domain-specific scope and supportable expertise; the owner must not infer unreviewed coverage.

## Evidence and finding contract

A completed record identifies the review, domain, commit, review-bundle manifest SHA-256, date,
public attribution, optional affiliation, expertise, independence and conflict declarations, scope,
methodology, tools, AI assistance, limitations, findings, conclusion, attestation, and evidence
references. Private contact details are prohibited.

Findings use stable `P5E-<DOMAIN>-F###` IDs and severities `blocker`, `high`, `medium`, `low`, or
`informational`. Each records its originating review, evidence, affected components, four impact
flags, and recommended action. Reviewer evidence remains distinct from owner disposition,
remediation, and final verification. The owner's machine-readable closing decision may use
`ACCEPT`, `REMEDIATE`, `DEFER`, or `REJECT_WITH_RATIONALE`; rationale is mandatory, remediation
requires evidence and a resolving commit, and `blocker`/`high` findings must be remediated before
the automated completion gate can close. Hash-bound accepted reviews prevent a finding from being
silently removed by deleting a register row.

## Safe reporting

Do not put coordinates, private terrain, model bytes, credentials, exploitable details, restricted
data, private correspondence, or unnecessary personal information in a public issue or review
record. Use a redacted public finding with an opaque owner-controlled evidence reference. Arrange
private transfer through an already agreed owner-controlled channel; this repository invents no
email address or public contact route. See `evidence/README.md` and `SECURITY.md`.
