# E001 — Representation and split sensitivity baseline

## Research question

Does a terrain representation that encodes local morphology outperform elevation alone on an unseen geographic region, and how much does a random split overstate that performance?

## Preconditions

- D001 is approved and recorded.
- The class is scheduled, single bowl barrows surviving as discrete upstanding earthworks in England.
- The five-site Phase 2B positive-terrain pilot passes; full positive acquisition remains a separate gate.
- Three or more spatial blocks contain positive and matched negative patches.
- The feature/label licenses permit this use.

## Frozen Phase 2B preprocessing

- Primary positive patch: configurable 128 m square, aligned to the 1 m EPSG:27700 grid.
- Terrain source: bounded EA LIDAR Composite DTM 1 m WCS responses, ODN heights.
- Representations: per-patch median-normalized elevation, slope degrees, 315°/45° hillshade, and
  16 m-radius local relief.
- No-data above 20%, wrong CRS/resolution/dimensions, incomplete bounds, or extreme values reject a
  patch; no-data is never silently filled.
- No global normalization is permitted before the split; any later fitted transform uses training
  groups only.
- Overlapping positive patches must stay together. Provisional groups are preserved, but no
  train/test assignment is frozen yet.

## Design

1. Produce raw DTM, hillshade, slope, and one justified multi-scale local-relief representation using fixed, recorded parameters.
2. Create positive patches centered on labels; create terrain- and region-matched negatives excluding a documented buffer around all known labels.
3. Compare two splits: (a) random patch split and (b) group split by spatial block, with one block held out.
4. Fit only low-compute baselines: logistic regression on summary features and a small random forest. Tune within training blocks only.
5. Report precision–recall AUC, F1 at a preselected validation threshold, recall, precision, block-bootstrap 95% confidence intervals, and confusion matrices.

## Predictions to record before running

- Student prediction: ____________________
- Expected direction of random-vs-geographic performance gap: ____________________
- Representation expected to be most robust: ____________________

## Falsification / stop rules

- If labels cannot be licensed or safely handled, stop and select another task.
- If positives/negatives are separable by tile metadata or acquisition date, redesign before fitting.
- If geographic holdout has too few independent blocks, report only as feasibility evidence—not a generalization claim.

## Definition of done

Code, environment lockfile, data manifest, split manifest, seed, parameters, metrics, and error review are all saved. The report must say whether H0 was rejected and must distinguish a terrain signature from an archaeological conclusion.
