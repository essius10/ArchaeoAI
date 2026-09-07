# Phase 6D approved private model runtime

Phase 6D connects the frozen E001 Random Forest to the local portal while retaining a deliberately
narrow input boundary: the real model can score only deterministic mathematical terrain generated
inside the application. Real terrain, uploads, coordinates, remote inference, training, tuning, and
archaeological determination remain out of scope.

## Approved identity

- Model: `E001_FROZEN_RANDOM_FOREST` (`sklearn.ensemble.RandomForestClassifier`)
- Configuration SHA-256: `20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4`
- Private artifact SHA-256: `50f7968069ecaa1e0016f37be6356531ab3f26802c806efb5dc8fb2e295a503f`
- Learned-state SHA-256: `e3b0c072f437e889f09a2a2cf5a37f19b2f483eb5188e102b132a89ee76d1939`
- Private ignored location: `data/private/e001/inference/e001_phase2f_random_forest.pkl`

The path is fixed in the inference system. It is not accepted from the CLI, browser, or API.

## Runtime architecture

The owner explicitly authorizes the runtime at server startup. The loader resolves the repository
root and exact private location, confirms private containment and Git-ignore protection, verifies the
artifact digest before pickle deserialization, then validates the exact estimator class, learned
state, and frozen configuration identity. Any mismatch stops startup. It never searches for another
model, rebuilds one, or falls back to the demonstration scorer.

For each approved run, the portal creates a deterministic 128 × 128 mathematical elevation surface,
uses the canonical four-representation Phase 5 transform and immutable 4,096-value `float32` model
input, and invokes the frozen Random Forest probability-scoring path. Features are discarded rather
than stored. Results record `AI_OUTPUT`, `APPROVED_PRIVATE_RANDOM_FOREST`, and
`PERFORMED_APPROVED_PRIVATE_MODEL` before entering the human-review workflow.

Pickle can execute code during deserialization. This implementation therefore permits only the
single private, hash-bound artifact. Possession of repository or browser access does not authorize a
different pickle.

## Safe interpretation

The output is a **bounded terrain-pattern similarity score from the frozen E001 model**. It is not an
archaeological probability, archaeological confidence, discovery probability, or determination of
presence or absence. Synthetic input and required human review remain visible in the UI, API-safe
provenance, audit trail, and report.

## Launch

Default synthetic demonstration, including Web Preview:

```powershell
archaeoai portal --demo --reset --host 0.0.0.0
```

Real frozen model on synthetic terrain, local/private only:

```powershell
archaeoai portal --demo --approved-model-runtime --reset
```

Open the latter at `http://127.0.0.1:8000`. Approved mode rejects `--host 0.0.0.0`; the default remains
`127.0.0.1`.

## Expected closed failures

Startup stops with a fixed safe message if the private artifact is missing, outside the approved
private boundary, not ignored, changed, not the exact classifier type, or different in learned state.
An API request cannot authorize a runtime that the server did not authorize at startup. Runtime and
request errors do not reveal filesystem paths, pickle details, features, or model internals.

## Still unauthorized

This phase does not complete Phase 5E independent review, authorize Phase 5F, establish pilot
readiness, or validate a commercial product. Real/customer terrain, file upload, public or remote
model execution, candidate-location publication, and archaeological discovery claims remain
prohibited. A later owner-approved gate must resolve external review findings before any broader
interface or real-data work.
