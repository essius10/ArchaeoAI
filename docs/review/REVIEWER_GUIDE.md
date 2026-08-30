# ArchaeoAI E001 external reviewer guide

## Purpose

ArchaeoAI E001 is an independent student research project studying whether terrain-only machine
learning can distinguish LiDAR-derived patches centred on documented, scheduled, surviving single
bowl barrows from matched `unlabelled_background`, and whether that signal survives geographic
separation. It is not a system for declaring archaeological sites.

The frozen Random Forest achieved **84.2% balanced accuracy (95% paired-bootstrap CI 77.5–90.0%)**
in a one-time independent external evaluation of 120 observations across five pre-specified
geographic cells. This is classification of documented bowl-barrow terrain versus matched
unlabelled background—not archaeological-discovery accuracy or England-wide performance.

## Evidence boundary

- **Confirmatory:** the pre-specified E001 geographic final result and the one-time Phase 3C
  external evaluation. The external test is spent and cannot be reused for tuning.
- **Post-hoc / exploratory:** five-fold robustness, compact-CNN comparison, and Phase 4A error
  analysis. These contextualize the frozen result but do not replace it.
- **Frozen:** dataset definitions, splits, model configuration/state, external score vector,
  metrics, figures, and manuscript evidence hashes.
- **Not claimed:** discovery, field validation, calibrated archaeological probability,
  archaeology-free backgrounds, universal transfer, institutional endorsement, or peer review.

Please begin with the [manuscript](../manuscript/archaeoai-e001-manuscript.md), then consult the
[reproducibility guide](../reproducibility.md), [citation audit](../citation-audit.md), and
[claims register](../claims-register.md). Precise locations and location-linked terrain are
intentionally withheld.

## Questions for reviewers

1. Does the distinction between documented-terrain classification and archaeological discovery
   remain clear throughout?
2. Is the geographic-validation design convincing for the bounded claim being made?
3. Are the matched unlabelled-background assumptions and exclusions reasonable and sufficiently
   explicit?
4. Does `EXTERNAL_GENERALIZATION_SUPPORTED` accurately describe the frozen decision rule without
   overstating geographic scope?
5. Is the paired-cluster bootstrap interval described and interpreted appropriately for 60
   matched pairs?
6. Are important archaeology, LiDAR, spatial-validation, or machine-learning references missing?
7. Are confirmatory, robustness, stronger-model, and post-hoc analyses separated clearly enough?
8. Are the limitations proportionate, especially inventory bias, limited geography, absent field
   validation, and the unreviewed Phase 2F packet?
9. Do the privacy controls and withheld-data policy adequately address responsible archaeology?
10. What must change before this could be considered for a preprint or formal publication?
