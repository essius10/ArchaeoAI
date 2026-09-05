# 2026-09-05 — Phase 5D bounded batch feature orchestration

## Question I worked on

Can the approved single-patch validation and feature pathway process a small local collection in a
deterministic, resource-bounded, no-retention workflow without enabling model execution or exposing
spatial metadata?

## What I predicted, and why

I expected a sequential JSON-manifest layer to be safer and more reproducible than directory
enumeration or concurrency. The existing Phase 5C reader and Phase 5B transform already provided
the scientific path, so Phase 5D should add orchestration controls rather than new terrain or model
logic.

## What I did myself

The project owner authorized Phase 5D only after final Phase 5C review and merge. The owner defined
the no-model, synthetic-only, aggregate-reporting, cleanup, privacy, and scientific boundaries and
required an unmerged review pull request.

## AI/tool assistance used

OpenAI Codex verified and merged the exact green Phase 5C pull request, waited for successful
post-merge CI, audited Phase 2F and Phase 5 components, implemented the strict batch layer and tests,
updated documentation, and ran clean-worktree verification. It did not load or execute the approved
private Random Forest, access real terrain or the spent external test, train or tune a model, or
create a scientific score.

## Evidence created (paths, figures, outputs)

- `src/archaeoai/inference_system/geotiff.py`
- `src/archaeoai/inference_system/batch.py`
- `configs/phase5d-batch.example.json`
- `tests/test_phase5d_bounded_batch.py`
- Phase 5D updates to the CLI, architecture, status, roadmap, reproducibility, security, claims,
  decision, and validation documentation

## Work completed

The new `batch-features` command admits one strict JSON manifest. It accepts at most 64 items with
opaque `item-0001`-style IDs and relative POSIX GeoTIFF references contained beneath the manifest
directory. The manifest is capped at 64 KiB, each file at 2 MiB, and cumulative input at 16 MiB.
Absolute or escaping paths, symbolic links, extra or duplicate JSON fields, invalid IDs, duplicate
IDs, duplicate resolved references, and byte-identical inputs fail before feature processing.

Admitted items are sorted by ID and processed sequentially. Each file's size and digest are rechecked
before the shared Phase 5C GeoTIFF reader and Phase 5B transform run. Controlled invalid rasters are
recorded and the remaining admitted items continue; admission or unexpected internal failures stop
the batch safely. Five generated mathematical surfaces matched direct Phase 5B feature arrays bit
for bit under `numpy.array_equal`.

The human report is aggregate only. JSON adds bounded opaque per-item operational statuses but no
path, coordinate, bounds, transform, tag, feature value, timing, model location, or score. There is
no model, worker, retention, cache, output, or test-double CLI option. Inputs are read in place, only
one feature vector is held at a time, and the implementation creates no temporary directory, copy,
cache, archive, output artifact, debug dump, or telemetry record.

## What surprised me / what failed

The existing Phase 2F code contains valuable ranking and spatial-deduplication logic, but it is bound
to a private domain, candidate receipts, and real-model research semantics. Reusing that runner would
have expanded Phase 5D improperly. The correct reusable seam was smaller: extract the Phase 5C
GeoTIFF reader from the CLI module, then combine it with the unchanged Phase 5B feature transform.

On Windows, the direct symlink-creation red-team test may skip when the account lacks symlink
privilege; the same code path remains testable on GitHub's Linux runner. No product defect required
loosening a boundary.

## What I now believe, with confidence level

High confidence that the synthetic-tested orchestration is deterministic, bounded, and
coordinate-safe for its exact contract. This is not evidence that real terrain processing, private
model execution, archaeological-risk assessment, discovery, public deployment, or commercial use
is authorized or validated.

## Next smallest test

Do not begin implementation automatically. Phase 5E requires independent security and privacy
review, archaeological-workflow and terminology review, model/data/licensing review, and a written
decision on whether any private runtime test or later public interface is acceptable.
