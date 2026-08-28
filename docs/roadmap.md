# Research roadmap — 15 September 2026 to March 2027

## Current gate (28 August 2026)

Phase 2B completed a five-site real-terrain pilot and returned **GO FOR FULL TERRAIN DATASET**. The
remaining 256 positive patches have not been downloaded. Background sampling, split finalization,
and all modelling remain blocked pending explicit approval and the safeguards in the Phase 2B memo.

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
| 5 | Label and negative-sampling specification | 7 h | Exclusion buffers and matching rules fixed before model fitting. |
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
