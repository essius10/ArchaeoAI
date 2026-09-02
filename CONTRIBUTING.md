# Contributing to ArchaeoAI

Thank you for considering a contribution. ArchaeoAI is an early-stage, student-led research project,
so scientific validity and responsible data handling matter as much as code quality.

## Useful contribution areas

- reproducibility and environment checks;
- geospatial processing and CRS validation;
- spatial statistics and leakage-resistant evaluation;
- archaeological methodology and terminology;
- interpretable machine-learning baselines;
- aggregate visualization and accessibility;
- synthetic terrain examples and inference benchmarks;
- tests and documentation.

See [contribution opportunities](docs/contribution-opportunities.md) for five useful, coordinate-safe
starting points. Large method changes should begin with a research/methodology issue. Do not begin a
new research, training, terrain-acquisition, or inference phase unless it has been explicitly
approved and scoped.

## New-contributor workflow

1. Choose a small issue or discuss the proposed scope before substantial work.
2. Use synthetic or clearly fictional data for code and documentation examples.
3. Create a focused branch and keep unrelated research artifacts unchanged.
4. Run the public quality checks below.
5. Open a pull request using the repository template and describe research/privacy impact.

## Local setup

The reference runtime is CPython 3.12; supported development versions are `>=3.12,<3.15`.

### Windows (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\scripts\doctor.ps1
.\scripts\validate_project.ps1
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
```

`scripts/doctor.py` is a data-free cross-platform check for the supported Python runtime, required
packages, EPSG:27700, GDAL/PROJ, PyTorch, Git, and dependency consistency. Use `--json` when a
machine-readable report is useful. The full `validate_project.ps1` evidence audit remains Windows
PowerShell-specific.

The hosted CI runs installation, pytest, Ruff lint, and Ruff formatting on Python 3.12 without
private terrain, coordinates, CUDA, or a GPU. The doctor and full project validator are additional
local checks because they inspect the configured research environment and local evidence state.

## Research integrity

- Separate verified observations, estimates, assumptions, and future plans.
- Do not describe a title match, model output, or undocumented location as an archaeological site.
- Do not report a random-split result without the planned geographic comparison and its limitations.
- Add or update evidence before making a public-facing claim; follow the
  [claims register](docs/claims-register.md).
- Document failures and material AI/tool assistance in the research log.
- Prefer small, reviewable changes with tests for deterministic logic.

## Data and coordinate safety

Never include these in an issue, pull request, test fixture, screenshot, or tracked file:

- sensitive or permission-restricted archaeological coordinates;
- raw NHLE polygons or machine-ready coordinate tables;
- locations of unreviewed potential sites or future model predictions;
- restricted datasets or data whose redistribution terms are unclear;
- credentials, tokens, private URLs, or local environment files.

Use fictional values for tests. Exact data needed for approved local processing belongs only in an
ignored controlled-data location such as `data/private/`. See [SECURITY.md](SECURITY.md) before
reporting an accidental exposure.

## Pull-request checklist

- [ ] The change is within the currently approved research phase.
- [ ] Claims are no stronger than their linked evidence.
- [ ] Tests cover new deterministic or validation behavior.
- [ ] pytest, Ruff lint, Ruff format check, the environment doctor, and project validation pass.
- [ ] No sensitive coordinates, secrets, raw spatial exports, or large datasets are tracked.
- [ ] Documentation and the research log are updated when the scientific method or evidence changes.
- [ ] Third-party material has documented reuse terms and attribution.

By contributing, you acknowledge that the repository does not yet declare an open-source licence.
Discuss substantial contributions with the maintainer before investing significant work; see the
[licensing audit](docs/licensing-and-attribution.md).
