# E001 Phase 2D-B — frozen one-way final-evaluation protocol

This protocol was written and committed before any E001 final-test score was computed. It binds the
one-way evaluation to selection commit `790ac9f4b99da94e8f9bab2a6aed70b34ac88558` and frozen primary
configuration SHA-256
`20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4`.

## Frozen system

The only evaluated system is the selected 300-tree Random Forest with depth 8, minimum leaf size 5,
square-root feature sampling, one worker, and seed 20260829. Its inputs are normalized elevation,
slope, fixed hillshade, and local relief. Non-overlapping 4×4 means reduce each 128×128 channel to
1,024 features; the four channels concatenate to 4,096 features. The classification threshold is
0.5. None of these choices may change after final-test access.

No secondary final baseline is authorized. Phase 2D-A pre-registered other candidates for
development selection, but it did not pre-register their final-test evaluation.

## Conditions and endpoints

The random final condition is evaluated first as a secondary descriptive comparison. The geographic
final condition is then evaluated as the primary E001 endpoint. Each condition independently fits
the exact frozen model on that condition's 432 training observations and evaluates its frozen 62
observation final partition (31 `positive_bowl_barrow`, 31 `unlabelled_background`). Development
observations are not added to training.

The primary metric is balanced accuracy. Supporting metrics are accuracy, positive-class precision,
recall, F1, ROC-AUC, average precision, and the confusion matrix. Random-minus-geographic balanced
accuracy is descriptive: a positive value means geographic performance was lower. No significance
test is pre-specified.

## Uncertainty

Percentile 95% intervals use 5,000 deterministic bootstrap resamples with seed 20260835. The unit is
an overlap component when present and otherwise an observational group. Entire units are sampled
with replacement, so matched observations and retained overlapping positives are never separated.
Balanced accuracy, accuracy, F1, and ROC-AUC receive intervals; undefined replicates, if any, are
counted and omitted transparently.

## Guard and result policy

The runner must validate the protocol hash, primary-configuration hash, both split hashes, exact
model and preprocessing specification, selection commit ancestry, clean pre-existing result paths,
dataset checksums, and expected class counts before scoring. It writes final results with exclusive
creation and never overwrites an existing result. The frozen Phase 2D-A configuration remains an
immutable pre-unlock artifact with `final_test_evaluated: false`; the separate final result receipt
records the completed transition to `true`.

Labels come only from the coordinate-safe modelling index. Features come only from the four private
terrain arrays. Coordinates, identifiers, paths, provenance, survey year, BNG group, source
resolution, and filenames are not model features. Final outputs contain aggregate results only.

After metrics are frozen, coordinate-safe aggregate error and shortcut audits may describe coarse
groups and terrain properties. They cannot trigger refitting, threshold changes, sample removal, or
any other Phase 2D change.
