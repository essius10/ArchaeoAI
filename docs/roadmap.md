# Research roadmap — 15 September 2026 to March 2027

## Current gate (30 August 2026)

Phase 2C froze 261 approved positive-terrain and 261 matched unlabelled-background patches. Both the
group-aware random condition and the complete-block geographic condition now contain 216/14/31
examples per class in train/development/final test. All seven overlap components remain intact and
the two final-test block assignments are hash-guarded. Phase 2D-A selected and froze an all-four
pooled Random Forest using only geographic development. Phase 2D-B then recorded 0.870968 balanced
accuracy [0.774194, 0.951613] on the one-way geographic final test. Phase 2E-A then classified the
baseline as ROBUST under a pre-committed five-fold post-hoc protocol (mean 0.823406; fold range
0.790000–0.861111). Phase 2E-B0 has now frozen a privacy-safe 59,145-parameter compact-CNN
protocol against the same five folds. Phase 2E-B then completed all 15 frozen runs without tuning.
The CNN averaged 0.700866 balanced accuracy, 0.122540 below the Random Forest mean, and showed
internal-validation overfitting despite modest seed variation. The stronger-model classification is
`CNN NOT JUSTIFIED AT CURRENT DATA SCALE`; the model recommendation for any separately approved
Phase 2F is `USE RANDOM FOREST FOR PHASE 2F`.

Phase 2F-A froze a controlled one-domain ranking design and a full-data Random Forest fit. Phase
2F-B then bound exactly one private 5 km domain without model scores, processed all 5,929 frozen
grid windows, and retained 1,159 representatives after deterministic spatial deduplication. The
private blinded packet contains 12 HIGH, 25 MEDIUM, and 25 RANDOM items. The current gate is
blinded human morphology review: no review, heritage-record cross-check, candidate claim, second
domain, or public location exists.

Phase 3A additionally froze an independent external geographic-validation design for the unchanged
Random Forest. Phase 3B-R1 authorized four supplementary 25 km cells without changing the class,
evidence gate, target, model, or privacy policy. Phase 3B then froze 60 documented bowl-barrow and
60 matched `unlabelled_background` observations. Phase 3C evaluated the unchanged model exactly
once: combined balanced accuracy was 0.841667 with preregistered matched-pair bootstrap 95% CI
[0.775, 0.900]. The frozen classification is `EXTERNAL GENERALIZATION SUPPORTED`. The external
test is now spent; it cannot be used for tuning, and no discovery or England-wide claim follows.

Target commitment: 6–8 hours/week during school terms. Increase only during breaks after evidence justifies it.

| Month | Learning and research focus | Engineering/experiment deliverable | Evidence / gate |
|---|---|---|---|
| Sep | LiDAR/DTM basics, CRS, spatial leakage; complete systematic search | Environment lock, source registry, label/license decision | D001 approval; reproducible data manifest prototype |
| Oct | Terrain derivatives, sampling, descriptive statistics | Deterministic raster/patch pipeline and spatial split manifest | Tests show no block crosses splits; visual QA of 50 patches |
| Nov | Logistic regression, trees, PR curves, bootstrap CIs | E001 classical baselines on internal blocks | Pre-registered metrics and result log; **Gate 2 review** |
| Dec | Error analysis and negative controls | Geographic-holdout report and leakage audit | **Gate 3 review:** improve data/representation, or stop/pivot |
| Jan | Convolution/math only if E001 warrants it | Small CNN comparison with fixed compute budget | Improvement assessed on untouched holdout; no model escalation without Gate 3 evidence |
| Feb | Robustness: resolution, representation, and region sensitivity | Ablation matrix and block-level uncertainty | Conclusions survive stated perturbations or are narrowed |
| Mar | Writing, reproducibility, external-review preparation | Technical report v0.1, release checklist, reviewer questions | Independent rerun from clean environment; **Gate 4 review** |

## First 12 weeks

| Week | Primary deliverable | Time | Definition of done |
|---:|---|---:|---|
| 1 | D001 label/data decision and 20-paper search matrix | 7 h | License, sensitivity, and three-block feasibility recorded; all citations linked. |
| 2 | Python/geospatial environment and data manifest | 6 h | Clean environment installs; one raw tile checksum recorded. |
| 3 | CRS and raster QA notebook | 6 h | One DTM renders correctly; units, nodata, bounds, and CRS verified. |
| 4 | Terrain-derivative specification | 6 h | Equations/parameters justified; 50 visual checks logged. |
| 5 | Label and unlabelled-background sampling specification | 7 h | Exclusion buffers and matching rules fixed before model fitting. |
| 6 | Spatial split generator + tests | 7 h | No spatial block appears in more than one split. |
| 7 | Patch generator and dataset card v0.1 | 7 h | Patches reproducible from manifest/seed. |
| 8 | Descriptive data audit | 6 h | Class counts, region counts, missingness, and acquisition confounds reported. |
| 9 | Logistic-regression baseline | 7 h | Metrics on validation blocks and exact configuration logged. |
| 10 | Random-forest baseline | 7 h | Same split, metrics, and feature ablation logged. |
| 11 | Geographic holdout + block bootstrap | 7 h | Holdout untouched until final run; uncertainty reported. |
| 12 | Error/failure review and red-team memo | 6 h | 30 false positives/negatives reviewed; next decision recorded. |

## Week 1 exact tasks (15–21 September)

1. Read the research charter and write a one-paragraph prediction for E001 (20 min).
2. Expand the literature matrix to 20 primary studies; record dataset, geography, labels, split, metric, and limitation (3 h).
3. Identify two candidate label providers and read their terms; classify site sensitivity (90 min).
4. Verify whether each candidate can support three spatial blocks and matched negatives without publishing vulnerable coordinates (90 min).
5. Decide D001 using the stated rejection criteria; if none pass, document a pivot rather than downloading data (45 min).

Outputs: completed matrix, D001 decision, search log, and E001 prediction. The week is complete only when all four outputs exist.
