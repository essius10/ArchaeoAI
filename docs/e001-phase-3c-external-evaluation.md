# E001 Phase 3C — one-time independent external evaluation

## Decision

**EXTERNAL GENERALIZATION SUPPORTED under the preregistered rule.** The frozen Random Forest was
evaluated once on the independently constructed external dataset of 120 observations: 60
documented bowl-barrow terrain patches and 60 matched `unlabelled_background` patches across five
pre-specified 25 km cells.

The primary combined balanced accuracy was **0.841667**, with a preregistered 10,000-resample
matched-pair bootstrap 95% interval of **[0.775, 0.900]**. The result meets the frozen rule requiring
balanced accuracy of at least 0.75 and a lower interval bound above 0.5. The external test is now
spent and cannot be used for further model selection, tuning, recalibration, or threshold choice.

## Frozen evaluation

The evaluation used the previously fitted 300-tree Random Forest bound by the Phase 3A protocol.
Its model-state SHA-256, private artifact SHA-256, hyperparameters, four representation channels,
4 × 4 mean pooling, 4,096-feature input, and 0.5 threshold were all verified before prediction.
No retraining or refitting occurred.

The complete score vector was generated once, saved under the Git-ignored private tree, and
checksummed before metrics were calculated. No observation was removed, replaced, reclassified, or
visually selected after scoring.

## Combined result

| Measure | Result |
|---|---:|
| Balanced accuracy | 0.841667 |
| 95% matched-pair bootstrap interval | [0.775, 0.900] |
| Accuracy | 0.841667 |
| Precision | 0.859649 |
| Positive-class recall | 0.816667 |
| F1 | 0.837607 |
| ROC-AUC | 0.927778 |
| Average precision | 0.942058 |
| Unlabelled-background recall | 0.866667 |

The confusion matrix is TN = 52, FP = 8, FN = 11, TP = 49, where
`unlabelled_background` remains unknown terrain rather than a confirmed archaeology-free class.

## Preregistered descriptive geography

The Phase 3B-R1 amendment permitted two descriptive strata, not five confirmatory region tests.
The first external geography contained 37 matched pairs and had balanced accuracy 0.824324. The
combined supplementary geography contained 23 matched pairs and had balanced accuracy 0.869565.
These strata are secondary descriptions with different and sometimes small contributing regions;
they did not select or tune the model and do not replace the 120-observation combined result.

## Context and claim boundary

The external result is close to the original pre-specified geographic final result (0.870968 on 62
observations) and the five-fold geographic robustness mean (0.823406), and exceeds the post-hoc
compact-CNN mean (0.700866). These are contextual comparisons across different evaluation designs,
not a pooled analysis or exact replication.

This remains terrain-pattern classification of documented bowl-barrow terrain versus matched
unlabelled background. It does not establish England-wide accuracy, archaeological probability,
discovery performance, or the absence of archaeology in background terrain. No discovery is
claimed and no location is published.

The coordinate-safe aggregate result is
[`outputs/external_validation/e001_phase3c_external_evaluation.json`](../outputs/external_validation/e001_phase3c_external_evaluation.json).
Private prediction rows, coordinates, manifests, rasters, and processed terrain remain ignored by
Git.

The subsequent [Phase 4A analysis](e001-phase-4a-external-error-analysis.md) is explicitly post-hoc
and exploratory. It does not alter this confirmatory result, reuse the spent test for selection, or
change the frozen model.
