# E001 Phase 2D-A — development-only baseline selection

Phase 2D-A implemented the pre-registered baseline infrastructure, evaluated the geographic train
and development partitions, and froze one primary configuration. It did not request the geographic
final-test partition, run the random condition, compute a final metric, inspect final predictions,
or search unknown terrain.

## Infrastructure

The only direct modelling dependency added was scikit-learn 1.9.0. It installed its normal runtime
dependencies, including SciPy 1.18.1, Joblib, threadpoolctl, and Narwhals. No deep-learning library
or additional model family was added.

The fail-closed loader:

- reads labels only from the coordinate-safe modelling index;
- exposes only the active condition's `train` and `development` partitions;
- sanitizes active `final_test` labels and raises on any final-test request;
- verifies the frozen split SHA-256, QA status, NPZ schema, and patch-content checksum;
- loads private arrays without exposing coordinates;
- excludes provenance, year, BNG group, resolution, IDs, paths, and filenames from features.

Each representation uses deterministic non-overlapping 4×4 mean pooling: 128×128 becomes 32×32,
or 1,024 features. The four-representation configuration concatenates 4,096 features. All-nodata
pooling cells, if present, deterministically become zero. Logistic Regression alone uses a
training-fitted `StandardScaler` inside its scikit-learn `Pipeline`.

## Pre-registered candidates and rule

Commit `b5389e9` recorded the full matrix before development scoring: prior DummyClassifier, L2
Logistic Regression, and a modest 300-tree Random Forest crossed with normalized elevation, slope,
hillshade, local relief, and all four inputs.

Geographic-development balanced accuracy is primary. A difference below 0.02 is an effective tie;
ties prefer Logistic Regression and then fewer channels. ROC-AUC is secondary only. Threshold 0.5
was fixed. The random condition was deliberately not run in this bounded phase.

## Geographic development results

The geographic training partition contains 432 observations and development contains 28, balanced
14/14 by class.

| Model | Representation | Features | Balanced accuracy | ROC-AUC |
|---|---|---:|---:|---:|
| Dummy | Normalized elevation | 1,024 | 0.500000 | 0.500000 |
| Dummy | Slope | 1,024 | 0.500000 | 0.500000 |
| Dummy | Hillshade | 1,024 | 0.500000 | 0.500000 |
| Dummy | Local relief | 1,024 | 0.500000 | 0.500000 |
| Dummy | All four | 4,096 | 0.500000 | 0.500000 |
| Logistic Regression | Normalized elevation | 1,024 | 0.750000 | 0.816327 |
| Logistic Regression | Slope | 1,024 | 0.642857 | 0.729592 |
| Logistic Regression | Hillshade | 1,024 | 0.678571 | 0.816327 |
| Logistic Regression | Local relief | 1,024 | 0.607143 | 0.686224 |
| Logistic Regression | All four | 4,096 | 0.678571 | 0.785714 |
| Random Forest | Normalized elevation | 1,024 | 0.750000 | 0.841837 |
| Random Forest | Slope | 1,024 | 0.571429 | 0.714286 |
| Random Forest | Hillshade | 1,024 | 0.785714 | 0.897959 |
| Random Forest | Local relief | 1,024 | 0.785714 | 0.928571 |
| Random Forest | All four | 4,096 | **0.821429** | 0.923469 |

The all-four Random Forest is selected because its balanced accuracy exceeds the two 0.785714
alternatives by 0.035715, outside the effective-tie band. ROC-AUC did not determine the choice.

## Sanity and shortcut audits

Five deterministic training-label permutations of the selected pipeline produced balanced
accuracies from 0.428571 to 0.714286, mean 0.528571; mean ROC-AUC was 0.484694. The selected score
exceeded all five permutations. The high single permutation is retained and is plausible with only
28 development examples; these checks are diagnostics, not significance tests or selection inputs.

Within both train and development, provenance, survey year, BNG group, and source-resolution
category counts have zero positive/background imbalance. None are model features. This count audit
does not prove the absence of every terrain shortcut.

## Frozen primary configuration

- model: Random Forest;
- parameters: 300 trees, depth 8, minimum leaf 5, square-root feature sampling, one worker;
- representation: all four pooled channels;
- feature count: 4,096;
- scaler: none;
- threshold: 0.5;
- model seed: 20260829;
- configuration SHA-256: `20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4`.

The configuration binds both frozen split hashes and records `final_test_evaluated: false`. Future
final evaluation must validate this configuration hash and its geographic split binding. The
Phase 2D-A loader itself has no final-test loading route.

## Limits

- Development has only 14 examples per class; its estimates are discrete and uncertain.
- The selected result is development evidence, not a final generalization estimate.
- The geographic and random final tests remain unevaluated.
- CPython 3.12 reproduction and the independent 40-record human label review remain outstanding.
- No F1, accuracy, or ROC-AUC was computed on a final test.
- No archaeological prediction or discovery claim is supported.

Phase 2D-B requires explicit approval.
