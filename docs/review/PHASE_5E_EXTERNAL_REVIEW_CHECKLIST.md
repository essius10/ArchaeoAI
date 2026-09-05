# Phase 5E external-review checklist

This checklist defines the evidence an independent reviewer should examine before any Phase 5F
public-interface work is considered. It is a review instrument, not evidence that a review has
occurred. For every item, select exactly one status—`PASS`, `CONCERN`, or `NOT REVIEWED`—and add
brief notes with supporting file or line references. Reviewers should assess only material within
their expertise and record limitations in the declaration.

## 1. Security / threat review

| Review item | Status: PASS / CONCERN / NOT REVIEWED | Reviewer notes | Repository evidence |
| --- | --- | --- | --- |
| Local file handling is allowlisted, bounded, and fail-closed. |  |  | `src/archaeoai/inference_system/geotiff.py`; `src/archaeoai/inference_system/batch.py` |
| Absolute paths, traversal, drive/URL syntax, and directory escape are rejected. |  |  | `src/archaeoai/inference_system/batch.py`; `tests/test_phase5d_bounded_batch.py` |
| Symlinks cannot bypass manifest or terrain-file boundaries. |  |  | `src/archaeoai/inference_system/batch.py`; `tests/test_phase5d_bounded_batch.py` |
| Malformed, truncated, oversized, or non-canonical GeoTIFFs fail safely. |  |  | `src/archaeoai/inference_system/geotiff.py`; `tests/test_phase5c_offline_cli.py` |
| Batch limits remain 64 items, 64 KiB per manifest, 2 MiB per item, and 16 MiB cumulative. |  |  | `src/archaeoai/inference_system/batch.py`; `tests/test_phase5d_bounded_batch.py` |
| No temporary-file, cache, or persistent-retention path is introduced. |  |  | `src/archaeoai/inference_system/batch.py`; `src/archaeoai/cli.py`; `SECURITY.md` |
| Pickle and unsafe model deserialization risks are absent now and explicitly addressed before future model loading. |  |  | `SECURITY.md`; `docs/architecture/PHASE_5_INFERENCE_ARCHITECTURE.md` |
| Any future approved model artifact must be authenticated against its frozen hash before use. |  |  | `docs/architecture/PHASE_5_INFERENCE_ARCHITECTURE.md`; `docs/reproducibility.md` |
| Errors use bounded codes and do not disclose caller-controlled paths or private content. |  |  | `src/archaeoai/inference_system/batch.py`; `src/archaeoai/cli.py` |
| Future network/API entry points have an explicit threat model before authorization. |  |  | `SECURITY.md`; `docs/architecture/PHASE_5_INFERENCE_ARCHITECTURE.md` |
| Future abuse controls cover authentication, rate/size limits, isolation, monitoring, and denial-of-service risks. |  |  | `SECURITY.md`; `docs/roadmap.md` |

## 2. Privacy review

| Review item | Status: PASS / CONCERN / NOT REVIEWED | Reviewer notes | Repository evidence |
| --- | --- | --- | --- |
| Exact coordinates are excluded from public inputs, outputs, logs, and documentation. |  |  | `SECURITY.md`; `docs/reproducibility.md`; `tests/test_phase5d_bounded_batch.py` |
| Raster bounds, transforms, and other georeferencing metadata are not emitted. |  |  | `src/archaeoai/inference_system/geotiff.py`; `src/archaeoai/inference_system/batch.py` |
| Filenames and filesystem paths are not exposed in errors or results. |  |  | `src/archaeoai/inference_system/batch.py`; `src/archaeoai/cli.py` |
| Archaeological location sensitivity is reflected in the public/private data boundary. |  |  | `SECURITY.md`; `docs/reproducibility.md`; `docs/review/REVIEWER_GUIDE.md` |
| Logs and telemetry do not capture private inputs or location-linked metadata. |  |  | `src/archaeoai/cli.py`; `SECURITY.md` |
| Inputs, arrays, and derived features are not retained after bounded processing. |  |  | `src/archaeoai/inference_system/batch.py`; `docs/architecture/PHASE_5_INFERENCE_ARCHITECTURE.md` |
| Per-item output is limited to opaque IDs and bounded operational status. |  |  | `src/archaeoai/inference_system/batch.py`; `tests/test_phase5d_bounded_batch.py` |
| Aggregate reporting contains no coordinates, paths, feature vectors, or model scores. |  |  | `src/archaeoai/inference_system/batch.py`; `tests/test_phase5d_bounded_batch.py` |
| Any future upload flow defines access, deletion, retention, encryption, and incident-response controls first. |  |  | `SECURITY.md`; `docs/roadmap.md` |
| Candidate locations cannot be published without a documented archaeological sensitivity review and owner approval. |  |  | `docs/claims-register.md`; `docs/review/REVIEWER_GUIDE.md`; `SECURITY.md` |

