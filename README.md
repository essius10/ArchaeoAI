# ArchaeoAI

ArchaeoAI is a reproducible research project studying **when terrain-derived representations from public airborne LiDAR can support reliable mapping of already documented archaeological earthworks**. It is not a site-discovery tool.

## Current research question

> For one documented earthwork type in England, how much do terrain representation and spatial validation design affect a model's ability to distinguish known archaeological features from matched background terrain?

The first study will compare interpretable terrain representations and simple baselines before any deep-learning work. Its primary endpoint is performance on a geographically disjoint holdout, not a random tile split.

## Safety

This repository must not publish precise coordinates for unprotected or sensitive sites, nor make claims of archaeological discovery. Predictions are terrain-pattern hypotheses only; they require independent archaeological assessment.

## Start here

- [Research charter](docs/research-charter.md)
- [Literature and novelty audit](docs/literature-novelty-audit.md)
- [Dataset decision record](docs/dataset-decision-record.md)
- [Candidate questions and recommendation](docs/research-questions.md)
- [Six-month roadmap and first 12 weeks](docs/roadmap.md)
- [Decision log](docs/decision-log.md)
- [Research quality bar](docs/project-quality-bar.md)
- [Claims register](docs/claims-register.md)
- [Initial experiment protocol](experiments/E001_geographic_baseline.md)
- [Environment audit](docs/environment-audit.md)

## Status

Phase 0–4 (environment, question discovery, literature/novelty, and data selection) are in progress. Data must not be downloaded or modelled until the label license, sensitivity policy, and geographic split plan are confirmed.
