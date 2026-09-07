# Phase 6C commercial MVP portal

## Status

Phase 6C implements a functional, local-only professional workflow demonstration. It is not a
production deployment, an inference service, a customer pilot, or evidence that external review has
occurred. Phase 5E remains incomplete and Phase 5F remains unauthorized.

## What was built

The portal provides a browser-based workspace for:

- creating project-scoped synthetic demonstrations;
- recording synthetic-only authorization and reviewer acknowledgements;
- preparing deterministic mathematical terrain through the existing Phase 5 validation,
  representation, pooling, and 4,096-feature path;
- displaying bounded terrain-similarity demonstration hypotheses;
- recording separately attributable human observations;
- inspecting evidence and audit timelines;
- generating a coordinate-safe, limitations-first report preview;
- changing declared retention and cascade-deleting local demo records.

The user interface includes Overview, Projects, Review Queue, Reports, Audit, and Settings areas. It
is responsive, keyboard-operable, and uses browser print styling for local report export.

## Architecture

The optional `portal` dependency group adds FastAPI and Uvicorn. FastAPI serves a semantic
HTML/CSS/vanilla-JavaScript single-page interface and strict typed JSON endpoints. SQLite stores
minimal workflow state under `data/private/portal/`, which is ignored by Git. The schema contains no
coordinate, raster, filesystem-path, feature-vector, or model-artifact fields.

`SyntheticDemoRuntime` generates bounded 128 × 128 mathematical surfaces. It invokes the canonical
Phase 5 single-patch transformation (EPSG:27700, 1 m, four frozen terrain representations, 4 × 4
pooling, 4,096 float32 features), verifies the contract, and discards the surface and feature values.
Its deterministic interface scores are not model outputs or archaeological probabilities.

`ScreeningRuntime` defines the replaceable runtime interface. `DisabledApprovedModelRuntime` is the
only approved-model implementation in Phase 6C and fails closed with
`APPROVED_MODEL_RUNTIME_NOT_AUTHORIZED` before artifact discovery, loading, deserialization, or
execution. A later phase may connect an approved, hash-bound adapter only after the relevant owner,
security, privacy, licensing, and review gates.

## Install and run

From the repository root in an activated virtual environment:

```powershell
python -m pip install -e ".[portal]"
archaeoai portal --demo --reset
```

Open `http://127.0.0.1:8000`. Subsequent launches may omit `--reset` to retain the local demo state.
See [PORTAL_RUNBOOK.md](PORTAL_RUNBOOK.md) for operator details.

## Demonstration workflow

1. Enter the local demo workspace.
2. Create a project and accept both synthetic-data boundaries.
3. Record the demonstration authorization.
4. Select and run a mathematical terrain scenario.
5. Inspect the terrain-similarity hypotheses and priority filters.
6. Record a human-vetted observation in the review queue.
7. Inspect the separately attributed evidence and audit records.
8. Generate and print the limitations-first report.
9. Change retention or delete the local demonstration project.

## Evidence and privacy boundaries

Machine-created records are limited to `AI_OUTPUT` or `AI_HYPOTHESIS`. A named human action is
required for `HUMAN_VETTED_OBSERVATION`. This demo role cannot create
`ARCHAEOLOGIST_VALIDATED_INTERPRETATION`, and the portal cannot create
`CONFIRMED_ARCHAEOLOGICAL_EVIDENCE`.

The portal accepts no uploads and exposes no anonymous inference route. It has no analytics,
telemetry, cloud storage, map provider, or normal-operation network dependency. It binds to
`127.0.0.1`, applies same-origin mutation checks and security headers, validates opaque identifiers,
rejects arbitrary metadata, and returns controlled errors. These are sensible demonstration
safeguards, not a claim of production security.

## Limitations and remaining gates

- No real terrain, archaeological coordinates, or candidate locations are accepted or shown.
- No approved private Random Forest is located, loaded, deserialized, or executed.
- Demonstration scores are deterministic UI values only.
- Local demo identity is not production authentication or enterprise authorization.
- Reports are not professional archaeological assessments or sign-off.
- No customer validation, pilot readiness, commercial performance, or archaeological discovery is
  claimed.
- Independent Phase 5E security, privacy, archaeological-workflow, and licensing review remains
  incomplete.
- Phase 5F/public-interface authorization and any production deployment decision remain separate
  owner gates.

The research conclusion and all frozen scientific artifacts remain unchanged.
