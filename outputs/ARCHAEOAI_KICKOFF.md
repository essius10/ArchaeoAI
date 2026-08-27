# ARCHAEOAI kickoff — 27 August 2026

## Recommendation

Do **not** build a generic LiDAR archaeology detector. Start with a reproducible study of whether terrain representation and spatial validation design change performance when mapping one class of *already documented*, non-sensitive English earthworks.

The central test is whether random patch splits exaggerate performance compared with an untouched geographic holdout. Classical, interpretable baselines come before deep learning.

## Bootstrap completed

- research charter and safety boundary;
- preliminary literature/novelty audit;
- ranked candidate research questions and recommendation;
- data/label decision record and sensitivity criteria;
- preregistered E001 experiment protocol;
- six-month architecture plus a concrete 12-week/Week-1 plan;
- four-gate research-quality bar, claims register, and student-authorship log;
- PowerShell environment check and project validation scripts;
- local Git repository initialization and a data/sensitive-location `.gitignore` policy.

## Evidence from the initial audit

- The hardware supports modest local ML experimentation: RTX 5060 Laptop GPU with 8,151 MiB VRAM and roughly 697 GiB free disk.
- Python is not on `PATH`; no package install or model training was attempted.
- There was no existing project code and no connected GitHub repository matching ArchaeoAI.
- Git metadata is owned by the user's Windows account, so this sandbox cannot write Git lock files. Use the user's normal terminal for the first commit.

## Scientific rationale

LiDAR archaeology is already mature: a 2024 systematic review found 291 studies, while published deep-learning systems already tackle detection and segmentation. England's public National LIDAR Programme is a promising terrain source, but a label source must pass licensing and cultural-sensitivity review before any download or modeling.

## E001 stop conditions

Stop or pivot if labels cannot be lawfully/safely used, cannot support at least three independent spatial blocks, or are confounded by acquisition metadata. A negative geographic-holdout result is evidence, not failure.

## Immediate next actions (preparation before 15 September)

1. Install Python 3.12+ and confirm `python --version` in a new terminal.
2. Make the first local Git commit from the user's terminal.
3. During Week 1, complete D001: audit two candidate label sources and expand the literature matrix to 20 primary papers.

The detailed research artifacts are in the repository root: `README.md`, `docs/`, `experiments/E001_geographic_baseline.md`, and `scripts/`.

## What makes this legitimately stronger

The project now cannot progress to a public result merely because a model produces a high score. It must clear data-trust, method-trust, result-trust, and communication-trust gates. Every future headline claim must point to evidence, carry a scope limit, and remain pending until reviewed. The student log records predictions, failed ideas, personal work, and AI assistance so that the eventual account is defensible and genuinely yours.
