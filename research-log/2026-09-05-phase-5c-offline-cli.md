# 2026-09-05 — Phase 5C offline single-patch CLI

## Question I worked on

Can the bit-exact Phase 5B single-patch path be exposed as a useful offline command-line interface
without exposing private spatial metadata or creating any route to unapproved model execution?

## What I predicted, and why

I expected the standard library plus the existing Rasterio dependency to be sufficient. The safest
surface would inspect one strictly canonical GeoTIFF, report only the feature contract, and make
`infer` an explicit fail-closed boundary rather than a fake or substitute scoring path.

## What I did myself

The project owner set the Phase 5C scope and prohibited real terrain, approved-model execution,
spent-test reuse, training, tuning, API/website work, deployment, and scientific-result changes.
The owner also required synthetic-only equivalence, strict output privacy, and a review PR rather
than a merge.

## AI/tool assistance used

OpenAI Codex inspected the merged Phase 5A/5B contracts, implemented the package entry point and
GeoTIFF boundary, wrote temporary synthetic-raster tests, tightened output allowlists, updated the
engineering documentation, and ran repository verification. It did not access, load, deserialize,
or execute the approved private model and did not read real or spent-test terrain.

## Evidence created (paths, figures, outputs)

- `src/archaeoai/cli.py`
- `src/archaeoai/__main__.py`
- `tests/test_phase5c_offline_cli.py`
- Phase 5C updates in the README, architecture, status, roadmap, reproducibility, security, claims,
  decision, and validation documentation

## Work completed

The CLI supports `inspect`, `features`, and a deliberately disabled `infer` boundary through both
`python -m archaeoai` and the installed `archaeoai` command. It accepts only a one-band GeoTIFF with
128 × 128 cells, EPSG:27700, 1 m square resolution, numeric terrain, and the frozen finite/no-data
rules. It does not crop, resize, resample, reproject, fill, or silently repair inputs.

`inspect` and `features` emit fixed human or deterministic JSON allowlists. Neither mode emits a
filename, full path, coordinate, bounds, transform, arbitrary raster tag, feature value, private
model location, or model score. A temporary synthetic GeoTIFF produced all 4,096 `float32` features
bit for bit identically to direct Phase 5B invocation under `numpy.array_equal`.

`infer` has no dummy, mock, heuristic, download, retraining, or fallback option. A missing approved
artifact exits explicitly, and even a test-injected successful integrity gate stops because Phase
5C does not authorize model execution.

## What surprised me / what failed

The first focused test run had four failures caused by a test-harness typo: assertions read a
nonexistent `stderr` capture attribute instead of pytest's `err` attribute. The product behavior was
unchanged; correcting the assertions made all four safety cases pass. A later review also tightened
the reader from suffix checking alone to explicit GeoTIFF-driver enforcement.

## What I now believe, with confidence level

High confidence that the tested CLI is a narrow, deterministic, coordinate-safe wrapper around the
Phase 5B feature path. This is engineering evidence from synthetic fixtures only. It is not evidence
that the private model is distributable or executable, that real terrain is safe to process, or that
ArchaeoAI discovers archaeology.

## Next smallest test

Phase 5D was not started. A future phase should address bounded private batch orchestration,
resource limits, cleanup, retention, auditability, and abuse controls before any real input or model
execution is authorized. Independent security, privacy, licensing, and archaeological-workflow
review remain separate gates.
