# E001 Phase 2E-A — frozen post-hoc robustness protocol

This protocol was created before any Phase 2E robustness score was computed. Phase 2D remains the
only confirmatory E001 result: geographic balanced accuracy 0.870968 with whole-group bootstrap 95%
CI [0.774194, 0.951613]. Every Phase 2E analysis is explicitly
`posthoc_geographic_robustness`; the observed Phase 2D final test is never described as unseen or
used for model, representation, threshold, background, or hyperparameter selection.

## Score-independent geographic folds

All 23 occupied BNG 100 km groups are assigned to five folds. Groups are sorted by descending
observation count, descending related-unit count, then group ID. Each group is greedily assigned to
the fold with the fewest observations, fewest groups, then lowest fold number. The algorithm uses no
model score. Matched observations and overlap components remain intact; a private coordinate audit
found zero cross-fold 128 m terrain-window overlaps. The frozen assignment SHA-256 is
`825eb1088a53f764f991bf6bb22f2c9fe6eeb868916a5abab92012eed85d90ab`.

## Fixed analyses

The primary robustness analysis uses only the frozen 300-tree Random Forest, depth 8, minimum leaf
5, square-root feature sampling, threshold 0.5, seed 20260829, and all four 4×4-pooled terrain
representations. It reports every fold and aggregate balanced-accuracy statistics.

Secondary post-hoc analyses use the same folds and fixed model parameters:

- the four individual representations plus all four;
- four drop-one-representation configurations;
- seeds 20260829, 20260830, 20260831, 20260901, and 20260902;
- deterministic 100%, 75%, 50%, and 25% related-unit training subsets;
- three 5,000-resample group-bootstrap seeds on the already observed geographic final result;
- 100 fixed training-label permutations on the original geographic train/development condition;
- representation correlation, aggregate out-of-fold score distributions, and coordinate-safe
  error/metadata summaries.

Training subsets rank whole `overlap_component_id` units, or otherwise observational groups, by a
fixed SHA-256 rule. No related unit is split. The permutation model seed remains 20260829; only the
training-label shuffle seed changes.

## Explicit exclusions

No hard-background condition is constructed because complete model-independent road, forestry,
field-boundary, and hard-relief annotations do not exist for every observation. Selecting hard
backgrounds after inspecting predictions would be biased, while acquiring new backgrounds is beyond
this bounded phase. The optional Random Forest capacity comparison is also skipped to prioritize
geographic stability and shortcut checks. No deep-learning dependency or model is authorized.

## Classification rule

`POTENTIAL SHORTCUT / REDESIGN REQUIRED` applies if a direct coordinate, serialization,
absolute-offset, class-schema, or split-integrity audit fails. Otherwise `ROBUST` requires mean
geographic CV balanced accuracy at least 0.70, minimum fold at least 0.60, seed-mean range at most
0.05, and 50%-training mean at least 0.65. `MIXED ROBUSTNESS` requires mean at least 0.60 and minimum
fold at least 0.50 but misses a robust criterion. Lower performance is `FRAGILE`.

This rule classifies stability; it cannot replace or improve the frozen Phase 2D result.
