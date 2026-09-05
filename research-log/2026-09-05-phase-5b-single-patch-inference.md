# Phase 5B — reusable single-patch inference core

Date: 5 September 2026
Scope: synthetic terrain and inert model plumbing only
Status: `COMPLETE`

## Question I worked on

Can one reusable single-patch path produce exactly the frozen Random Forest input without loading
the private model, processing real terrain, or duplicating scientific transformations?

## What I predicted, and why

I expected exact equivalence to be achievable by wrapping the established Phase 2F feature entry
point. Reimplementing representations or pooling would create unnecessary scientific-drift risk.

## What I did myself

The project owner authorized the synthetic-only Phase 5B scope and preserved the model, terrain,
spent-test, scientific-result, privacy, deployment, and Phase 5C boundaries.

## AI/tool assistance used

OpenAI Codex traced the frozen feature code and protocol, implemented the strict wrapper and model
boundary, created synthetic tests and documentation, and ran local and clean-worktree validation.
It did not read, deserialize, or execute the approved private model or process private terrain.

## Evidence created

- `src/archaeoai/inference_system/single_patch.py`
- `tests/test_phase5b_single_patch_inference.py`
- `docs/architecture/PHASE_5_INFERENCE_ARCHITECTURE.md`
- Phase 5B status, reproducibility, roadmap, claim, and decision updates

## Work completed

Phase 5B added a coordinate-free `TerrainPatch` wrapper and strict validation for the frozen E001
single-patch contract: one 128 × 128 elevation array, one boolean mask, EPSG:27700, 1 m square
resolution, one band, and at most 20% explicitly declared no-data. The wrapper never resizes,
crops, reprojects, interpolates, infers metadata, or repairs unmasked NaN or infinity.

The adapter calls the existing `features_from_elevation` research implementation. Its exact channel
order is normalized elevation, slope, fixed 315°/45° hillshade, and 16 m local relief. Each channel
uses the existing non-overlapping 4 × 4 finite-value mean pool, C-order flattening to 1,024 values,
and channel-order concatenation to a read-only `(4096,)` `float32` vector. The model-facing view is
read-only `(1, 4096)`. No scaler or other transformation follows.

Six deterministic synthetic surfaces—plane, Gaussian-like mound, smooth depression, sinusoidal
terrain, seeded noise, and constant terrain—were compared through the established research entry
point and the reusable wrapper. Every comparison passed bit for bit with `numpy.array_equal`.
Repeated execution remained identical across changed ambient NumPy RNG state.

The model boundary requires an explicit adapter and has no fallback. An obviously test-only inert
double verified the exact matrix and single invocation; its fixed output has zero scientific
meaning. The approved artifact guard accepts only the fixed private path, approved model enum,
configuration digest, and artifact digest. It reads bytes for checksum verification only and does
not deserialize or execute them.

## Boundaries preserved

- The approved private Random Forest was not loaded, deserialized, or executed.
- No model was trained, retrained, tuned, downloaded, substituted, or fabricated.
- No real, private, archaeological, or spent external-test terrain was read or scored.
- No coordinates, source filenames, model files, row-level results, or private metadata were added.
- No scientific metric, threshold, headline result, evidence status, or RQ1 conclusion changed.
- `RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW` remains unchanged.
- Independent scientific/privacy review, label-reliability review, systematic literature work,
  private-data reproduction, licensing, artifact distribution, and operational security remain
  external blockers.

## What surprised me / what failed

The frozen research function was already reusable, so no mathematical refactor was needed. A
first adapter draft could have attached the approved public model identity to an arbitrary adapter
score without first enforcing the private artifact gate. Review separated low-level inert plumbing
from the production result path; the latter now verifies the exact artifact path, hash, model enum,
and configuration digest before any adapter invocation.

## What I now believe, with confidence level

High confidence that the reusable path is bit-for-bit equivalent for the tested synthetic contract
and fails closed on the documented malformed inputs. This is engineering evidence only; it does not
validate model performance or archaeological interpretation.

## Next smallest test

Phase 5C was not started. Any offline CLI, private artifact deserialization, or real input requires
a new, explicit authorization and all documented privacy and artifact gates.
