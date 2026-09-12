# Phase 5E external-review checklist

This is a blank review instrument for an independent reviewer. It does not record approval, and
Phase 5E remains **NOT COMPLETED**. For each item, select exactly one of `PASS`, `CONCERN`, or
`NOT REVIEWED`, cite evidence, and explain the scope and limitations of the assessment.

## Current implementation boundary

- **Current local portal:** a FastAPI/Uvicorn professional-workflow demonstration with ignored,
  local SQLite persistence. Its default scorer is synthetic. It has no production authentication
  and is not a public production SaaS.
- **Current approved private runtime:** one fixed-path private pickle, verified by artifact and
  learned-state SHA-256, exact `RandomForestClassifier` type, frozen model identifier, and explicit
  server-start authorization. It is restricted to `127.0.0.1` and application-generated
  mathematical terrain. It accepts no caller model path and cannot silently fall back to demo
  scoring while reporting approved execution.
- **Still unauthorized:** real or customer terrain, uploads, public/remote model inference,
  candidate-location publication, Phase 5F, and pilot or production deployment.

SHA-256 is an integrity check, not evidence that a pickle is benign, trustworthy, lawfully sourced,
or safe to deserialize. Pickle deserialization can execute code. Reviewers must separately assess
artifact provenance, custody, authorization, and runtime isolation.

## 1. Security / threat review

| Review item | PASS / CONCERN / NOT REVIEWED | Reviewer notes | Repository evidence |
| --- | --- | --- | --- |
| Local Phase 5C/5D file handling rejects traversal, absolute/drive/URL syntax, directory escape, and symlinks. |  |  | `src/archaeoai/inference_system/geotiff.py`; `src/archaeoai/inference_system/batch.py`; `tests/test_phase5d_bounded_batch.py` |
| Malformed, truncated, oversized, or non-canonical GeoTIFFs fail closed. |  |  | `src/archaeoai/inference_system/geotiff.py`; `tests/test_phase5c_offline_cli.py` |
| Batch limits remain 64 items, 64 KiB manifest, 2 MiB each, and 16 MiB cumulative. |  |  | `src/archaeoai/inference_system/batch.py`; `tests/test_phase5d_bounded_batch.py` |
| The portal creates no terrain/feature temporary files or caches; its documented SQLite retention is accurate. |  |  | `src/archaeoai/portal/repository.py`; `docs/product/PORTAL_RUNBOOK.md`; `tests/test_phase5e_a_pre_review_hardening.py` |
| The approved pickle is fixed-path, private, ignored, untracked, and never caller-selectable. |  |  | `src/archaeoai/inference_system/private_model_adapter.py`; `.gitignore`; `tests/test_phase6d_private_model_adapter.py` |
| Artifact SHA mismatch is rejected before deserialization; missing artifact, state mismatch, wrong class, identifier, or configuration fail closed. |  |  | `src/archaeoai/inference_system/private_model_adapter.py`; `tests/test_phase6d_private_model_adapter.py` |
| Artifact provenance/trust is established independently of its SHA-256 digest before deserialization. |  |  | `docs/product/PHASE_6D_APPROVED_MODEL_RUNTIME.md`; owner-controlled private evidence (not public) |
| Approved-runtime failures never fall back to demo scoring while claiming real execution. |  |  | `src/archaeoai/portal/launch.py`; `src/archaeoai/portal/workflow.py`; `tests/test_phase6d_portal_runtime.py` |
| Error responses omit paths, pickle/model internals, request bodies, and private content. |  |  | `src/archaeoai/portal/app.py`; `tests/test_phase6d_portal_runtime.py` |
| Approved execution is startup-authorized, server-side, synthetic-only, and bound only to `127.0.0.1`. |  |  | `src/archaeoai/portal/launch.py`; `src/archaeoai/portal/app.py`; `tests/test_phase5e_a_pre_review_hardening.py` |
| The unauthenticated local demonstration is acceptable only within the stated loopback, synthetic, non-production scope. |  |  | `docs/product/COMMERCIAL_THREAT_MODEL.md`; `docs/product/PORTAL_RUNBOOK.md` |
| Future network/API deployment has separate authentication, authorization, isolation, monitoring, incident, rate/size, and abuse-control gates. |  |  | `docs/product/COMMERCIAL_THREAT_MODEL.md`; `SECURITY.md` |

