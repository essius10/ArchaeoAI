# Phase 5E five-minute reviewer handoff

Status: `READY_FOR_INDEPENDENT_REVIEW — REVIEW NOT COMPLETED`

## What ArchaeoAI claims

ArchaeoAI E001 asks whether terrain-only machine learning can distinguish 128 m × 128 m
LiDAR-derived patches centred on documented, scheduled, surviving single bowl barrows from matched
`unlabelled_background`, and whether the signal survives geographic separation. The bounded answer
remains `RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW`.

## What it does not claim

ArchaeoAI does not claim archaeological discovery, archaeological probability, England-wide
performance, archaeology-free backgrounds, field confirmation, universal model superiority,
institutional endorsement, peer review, publication, or authorization for public model execution.

## Exact snapshot

- Scientific/runtime evidence supplied for review: `2eab2716af01c7cf007b84342058483bfd1414a0`
- Phase 5E-C starting `main`: `8ac77c0c313a2966a0de54210a0e2dfd4f7a43f9`
- The scientific/runtime package originally sent for review remains pinned to the SHA above.
- Review the exact commit in your generated bundle manifest; do not infer that a later commit was
  examined.

## Key evidence and limitations

| Item | Coordinate-safe fact | Boundary |
|---|---|---|
| E001 dataset | 261 documented bowl-barrow patches + 261 matched `unlabelled_background`; n=522 | Background is not a known negative |
| Frozen geographic final | 87.1% balanced accuracy; n=62 in two pre-specified groups | Not England-wide performance |
| Geographic robustness | Random Forest mean 82.3% over five post-hoc folds | Contextual, not a new final test |
| Compact CNN | Mean 70.1% on the same folds | One architecture only; RF retained |
| Independent external test | 84.2%; 95% CI 77.5–90.0%; n=120 across five cells | Test is spent and cannot be tuned on or reinterpreted |
| Class scope | Documented bowl-barrow terrain versus matched unlabelled terrain | No other archaeological class or unknown-terrain claim |

The Random Forest was retained because it outperformed the compact CNN in this bounded comparison,
not because trees are universally superior. The evidence ladder is:

1. `AI_OUTPUT` — terrain-pattern score or prediction;
2. hypothesis/candidate interpretation;
3. human-vetted observation;
4. archaeologist-validated interpretation; and
5. confirmed archaeological evidence.

No new model-ranked candidate reaches levels 3–5. Human review is required before stronger
interpretation.

## AI assistance

The project is owner-directed and materially generative-AI-assisted. OpenAI Codex is explicitly
recorded as contributing to planning, implementation, tests, analysis workflows, debugging,
documentation, manuscript drafting, and privacy/security design. Read the full
[AI assistance and authorship disclosure](AI_ASSISTANCE_AND_AUTHORSHIP_DISCLOSURE.md). AI work and
automated tests are not independent external review.

## Sensitive-location boundary

Precise coordinates, geometries, private terrain, model bytes, row-level predictions, inference
domains, candidate locations, review imagery, and private custody evidence are not public. Do not
put them in issues, review forms, screenshots, or email excerpts. Request a separately authorized
private process if a review genuinely requires them.

## Review tracks

| Track | Start with | Then inspect |
|---|---|---|
| Security/threat | [External-review checklist, Track 1](PHASE_5E_EXTERNAL_REVIEW_CHECKLIST.md) | `SECURITY.md`; Phase 6D loader/runtime; threat model; focused tests |
| Privacy/retention | [External-review checklist, Track 2](PHASE_5E_EXTERNAL_REVIEW_CHECKLIST.md) | privacy lifecycle; portal repository/schema; retention tests |
| Archaeological/scientific | [External-review checklist, Track 3](PHASE_5E_EXTERNAL_REVIEW_CHECKLIST.md) | manuscript; Phase 4D audit; reviewer guide; claims register |
| Licensing/data/model | [External-review checklist, Track 4](PHASE_5E_EXTERNAL_REVIEW_CHECKLIST.md) | licensing audit; exact licensing questions; source/model terms |

The [review package](PHASE_5E_REVIEW_PACKAGE.md) gives exact paths and focused commands. The
[completion gate](PHASE_5E_COMPLETION_GATE.md) states what evidence is still missing.

## How to record the review

1. Build or verify the bundle using `scripts/build_phase5e_review_bundle.py` and its SHA-256
   manifest. This proves content integrity, not reviewer identity.
2. State your stable public attribution, role/expertise, date, exact commit, scope, methodology,
   conflicts, access limits, tools, and whether AI tools assisted your review.
3. Mark each item you examined `PASS`, `CONCERN`, or `NOT REVIEWED`. Do not infer a pass outside your
   expertise or access.
4. Transfer the declaration and findings into one domain-specific copy of
   `templates/phase5e_review.template.json`; validate it with
   `python scripts/validate_phase5e_review.py --review <record.json>`.
5. Record concise findings without sensitive material in the
   [feedback register](FEEDBACK_REGISTER.md). Never post coordinates, private terrain, credentials,
   exploitable details, or private correspondence; use a redacted summary and opaque private
   evidence reference instead.
6. The owner copies substantive findings into the
   [owner disposition register](PHASE_5E_OWNER_DISPOSITION.md), links changes/evidence, and records
   residual limitations.
7. Review completion does not itself authorize Phase 5F, real terrain, public inference,
   deployment, release, model redistribution, or candidate publication.

Your review records a bounded expert assessment. It does not prove archaeological truth, reviewer
identity through hashing, institutional endorsement, legal compliance outside its stated scope, or
the safety of material you did not inspect.
