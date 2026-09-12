# ArchaeoAI External Review

This directory contains materials for independent review of ArchaeoAI’s research and bounded
inference work. No document here constitutes independent approval by itself. Phase 5E remains
incomplete until actual external review occurs and its substantive findings are resolved.

## Start here

1. [Five-minute reviewer handoff](PHASE_5E_REVIEWER_HANDOFF.md) — bounded claims, results, privacy,
   AI-assistance summary, and track routing.
2. [Phase 5E external-review checklist](PHASE_5E_EXTERNAL_REVIEW_CHECKLIST.md) — structured
   security, privacy, archaeological/scientific-workflow, and licensing/data/model review tracks.
3. [Phase 5E review package](PHASE_5E_REVIEW_PACKAGE.md) — current Phase 6C/6D evidence map,
   focused commands, expertise needs, limitations, and intentionally private material.
4. [AI assistance and authorship disclosure](AI_ASSISTANCE_AND_AUTHORSHIP_DISCLOSURE.md) — candid
   human, expert, AI, tool, verification, and responsibility roles.
5. [Reviewer guide](REVIEWER_GUIDE.md) — overall orientation, evidence boundaries, terminology,
   and questions for reviewers.
6. [Current status](../CURRENT_STATUS.md) — current project state, results boundary, and next gate.
7. [Evidence submission directory](evidence/README.md) — machine-validatable review records and
   sensitive-reporting boundary.

## Supporting review material

- [Phase 4D RQ1 audit](PHASE_4D_RQ1_AUDIT.md) — bounded RQ1 conclusion and controlling status.
- [Readiness audit](READINESS_AUDIT.md) — independent-review readiness findings and limits.
- [Clean-environment reproduction](CLEAN_ENVIRONMENT_REPRODUCTION.md) — public-clone reproduction record.
- [Feedback register](FEEDBACK_REGISTER.md) — mechanism for recording and resolving review findings.
- [Owner disposition register](PHASE_5E_OWNER_DISPOSITION.md) — evidence-backed treatment of actual
  substantive findings; currently empty and pending.
- [Completion gate](PHASE_5E_COMPLETION_GATE.md) — single authoritative rule for truthful closure.
- [Licensing questions](PHASE_5E_LICENSING_QUESTIONS.md) — exact qualified-review questions; not
  legal advice.
- [External-review note](EXTERNAL_REVIEW_NOTE.md) — scope and status of external-review activity.
- [Research review checklist](REVIEW_CHECKLIST.md) — discipline-specific E001 review prompts.
- [Review execution policy](phase5e-review-policy.json) — canonical four-domain evidence and
  deterministic bundle allowlist.

## Current gate

`RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW`

Phase 5A–5D and Phase 6C–6D engineering are complete. Phase 5E external review is **NOT COMPLETED**,
and Phase 5F or other public-interface work is **NOT AUTHORIZED**. No archaeological discovery claim
follows from the engineering work, model output, or review materials.

Phase 5E-B classifies internal readiness as `READY` and independent review completion as `PENDING`.
It does not convert internal or AI-assisted checks into external review.

Phase 5E-C makes that review operational. Generate an exact, ignored review bundle only from a
clean committed tree, verify its manifest, and inspect the current fail-closed status with:

```powershell
python scripts/build_phase5e_review_bundle.py --commit HEAD
python scripts/validate_phase5e_review.py --verify-bundle outputs/review/phase5e-<short-sha>
python scripts/validate_phase5e_review.py
```

The generated SHA-256 manifest binds content; it does not establish reviewer identity or approval.

## Reviewer workflow

1. Read the [five-minute handoff](PHASE_5E_REVIEWER_HANDOFF.md) and
   [current status](../CURRENT_STATUS.md).
2. Read the [reviewer guide](REVIEWER_GUIDE.md) and
   [AI disclosure](AI_ASSISTANCE_AND_AUTHORSHIP_DISCLOSURE.md).
3. Build or verify the version-bound bundle and complete the appropriate track or tracks in the
   [Phase 5E checklist](PHASE_5E_EXTERNAL_REVIEW_CHECKLIST.md).
4. Create one completed JSON record per domain from the
   [review template](templates/phase5e_review.template.json), validate it, and record a public-safe
   summary in the [feedback register](FEEDBACK_REGISTER.md).
5. The owner documents substantive findings and resolutions in the
   [disposition register](PHASE_5E_OWNER_DISPOSITION.md).
6. Apply the [completion gate](PHASE_5E_COMPLETION_GATE.md); a separate explicit decision is
   required before any later interface work.
