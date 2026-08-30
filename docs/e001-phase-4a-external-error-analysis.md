# E001 Phase 4A — post-hoc external error analysis

## Status and boundary

**POST-HOC / EXPLORATORY.** Phase 4A analyzes the single frozen Phase 3C prediction vector after
the external test was spent. It does not retrain, refit, tune, recalibrate, rescore, change the
0.5 threshold, remove observations, or revise labels. The Phase 3C confirmatory result remains
0.841667 balanced accuracy (95% matched-pair bootstrap interval [0.775, 0.900]) on 120 observations.

The four frozen outcomes are 49 true positives (TP), 52 true negatives (TN), 8 false positives
(FP), and 11 false negatives (FN). Here “negative” is only the binary evaluation role of
`unlabelled_background`; it does not mean archaeology-free terrain. Model scores are terrain-
similarity scores, not archaeological probabilities.

## Score summaries

| Outcome | n | Mean | Minimum | Q1 | Median | Q3 | Maximum |
|---|---:|---:|---:|---:|---:|---:|---:|
| TP | 49 | 0.7961 | 0.5021 | 0.7054 | 0.8200 | 0.8927 | 0.9753 |
| TN | 52 | 0.2426 | 0.0817 | 0.1556 | 0.2476 | 0.3077 | 0.4887 |
| FP | 8 | 0.5822 | 0.5091 | 0.5432 | 0.5695 | 0.6065 | 0.7194 |
| FN | 11 | 0.3350 | 0.1383 | 0.3053 | 0.3380 | 0.3837 | 0.4967 |

## Exploratory terrain patterns

For each frozen representation, Phase 4A summarizes each 128 × 128 patch, then compares the
distributions of those summaries across TP/TN/FP/FN. This is descriptive analysis, not Random-
Forest feature attribution.

False negatives had lower median patch variability than true positives in slope (0.855 versus
2.233 degrees), hillshade (0.0148 versus 0.0289), and local relief (0.0956 versus 0.1816). False-
positive backgrounds had higher variability than true negatives in slope (3.153 versus 2.089),
hillshade (0.0386 versus 0.0244), and local relief (0.220 versus 0.166). These associations are
consistent with weaker relief being harder to classify and structurally varied background terrain
being more confusable, but the small error groups and post-hoc design do not establish causes.

All 120 processed patches had zero no-data fraction, so missing pixels do not distinguish the
outcome groups. That does not rule out other acquisition, landscape, preservation, or processing
differences.

## Geography and provenance

The five pre-specified 25 km cells had descriptive balanced accuracies of 0.824 (37 pairs), 0.800
(5), 0.900 (5), 0.889 (9), and 0.875 (4). Four cells contain fewer than ten pairs; their estimates
have high uncertainty and no “best region” is identified. Nine of eleven false negatives occurred
in the largest cell.

Survey-year strata were 2019 (12 observations; balanced accuracy 0.917), 2020 (34; 0.882), and
2021 (74; 0.811). Every observation used 1 m National LIDAR Programme terrain, so program and
resolution cannot be compared. Geography, sample composition, and survey year are confounded;
these values support no causal claim about acquisition year or region.

## Private terrain exemplars

Two deterministic coordinate-free terrain mosaics per outcome group were generated for private
technical inspection. Selection used a SHA-256 rank within the already frozen outcomes. The eight
PNG files contain only four grayscale terrain panels and no text metadata, identifiers, scores, or
coordinates. They remain under `data/private/`, are Git-ignored, and are not publication evidence.

## Future hypotheses

1. Lower slope, hillshade, and local-relief variability may increase false negatives; test this in
   a prospectively registered relief-stratified external dataset.
2. Highly variable unlabelled terrain may increase false positives; build a model-independent,
   independently reviewed hard-background study.
3. A single 315°/45° hillshade may encode low-relief morphology inconsistently; compare it with a
   pre-specified multi-azimuth representation in a new model generation.
4. Regional context or year-linked acquisition differences may contribute to the observed false-
   negative concentration; prospectively balance geography and provenance to separate them.
5. Near-threshold scores may mark morphological ambiguity rather than calibrated uncertainty;
   test an abstention design on new data without revising the reported Phase 3C threshold.

## Scientific decision

The frozen Random Forest remains the preferred current model because it retained strong geographic
performance, exceeded the compact CNN in the five-fold comparison, and generalized under the
pre-registered external rule. Phase 3 external data are not training data for that reported model.
Any future model trained with them is a new model generation and requires new independent
evaluation data.

The machine-readable aggregate is
[`e001_phase4a_error_analysis.json`](../outputs/external_validation/e001_phase4a_error_analysis.json).
Its SHA-256 is `209559c7759c6641d6ac7afeb47bd9a64f3f9581c6a3f9b5d8a5e024825a7276`.
