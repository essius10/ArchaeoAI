# 2026-09-05 — Phase 5A inference-system architecture

## Question I worked on

What is the smallest responsible architecture that can reuse the completed E001 inference research
without implying that the repository is a public archaeological discovery system?

## What I predicted, and why

I expected the research code to be substantially reusable but not publicly inference-ready. Phase
2F had already completed one controlled private run, while its approved model and inputs were
deliberately kept out of Git and no supported CLI or API had been built.

## What I did myself

The project owner authorized architecture and contract preparation only and preserved the Phase 4D
scientific, privacy, spent-test, and release boundaries.

## AI/tool assistance used

OpenAI Codex inspected tracked research code, protocols, configuration, documentation, tests, Git
state, and coordinate-safe receipts. It checked only the availability, ignored status, size, and
SHA-256 match of the approved private model file; it did not deserialize or execute it. Codex
drafted the architecture, implemented contract-only safeguards, and ran repository validation.

## Evidence created

- `docs/architecture/PHASE_5_INFERENCE_ARCHITECTURE.md`
- `src/archaeoai/inference_system/` input, evidence, result, and artifact contracts
- `tests/test_inference_contracts.py`
- status, roadmap, claims-register, and decision-log updates

## What surprised me / what failed

The core Phase 2F logic was already package-level and tested, so wholesale refactoring was not
justified. The decisive limitation is distribution: the exact approved model is private and absent
from public clones, and the executable workflow remains research-specific.

## What I now believe, with confidence level

High confidence in classification `INFERENCE_CODE_READY_MODEL_ARTIFACT_UNAVAILABLE`. An authorized
local environment can use the existing hash-bound artifact without retraining, but a public clone
cannot and must fail explicitly. Automatic output must remain at `AI_OUTPUT` or `AI_HYPOTHESIS`.

## Next smallest test

Only after separate Phase 5B approval, connect one synthetic 128 × 128 terrain patch to the frozen
preprocessing adapter and an inert model double. Do not use real terrain or execute the private RF
until a later explicit gate.
