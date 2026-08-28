# Contributing to ArchaeoAI

Thank you for considering a contribution. ArchaeoAI is an early-stage, student-led research project,
so scientific validity and responsible data handling matter as much as code quality.

## Useful contribution areas

- reproducibility and environment checks;
- geospatial processing and CRS validation;
- spatial statistics and leakage-resistant evaluation;
- archaeological methodology and terminology;
- interpretable machine-learning baselines;
- tests, documentation, and accessibility.

Large method changes should begin with a research/methodology issue. Please do not implement Phase
2B terrain acquisition or modeling unless that work has been explicitly approved and scoped.

## Local setup

The reference runtime is CPython 3.12; supported development versions are `>=3.12,<3.15`.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\scripts\doctor.ps1
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\scripts\validate_project.ps1
```

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

