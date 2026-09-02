# E001 reproducibility guide

## Scope

This guide separates reproducibility of public, coordinate-safe evidence from reconstruction of
the private spatial data layer. It does not authorize a new model run, external evaluation, terrain
download, or public release. The Phase 3C external test is spent.

**Current classification: PARTIALLY REPRODUCIBLE — PRIVATE DATA REQUIRED FOR SPECIFIC STEPS.** See
the [clean-environment audit](review/CLEAN_ENVIRONMENT_REPRODUCTION.md) for the tested boundary.

## Environment

The reference runtime is CPython 3.12. Development is supported on CPython `>=3.12,<3.15`.

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\scripts\doctor.ps1
.\scripts\validate_project.ps1
.\.venv\Scripts\python.exe -m pip check
```

### Linux and macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python scripts/doctor.py
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m pip check
```

The Python doctor is coordinate-free and does not read private terrain, model files, or local
research caches. Pass `--json` for a machine-readable report. The PowerShell project validator is a
separate, deeper audit of frozen evidence and remains Windows-specific.

GitHub Actions repeats the platform-independent quality checks on Linux with CPython 3.12. Exact
package versions used for frozen model phases are recorded in their result artifacts. The local
Phase 4B verification environment may be newer within the supported range; it does not regenerate
scientific results.

On Windows, use a short checkout path if environment creation fails with a maximum-path error in a
dependency's packaged files. A Phase 4C clean install succeeded after moving the temporary clone to
a short path.

## Frozen configurations and evidence hierarchy

The project deliberately separates decisions from results:

1. `configs/e001-phase-2d-a-preregistered.json` freezes development selection.
2. `outputs/modelling/e001_primary_baseline_config.json` freezes the selected Random Forest.
3. `configs/e001-phase-2d-b-final-protocol.json` authorizes one-way final evaluation.
4. `configs/e001-phase-2e-a-robustness-protocol.json` and the fold manifest bind post-hoc
   robustness.
5. `outputs/deep_learning/e001_cnn_protocol.json` freezes the compact CNN before training.
6. `configs/e001-phase-3a-external-validation.json` and the Phase 3B-R1 amendment freeze the
   independent external design before construction and scoring.
7. `outputs/external_validation/e001_phase3c_external_evaluation.json` is the spent external result.
8. `outputs/external_validation/e001_phase4a_error_analysis.json` is explicitly exploratory.
9. `outputs/manuscript/e001_manuscript_evidence.json` binds the manuscript to these artifacts.

Do not regenerate result JSON merely to reproduce it. Validation should confirm the frozen hashes
and metrics. Any genuinely new model generation must use new filenames, protocols, and independent
evaluation data.

## Dataset methodology

E001 contains 261 curated `positive_bowl_barrow` and 261 matched `unlabelled_background`
observations. Positive curation, terrain acquisition, background construction, and split freezing
are documented in the Phase 2A.5–2C reports. Backgrounds are uncertain terrain, never confirmed
archaeology-free negatives.

Raw data reconstruction requires lawful access to the Historic England and Environment Agency
sources, the documented snapshot/access dates, and execution of controlled scripts that write only
to ignored private storage. Precise coordinates and raw or processed terrain must not be committed.
Source availability and service behavior may change, so a later full rerun must record a new source
snapshot rather than pretending byte-for-byte source stability.

## Geographic leakage controls

The public modelling index contains labels and safe grouping identifiers but no exact coordinates.
Private audits enforce positive/background buffers, background spacing, terrain-window overlap,
content-digest uniqueness, matched-group integrity, and complete geographic-block assignments.
Both random and geographic split manifests are SHA-256 bound. The five robustness folds preserve
matched and overlap units and have frozen assignment SHA-256
`825eb1088a53f764f991bf6bb22f2c9fe6eeb868916a5abab92012eed85d90ab`.

## Result reproduction

Public verification validates exact stored metrics, scientific state, and immutable hashes without
loading the private model or prediction vector. Where private evidence is present locally, tests
also reproduce the Phase 3C metrics from the frozen 120-row score vector. They do not call the
model again. The expected bindings include:

| Artifact | SHA-256 |
|---|---|
| Primary RF configuration | `20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4` |
| Full-fit RF state | `e3b0c072f437e889f09a2a2cf5a37f19b2f483eb5188e102b132a89ee76d1939` |
| External dataset | `17eeb9366e02ce2acddcfaf3324a9558a439a5655139859e6f9fb0707f69057c` |
| External prediction vector | `bd4a14794132b57f19b8345f70f2f1259f5d385a06ee2328d02bcab9d8b91ca7` |
| Phase 3C result | `2654932891aa48f4e41ea7cfa8a0f72d5fbbb38a6c2741ce82685fc84edb432b` |
| Phase 4A aggregate | `209559c7759c6641d6ac7afeb47bd9a64f3f9581c6a3f9b5d8a5e024825a7276` |

## Figures

Manuscript figures are existing coordinate-safe SVG artifacts. The manuscript evidence manifest
records both their paths and repository-normalized hashes so Windows CRLF and Linux LF checkouts
validate strictly without accepting changed figure content. No sensitive map is part of the
package.

## Provenance and licensing

The curation and data manifests record provider, dataset identity, access date, CRS, nominal
resolution, licence category, and processing version. Historic England and Environment Agency
attribution requirements are summarized in `docs/licensing-and-attribution.md`. The repository
currently has no repository-wide licence. A future release must resolve ownership and source-term
boundaries before promising reuse or redistribution.

## Privacy boundary

Public: source code, tests, protocols, safe indices, aggregate results, coarse group summaries,
manuscript, and coordinate-safe figures.

Private/ignored: exact coordinates, geometries, raw terrain, processed NPZ files, private
manifests, model/checkpoint files, row-level external predictions, candidate scores, blinded review
media, and exact inference domains.

Successful public checks do not prove that private files are publishable. Release review must
inspect the tracked Git tree, not merely the working directory.

## Known reproducibility limitations

- no independent researcher has completed a clean full-data rerun;
- source services and inventory snapshots can change;
- private data cannot be audited from a public checkout;
- CPython 3.12 is CI-tested, while the original local model phases used recorded CPython 3.14.7
  environments;
- external Phase 3 scores cannot be regenerated by rerunning the model because the test is spent;
- a verified manuscript package is not equivalent to peer review or archival publication.
