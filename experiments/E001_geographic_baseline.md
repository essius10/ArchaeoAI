# E001 — Representation and split sensitivity baseline

## Research question

Does a terrain representation that encodes local morphology outperform elevation alone on an unseen geographic region, and how much does a random split overstate that performance?

## Preconditions

- D001 is approved and recorded.
- One documented, non-sensitive earthwork class is selected.
- Three or more spatial blocks contain positive and matched negative patches.
- The feature/label licenses permit this use.

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
