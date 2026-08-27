# Candidate research questions and decision — RQ001

Scores are 1 (weak) to 5 (strong), based on the initial literature scan and the current no-data state. They are provisional until label provenance is audited.

| Rank | Candidate question | Novelty | Feasibility | Scientific value | Data/labels | Validation | Compute fit | Decision |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 1 | For one documented English earthwork class, how do terrain representations and random versus geographic splits change apparent baseline performance? | 4 | 5 | 5 | 4 | 5 | 5 | **Recommend** |
| 2 | Can a small CNN trained on one English region detect the same feature class in another? | 3 | 3 | 4 | 4 | 5 | 3 | Defer until RQ1 data pipeline/baselines work. |
| 3 | Can self-supervised pretraining reduce labels needed for archaeological segmentation? | 3 | 2 | 4 | 3 | 4 | 2 | Defer; requires a mature dataset and stronger compute/ML foundation. |
| 4 | Can anomaly detection find previously undocumented terrain signatures? | 2 | 1 | 2 | 2 | 1 | 3 | Reject: validation and cultural-heritage risk are poor. |
| 5 | Do features transfer between English earthworks and Maya LiDAR datasets? | 3 | 1 | 3 | 1 | 3 | 1 | Reject for now: task, label, resolution, and domain differences confound the result. |

## Recommended direction

Start with RQ1. It is narrow enough to execute rigorously, directly tests a commonly weak practice (spatially correlated evaluation), teaches geospatial ML properly, and can produce a useful negative result. It avoids claiming a new detector or an archaeological discovery.

## Why not begin with a CNN?

The current unknowns are label legality, label quality, class definition, negative sampling, and independent spatial blocks. A CNN cannot repair failures in those components. If the baseline collapses under geographic holdout, that result is the finding—not a reason to add a larger model.

## Decision gate

Proceed only when D001 identifies a non-sensitive, reusable label source with at least three independent spatial blocks. Otherwise pivot to a fully documented open benchmark or a representation-only analysis without site-level labels.
