# 2026-08-30 — Phase 4A external error analysis

Phase 4A reproduced the spent Phase 3C result from its frozen private prediction vector and then
performed only post-hoc aggregate analysis. The immutable confusion groups are TP 49, TN 52, FP 8,
and FN 11. No model object was loaded; no fit, prediction, rescoring, threshold change, observation
removal, or relabelling occurred.

The analysis summarized score distributions, the four frozen terrain representations, zero no-data
fractions, five pre-specified geographic cells, and survey-year/provenance strata. It also generated
eight deterministic private metadata-free terrain mosaics, two per outcome group. All public
outputs are coordinate-safe aggregate JSON or SVG. The strongest patterns and five future
hypotheses are documented as exploratory and non-causal.

Decision: retain the frozen Random Forest as the preferred current model. Preserve Phase 3 data as
evaluation-only for that model; any future use for training creates a new model generation and
requires new independent evaluation data.
