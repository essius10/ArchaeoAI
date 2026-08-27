# ArchaeoAI

ArchaeoAI is a reproducible research project studying **when terrain-derived representations from public airborne LiDAR can support reliable mapping of already documented archaeological earthworks**. It is a research foundation, not a site-discovery tool.

## Current research question

> For one documented earthwork type in England, how much do terrain representation and spatial validation design affect a model's ability to distinguish known archaeological features from matched background terrain?

Experiment E001 will eventually compare interpretable terrain representations and simple baselines before any deep-learning work. Its primary endpoint is performance on a geographically disjoint holdout, not a random tile split.

## Current implementation status

Phase 1 provides:

- an installable Python package using a `src/` layout;
- strict TOML experiment-configuration loading;
- repository-contained path resolution with escape prevention;
- typed dataset provenance manifests;
- explicit dataset status and heritage-sensitivity classifications;
- automated tests, Ruff checks, and Windows-compatible environment validation.

Phase 2A.5 now provides a coordinate-safe curated-data gate for scheduled single bowl barrows. A
deterministic 360-record official-entry review retained 261 records after geometry, provisional
128 m terrain-coverage, and survey-provenance checks. This moves dataset decision D001 to FINAL GO
for Phase 2B planning. Groups and holdouts remain provisional, 40 records await actual independent
review, and no terrain or model experiment has begun. See the
[Phase 2A.5 gate](docs/e001-phase-2a5-curation-gate.md).

The following are **not implemented**:

- raster loading, validation, clipping, tiling, or terrain transformations;
- background sampling or a finalized buffered geographic split;
- baseline models, metrics, visualizations, or an executable E001 run;
- any real dataset, archaeological coordinate, prediction, or result.

## Python policy and setup

The reference/reproducibility runtime is CPython 3.12. Phase 1 supports CPython `>=3.12,<3.15`; local development has been verified on CPython 3.14.7.

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

No runtime third-party dependencies are installed for Phase 1. The `dev` extra contains only pytest and Ruff.

Verify the environment and repository:

```powershell
.\scripts\doctor.ps1
.\scripts\validate_project.ps1
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
```

Reproduce the coordinate-safe live NHLE metadata audit:

```powershell
.\.venv\Scripts\python.exe .\scripts\audit_nhle_bowl_barrows.py
```

This command queries only official designation metadata and writes aggregate outputs without exact
coordinates. It does not download terrain or create final archaeological labels.

Reproduce the Phase 2A.5 queue or rerun its metadata gate:

```powershell
.\.venv\Scripts\python.exe .\scripts\curate_e001_labels.py --print-queue
.\.venv\Scripts\python.exe .\scripts\curate_e001_labels.py --terrain-workers 2
```

The second command needs the ignored full-entry review cache described in `data/README.md`. It
queries designation and terrain metadata only; it does not download LiDAR.

## Configuration

`configs/e001.example.toml` is a non-data example of the E001 configuration contract. It records the experiment ID, deterministic seed, safe repository-relative paths, random and geographic split settings, and placeholder preprocessing parameters.

Load it from Python with:

```python
from archaeoai.config import load_experiment_config

config = load_experiment_config("configs/e001.example.toml")
```

Configured paths must remain inside the repository. Absolute paths and parent-directory escapes are rejected during Phase 1. This policy can be revisited explicitly if externally stored datasets become necessary.

## Dataset manifests

`data/manifests/example-dataset.toml` demonstrates the provenance schema. It is intentionally fictional, uses the reserved `example.invalid` domain, and has `template` status. It does not represent an acquired dataset.

Manifests record dataset identity, provider, URL, license, CRS, resolution, geographic description, expected local path, optional dates, optional SHA-256 checksum, acquisition status, and sensitivity classification. `acquired` and `verified` manifests require an access date and checksum.

Raw, derived, and sensitive data remain excluded from Git. D001 now approves the source strategy;
Phase 2B must create a real manifest only when a bounded dataset is actually acquired and verified.

## Repository structure

```text
configs/                 Example experiment configuration
data/manifests/          Tracked provenance metadata, never bulk data
docs/                    Research governance and decisions
experiments/             E001 scientific protocol
src/archaeoai/           Phase 1 Python package
tests/                   Data-free automated tests
scripts/                 Windows environment and project checks
research-log/            Student research-session record
outputs/                 Reviewed small reports; generated E001 runs are ignored
```

## Responsible use

This repository must not publish precise coordinates for unprotected or sensitive sites, nor make claims of archaeological discovery. Predictions are terrain-pattern hypotheses only; they require independent archaeological assessment. “Not recorded as archaeology” must not be treated automatically as a verified negative.

## Research documentation

- [Research charter](docs/research-charter.md)
- [Literature and novelty audit](docs/literature-novelty-audit.md)
- [Dataset decision record](docs/dataset-decision-record.md)
- [E001 Phase 2A feasibility audit](docs/e001-feasibility-audit.md)
- [E001 Phase 2A.5 curation and terrain gate](docs/e001-phase-2a5-curation-gate.md)
- [Candidate questions and recommendation](docs/research-questions.md)
- [Six-month roadmap and first 12 weeks](docs/roadmap.md)
- [Decision log](docs/decision-log.md)
- [Research quality bar](docs/project-quality-bar.md)
- [Claims register](docs/claims-register.md)
- [Initial experiment protocol](experiments/E001_geographic_baseline.md)
- [Environment audit](docs/environment-audit.md)
