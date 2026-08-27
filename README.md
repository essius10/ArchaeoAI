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

Phase 2A now provides a **metadata-only feasibility audit** for scheduled single bowl barrows. The
official NHLE title pool and a deterministic 30-entry quality sample support a conditional GO, but
no record is yet an approved E001 label. See the
[E001 feasibility audit](docs/e001-feasibility-audit.md).

The following are **not implemented**:

- raster loading, validation, clipping, tiling, or terrain transformations;
- approved archaeological labels, background sampling, or geographic split generation;
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

Raw, derived, and sensitive data remain excluded from Git. A real manifest must not be created until dataset decision D001 resolves license, provenance, geographic coverage, and heritage-sensitivity questions.

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
- [Candidate questions and recommendation](docs/research-questions.md)
- [Six-month roadmap and first 12 weeks](docs/roadmap.md)
- [Decision log](docs/decision-log.md)
- [Research quality bar](docs/project-quality-bar.md)
- [Claims register](docs/claims-register.md)
- [Initial experiment protocol](experiments/E001_geographic_baseline.md)
- [Environment audit](docs/environment-audit.md)