## 2. Privacy / retention review

| Review item | PASS / CONCERN / NOT REVIEWED | Reviewer notes | Repository evidence |
| --- | --- | --- | --- |
| Portal request schemas admit no terrain uploads, paths, arrays, URLs, coordinates, bounds, or transforms. |  |  | `src/archaeoai/portal/schemas.py`; `tests/test_phase5e_a_pre_review_hardening.py` |
| API/HTML/results/reports/evidence/audit/runtime surfaces expose no coordinates, paths, bounds, transforms, feature vectors, model contents, or candidate locations. |  |  | `src/archaeoai/portal/app.py`; `src/archaeoai/portal/static/`; `tests/test_phase5e_a_pre_review_hardening.py` |
| SQLite schema contains no terrain, coordinate, path, transform, raster, feature-vector, or candidate-location fields. |  |  | `src/archaeoai/portal/repository.py`; `tests/test_phase5e_a_pre_review_hardening.py` |
| The 4,096-element model input is transient and discarded after scoring rather than persisted. |  |  | `src/archaeoai/portal/approved_runtime.py`; `tests/test_phase6d_portal_runtime.py`; `tests/test_phase5e_a_pre_review_hardening.py` |
| Project metadata, human rationales, scores, and audit events retained in local SQLite match the documented data inventory. |  |  | `src/archaeoai/portal/repository.py`; `docs/product/PRODUCT_PRIVACY_AND_DATA_LIFECYCLE.md` |
| Project deletion cascades through jobs, results, reviews, evidence, reports, and audit rows. |  |  | `src/archaeoai/portal/repository.py`; `tests/test_phase5e_a_pre_review_hardening.py` |
| Documentation distinguishes logical SQLite deletion/reset from forensic or physical-media erasure. |  |  | `docs/product/PORTAL_RUNBOOK.md`; `docs/product/PRODUCT_PRIVACY_AND_DATA_LIFECYCLE.md` |
| Uvicorn access logs are disabled; warning/error logs are not falsely described as nonexistent and exclude request bodies/private values by design. |  |  | `src/archaeoai/portal/launch.py`; `docs/product/PORTAL_RUNBOOK.md` |
| There is no application telemetry or analytics in the current portal. |  |  | `src/archaeoai/portal/`; `docs/product/PRODUCT_PRIVACY_AND_DATA_LIFECYCLE.md` |
| Archaeological location sensitivity and future upload/retention/deletion obligations remain explicit blockers. |  |  | `SECURITY.md`; `docs/product/PRODUCT_PRIVACY_AND_DATA_LIFECYCLE.md` |
| Candidate locations cannot be published without archaeological sensitivity review and explicit owner approval. |  |  | `docs/claims-register.md`; `SECURITY.md`; `docs/review/REVIEWER_GUIDE.md` |

## 3. Archaeological / scientific workflow review

| Review item | PASS / CONCERN / NOT REVIEWED | Reviewer notes | Repository evidence |
| --- | --- | --- | --- |
| Automatic approved-model output is exactly `AI_OUTPUT`, distinct from human or archaeological interpretation. |  |  | `src/archaeoai/portal/approved_runtime.py`; `src/archaeoai/portal/repository.py` |
| The evidence ladder distinguishes model output, hypothesis, human observation, archaeologist validation, and confirmation. |  |  | `docs/review/REVIEWER_GUIDE.md`; `docs/product/PRODUCT_EVIDENCE_AND_HUMAN_REVIEW.md` |
| The score is described only as bounded terrain-pattern similarity, never archaeological/site probability or calibrated confidence. |  |  | `src/archaeoai/portal/`; `docs/product/PHASE_6D_APPROVED_MODEL_RUNTIME.md` |
| No output implies archaeological discovery, confirmation, absence, or that land is safe to build/develop. |  |  | `README.md`; `docs/claims-register.md`; `tests/test_phase5e_a_pre_review_hardening.py` |
| Qualified human review remains mandatory before stronger archaeological interpretation. |  |  | `src/archaeoai/portal/schemas.py`; `docs/review/REVIEWER_GUIDE.md` |
| Claims remain limited to bowl-barrow terrain versus matched `unlabelled_background`. |  |  | `docs/research-charter.md`; `docs/manuscript/archaeoai-e001-manuscript.md` |
| Geographic generalization remains limited to the evaluated regions, sources, and design. |  |  | `docs/manuscript/archaeoai-e001-manuscript.md`; `docs/CURRENT_STATUS.md` |
| The external test remains spent and unavailable for tuning or reinterpretation. |  |  | `docs/CURRENT_STATUS.md`; `docs/reproducibility.md`; `docs/claims-register.md` |
| RQ1 remains exactly `RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW`; internal hardening does not advance it. |  |  | `docs/review/PHASE_4D_RQ1_AUDIT.md`; `docs/CURRENT_STATUS.md`; `docs/decision-log.md` |
| Human, external-expert, generative-AI, and automated-tool roles are disclosed candidly without treating AI assistance as independent review. |  |  | `docs/review/AI_ASSISTANCE_AND_AUTHORSHIP_DISCLOSURE.md`; `research-log/` |

