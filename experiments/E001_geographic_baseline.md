# E001 — Representation and split sensitivity baseline

## Research question

Does a terrain representation that encodes local morphology outperform elevation alone on an unseen geographic region, and how much does a random split overstate that performance?

## Preconditions

- D001 is approved and recorded.
- The class is scheduled, single bowl barrows surviving as discrete upstanding earthworks in England.
- The five-site Phase 2B positive-terrain pilot passes; full positive acquisition remains a separate gate.
- The frozen Phase 2C index contains positive and matched `unlabelled_background` patches.
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
- Overlapping positive patches and their matched backgrounds stay in one observation group.
- Phase 2C split manifests freeze train, development, and final-test assignments before modelling.

## Frozen Phase 2C dataset and splits

- Primary ratio: 261 positives to 261 unlabelled backgrounds (1:1), selected before modelling.
- Background candidates use a 500 m all-positive exclusion, 250 m Scheduled Monument exclusion,
  256 m background separation, the same coarse group, and exact terrain-provenance matching.
- `unlabelled_background` means no target label is known under those rules; it is not a true
  archaeological negative.
- Random comparison: deterministic SHA-256-ranked observation groups, with 216/14/31 examples per
  class in train/development/final test.
- Geographic primary condition: `BNG_100KM_E2_N0` is development;
  `BNG_100KM_E3_N2` and `BNG_100KM_E5_N4` are the frozen final test; other blocks are training.
- Assignment hashes in both manifests are change guards. Phase 2D development must not inspect or
  alter final-test membership.

## Design

1. Produce raw DTM, hillshade, slope, and one justified multi-scale local-relief representation using fixed, recorded parameters.
2. Load labels only from the coordinate-safe frozen index; never infer class from paths or filenames.
3. Compare the frozen group-aware random and complete-block geographic conditions without changing
   their observations or assignments.
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
