# E001 Phase 2D-A preregistration — development-only baseline selection

This record was written before any E001 development score was computed. Phase 2D-A may load only
the geographic `train` and `development` partitions. Geographic `final_test` is inaccessible to the
experiment runner. The random condition is not evaluated in this bounded phase.

## Candidate matrix

Exactly three model families are crossed with exactly five input configurations, producing 15
pre-specified candidates:

- `DummyClassifier(strategy="prior")`;
- L2 `LogisticRegression(C=1, solver="lbfgs", max_iter=2000)` inside a training-fitted
  `StandardScaler` pipeline;
- `RandomForestClassifier` with 300 trees, depth 8, minimum leaf size 5, square-root feature
  sampling, one worker, and fixed seed 20260829.

Inputs are normalized elevation, slope, fixed hillshade, local relief, and all four concatenated.
Each 128×128 representation is reduced by deterministic non-overlapping 4×4 mean pooling to 32×32
or 1,024 features. The four-channel input has 4,096 features. Missing pooled cells, if any, are set
to zero after masked mean pooling; no metadata or coordinate is added.

## Selection rule

The primary criterion is balanced accuracy on the frozen geographic development block
`BNG_100KM_E2_N0`. Differences below 0.02 are effective ties. Ties prefer Logistic Regression, then
fewer representation channels, then the fixed model and representation orders recorded in
`configs/e001-phase-2d-a-preregistered.json`. ROC-AUC is secondary evidence only and cannot override
the primary rule. The classification threshold is fixed at 0.5.

No choice may use a final-test score. After selection, five deterministic training-label
permutations test whether the selected pipeline behaves near chance without changing development
labels. Permutation results cannot change the selected configuration.

## Integrity and feature policy

Labels come only from `outputs/dataset/e001_modelling_index.csv`. The loader verifies the active
split hash, QA status, NPZ structure, and patch-content checksum before pooling. It receives class
labels from the index; filenames and directories are never model features. Coordinates,
provenance, survey year, BNG group, source resolution, IDs, and checksums are prohibited as model
features. Metadata are used only for aggregate shortcut audits.

The future final-test runner must require a valid frozen primary-configuration hash. Phase 2D-A
creates that configuration but does not invoke final evaluation.