## 4. Licensing / data / model review

| Review item | PASS / CONCERN / NOT REVIEWED | Reviewer notes | Repository evidence |
| --- | --- | --- | --- |
| Source-data terms, attribution requirements, and redistribution restrictions are verified against authoritative terms. |  |  | `docs/licensing-and-attribution.md`; `docs/reproducibility.md` |
| Private terrain and location-linked source material remain untracked and outside public releases. |  |  | `.gitignore`; `SECURITY.md`; `docs/reproducibility.md` |
| Ownership, provenance, custody, and authority to use the private pickle are established separately from hash verification. |  |  | `docs/product/PHASE_6D_APPROVED_MODEL_RUNTIME.md`; private owner evidence (not public) |
| Model use and redistribution are separately authorized; code publication does not grant model redistribution rights. |  |  | `docs/licensing-and-attribution.md`; `docs/architecture/PHASE_5_INFERENCE_ARCHITECTURE.md` |
| Repository licensing status is accurate and compatible with the intended use. |  |  | `README.md`; `docs/licensing-and-attribution.md`; `LICENSE` if present |
| Third-party dependency licenses and notices are reviewed for the intended distribution. |  |  | `pyproject.toml`; `docs/licensing-and-attribution.md` |
| Rights for derived representations, figures, reports, and other outputs are documented. |  |  | `docs/licensing-and-attribution.md`; `docs/reproducibility.md` |
| Commercial use is not assumed; unresolved data, model, dependency, and repository terms remain `NOT REVIEWED` or `CONCERN`. |  |  | `docs/licensing-and-attribution.md`; `docs/product/COMMERCIAL_DECISION_GATES.md` |

## Reviewer declaration

- **Stable public attribution (private contact details are not required):**
- **Affiliation, if supplied:**
- **Reviewer role/expertise:**
- **Review date:**
- **Review scope (tracks/items examined):**
- **Exact commit reviewed:**
- **Review methodology:**
- **Tools used:**
- **Conflicts, access constraints, or limitations:**
- **AI or automated tools used during this review (if any):**
- **Overall recommendation:** `PASS` / `PASS WITH CONDITIONS` / `CHANGES REQUIRED` / `NO-GO`
- **Recommendation notes and required actions:**
- **Evidence references:**
- **Attestation that this record represents the stated scope and limitations:**

Completing this form records only the named reviewer's assessment of the stated scope. It does not
imply institutional endorsement, archaeological confirmation, or completion of unreviewed tracks.

## Owner decision gate

Checklist completion does not automatically authorize Phase 5F or any real-data, upload, network,
deployment, model-distribution, pilot, or candidate-publication work. Substantive findings require
documented disposition in `PHASE_5E_OWNER_DISPOSITION.md` and explicit owner approval under
`PHASE_5E_COMPLETION_GATE.md` at a separate gate.

Until actual independent review occurs, external review remains **NOT COMPLETED**, Phase 5F remains
**NOT AUTHORIZED**, and `RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW` remains controlling.

For attributable machine validation, transfer the completed assessment into one copy of
`templates/phase5e_review.template.json` per review domain and run
`python scripts/validate_phase5e_review.py --review <record.json>`. A blank template, placeholder,
or structurally valid but unattributable note cannot satisfy the gate.
