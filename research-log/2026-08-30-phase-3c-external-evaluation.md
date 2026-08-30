# 2026-08-30 — Phase 3C one-time external evaluation

## Pre-score gate

The tracked repository was clean at
`fb26bfa053cf84006fdd9db969aba82c270fa09b` and matched `origin/main`. Before loading the model,
the run revalidated the Phase 3A protocol, Phase 3B-R1 amendment, 120-observation dataset digest,
60 matched-pair structure, private manifest, every raw and processed terrain checksum, every
representation checksum, 4,096-feature shape, prior-study independence receipt, immutable prior
artifacts, frozen RF configuration, and private model-artifact bytes.

## One-time execution

A private authorization receipt was written before the model was loaded. The previously frozen
full-fit Random Forest artifact then produced exactly one complete 120-score vector. That vector
was written privately and checksummed before interpretation. The scoring entry point now refuses a
second run.

No model refit, retraining, tuning, recalibration, feature change, threshold change, label change,
sample removal, or sample replacement occurred.

## Result

The combined balanced accuracy was 0.841667. The frozen 10,000-resample matched-pair bootstrap
interval was [0.775, 0.900]. The confusion matrix was TN = 52, FP = 8, FN = 11, TP = 49. Under the
pre-scoring interpretation rule, the outcome is `EXTERNAL_GENERALIZATION_SUPPORTED`.

The external test is now spent. All row-level predictions, coordinates, terrain paths, and terrain
artifacts remain private and ignored. The tracked record contains aggregate scientific evidence
only and makes no archaeological-discovery or England-wide performance claim.
