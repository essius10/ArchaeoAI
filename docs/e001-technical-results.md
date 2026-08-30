# ArchaeoAI E001 — technical results

## Research question

Can a terrain-only model distinguish public LiDAR-derived patches centred on documented,
scheduled, surviving single bowl barrows from carefully matched `unlabelled_background`, and does
that signal persist when evaluation geography is separated from training geography?

## Data and safeguards

E001 contains 261 curated positive patches and 261 matched unlabelled-background patches. Each
128 m × 128 m, 1 m-resolution DTM patch is transformed into median-normalized elevation, slope,
fixed 315°/45° hillshade, and 16 m local relief. Backgrounds were matched by coarse geography and
terrain provenance and excluded from known positive and Scheduled Monument buffers, but remain
unknown terrain rather than confirmed negatives.

Spatial overlap components and groups were kept intact across frozen train, development, and final
partitions. Coordinates, geography, provenance, survey year, IDs, filenames, and paths were never
model features. Exact locations, rasters, processed arrays, manifests, model files, and row-level
predictions remain private and Git-ignored.

## Baseline selection and confirmatory evaluation

A pre-registered development matrix compared Dummy, L2 Logistic Regression, and modest Random
Forest models across five frozen representation configurations. Geographic-development balanced
accuracy selected a 300-tree Random Forest using all four 4 × 4 mean-pooled representations
(4,096 features). Its development score was 0.821429, 0.035715 above the runner-up and outside the
frozen 0.02 tie band.

The separately authorized one-way evaluation produced:

| Condition | Observations | Balanced accuracy | 95% interval |
|---|---:|---:|---:|
| Frozen geographic final test | 62 | 0.870968 | [0.774194, 0.951613] |
| Group-aware random final comparison | 62 | 0.822581 | [0.718750, 0.916667] |

The geographic result concerns two specific held-out 100 km groups. It is not England-wide
performance and does not establish unknown-site discovery.

## Robustness and stronger-model comparison

A score-independent, post-hoc five-fold geographic analysis across the 23 coarse groups gave a
Random-Forest mean balanced accuracy of 0.823406 (fold range 0.790000–0.861111). A frozen compact
59,145-parameter CNN, evaluated on the same folds with three seeds, averaged 0.700866 and was weaker
on every fold. The simpler Random Forest was retained; the CNN result is useful negative evidence,
not a failed project.

## Independent external evaluation

Phase 3 constructed a separate multi-region dataset of 60 documented bowl-barrow patches and 60
matched unlabelled-background patches across five pre-specified 25 km cells. All were at least
15 km from prior E001 and controlled-inference geography. The unchanged Random Forest was scored
exactly once after the complete private prediction vector was frozen.

The primary external balanced accuracy was **84.17%**, with a pre-registered matched-pair bootstrap
**95% CI of 77.5–90.0%** (120 observations). The confusion matrix was TN = 52, FP = 8, FN = 11,
TP = 49. This met the frozen `EXTERNAL_GENERALIZATION_SUPPORTED` rule. The test is spent and cannot
be used for model selection, threshold choice, recalibration, or revision of the current model.

## Post-hoc external error analysis

Phase 4A is explicitly **POST-HOC / EXPLORATORY**. False negatives showed lower median slope,
hillshade, and local-relief variability than true positives, while false-positive backgrounds
showed higher variability than true negatives. Nine of eleven false negatives occurred in the
largest external cell and the 2021 stratum, but geography, sample composition, and year are
confounded. Small regional counts and retrospective inspection prevent causal or confirmatory
interpretation. Full details are in the [Phase 4A report](e001-phase-4a-external-error-analysis.md).

## Interpretation and limitations

The results support a reproducible terrain-pattern classification signal for the evaluated bowl-
barrow and matched-background design. They do not show archaeological finding accuracy, calibrated
archaeological probabilities, absence of archaeology in background terrain, or England-wide
generalization. Labels are curated public records rather than infallible ground truth. The project
still lacks independent label review, an independent clean-environment reproduction, and a
prospective evaluation for any future model generation.

No candidate location, discovery, or public map follows from these experiments. Phase 3 external
data remain evaluation-only for the reported Random Forest. Using them in future training would
create a new model generation requiring new independent data.