## 3. Archaeological/scientific workflow review

| Review item | Status: PASS / CONCERN / NOT REVIEWED | Reviewer notes | Repository evidence |
| --- | --- | --- | --- |
| AI output is kept distinct from archaeological interpretation. |  |  | `docs/review/REVIEWER_GUIDE.md`; `docs/claims-register.md` |
| The evidence ladder distinguishes model output, hypothesis, human-vetted observation, archaeologist validation, and confirmation. |  |  | `docs/review/REVIEWER_GUIDE.md`; `docs/review/PHASE_4D_RQ1_AUDIT.md` |
| Public wording uses “terrain similarity” only within its documented bounded meaning. |  |  | `docs/claims-register.md`; `docs/CURRENT_STATUS.md`; `README.md` |
| Scores are not interpreted as calibrated archaeological probabilities. |  |  | `docs/review/REVIEWER_GUIDE.md`; `docs/claims-register.md` |
| No output or workflow implies an archaeological discovery claim. |  |  | `README.md`; `docs/claims-register.md`; `docs/review/PHASE_4D_RQ1_AUDIT.md` |
| Qualified human review is required before stronger archaeological interpretation. |  |  | `docs/review/REVIEWER_GUIDE.md`; `docs/roadmap.md` |
| Claims remain limited to documented bowl-barrow terrain versus matched `unlabelled_background`. |  |  | `docs/research-charter.md`; `docs/manuscript/archaeoai-e001-manuscript.md` |
| Geographic results are not generalized beyond the evaluated regions, data sources, and design. |  |  | `docs/manuscript/archaeoai-e001-manuscript.md`; `docs/CURRENT_STATUS.md` |
| The independent external test is identified as spent and unavailable for tuning or reinterpretation. |  |  | `docs/CURRENT_STATUS.md`; `docs/reproducibility.md`; `docs/claims-register.md` |
| RQ1 remains exactly `RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW`; this checklist does not advance it. |  |  | `docs/review/PHASE_4D_RQ1_AUDIT.md`; `docs/CURRENT_STATUS.md`; `docs/decision-log.md` |

## 4. Licensing / data / model review

| Review item | Status: PASS / CONCERN / NOT REVIEWED | Reviewer notes | Repository evidence |
| --- | --- | --- | --- |
| Source-data terms and attribution requirements are identified and verified against authoritative terms. |  |  | `docs/licensing-and-attribution.md`; `docs/reproducibility.md` |
| Redistribution restrictions are respected for raw and location-linked data. |  |  | `docs/licensing-and-attribution.md`; `SECURITY.md` |
| Private terrain remains untracked and outside public release artifacts. |  |  | `.gitignore`; `SECURITY.md`; `docs/reproducibility.md` |
| Ownership and authority to use the private model artifact are documented before deployment. |  |  | `docs/architecture/PHASE_5_INFERENCE_ARCHITECTURE.md`; `SECURITY.md` |
| Model redistribution is separately authorized and does not follow automatically from code publication. |  |  | `docs/licensing-and-attribution.md`; `docs/architecture/PHASE_5_INFERENCE_ARCHITECTURE.md` |
| The repository’s own licensing status is accurate, visible, and compatible with proposed use. |  |  | `README.md`; `docs/licensing-and-attribution.md` |
| Third-party dependency licenses and notices are reviewed for the intended distribution. |  |  | `pyproject.toml`; `docs/licensing-and-attribution.md` |
| Rights and restrictions for derived representations, figures, reports, and other outputs are documented. |  |  | `docs/licensing-and-attribution.md`; `docs/reproducibility.md` |
| Commercial use is not assumed; data, model, dependency, and repository terms are assessed for the specific use case. |  |  | `docs/licensing-and-attribution.md`; `README.md` |

## Reviewer declaration

- **Reviewer role/expertise:**
- **Review date:**
- **Review scope (tracks/items examined):**
- **Conflicts, access constraints, or other limitations:**
- **Overall recommendation:** `PASS` / `PASS WITH CONDITIONS` / `CHANGES REQUIRED` / `NO-GO`
- **Recommendation notes and required actions:**

Signing or completing this form records only the stated reviewer’s assessment of the stated scope.
It does not imply institutional endorsement, archaeological confirmation, or completion of review
tracks marked `NOT REVIEWED`.

## Owner decision gate

Completion of this checklist does **not** automatically authorize Phase 5F or any public-interface,
network, upload, deployment, model-execution, or candidate-publication work. Every substantive
`CONCERN` or conditional recommendation must have a documented disposition, including evidence of
the correction or a reasoned acceptance of residual risk. Phase 5F may begin only after the owner
records explicit approval based on the completed review record and confirms that all required
security, privacy, scientific, archaeological, licensing, and data safeguards remain in force.

Until then, external review remains **NOT COMPLETED**, Phase 5E status is unchanged, and
`RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW` remains the controlling RQ1 status.
