# E001 Phase 3B — multi-region external dataset construction

## Decision

**READY_UNSCORED.** Phase 3B constructed and froze the independent external dataset without
loading the Random Forest, generating predictions, or calculating a performance metric. The
dataset contains 60 strictly curated scheduled single bowl-barrow observations and 60 matched
`unlabelled_background` observations across the five cells authorized by Phase 3A and Phase
3B-R1.

This status means the data are technically ready for the separately authorized one-time Phase 3C
evaluation. It is not an external-validation result and does not support a performance or
discovery claim.

## Strict curation and frozen selection

The first cell retained its locked 47 accepted records. The 33 supplementary probable-title
records were reviewed under the same official full-entry, single-monument, upstanding-earthwork,
geometry, 1 m coverage, and provenance rules: 29 were accepted, two rejected, none remained
uncertain, and two still required terrain review. The combined accepted pool was therefore 76.

The Phase 3A SHA-256 ranking rule selected exactly 60 positives from that pool. No inclusion rule
was loosened, no terrain morphology informed selection, and no model output was available.

## Matched backgrounds and terrain

Each positive has one deterministically sampled observation labelled `unlabelled_background`.
The label means unknown terrain, not archaeology-free terrain or a known negative. Each background
uses the frozen 1–5 km annulus, remains in its positive's 25 km cell, matches its exact Environment
Agency survey provenance, and passes the 500 m positive, 250 m known Scheduled Monument, and 256 m
background-spacing exclusions.

All 120 observations use bounded 128 m × 128 m Environment Agency LiDAR Composite DTM windows in
EPSG:27700 at 1 m resolution. Technical QA verifies dimensions, transform, resolution, no-data,
finite values, provenance, and raw/patch/archive checksums. The frozen representations are:

- median-normalized elevation;
- slope in degrees;
- fixed 315° azimuth / 45° altitude hillshade; and
- 16 m local relief.

No visual decision about whether a terrain patch resembles a barrow was made during technical QA.

## Independence and privacy

Private in-memory audits enforce at least 15 km separation from all 522 E001 observations and the
Phase 2F private inference domain. They also check sample IDs, centres, exact terrain content,
positive/background pairing, terrain-window overlap, and duplicate content. Exact coordinates,
row-level labels, raw GeoTIFFs, processed NPZ archives, and the private manifest remain Git-ignored.

Five internal window overlaps remain between distinct accepted positive monuments. They are valid
under the frozen protocol: Phase 3A's disjoint-window language belongs to the prior-study
independence boundary and its machine-readable gates prohibit overlap with E001 and Phase 2F. The
protocol separately fixes 500 m positive-to-background and 256 m background-to-background spacing,
but specifies no positive-to-positive exclusion. All five pairs have different centres, sample IDs,
and terrain-content hashes; none is a matched positive/background pair. Removing them after
construction would alter the performance-blind SHA-256 selection rule.

Only the aggregate coordinate-safe freeze receipt is public:
[`outputs/external_validation/e001_phase3b_external_dataset_freeze.json`](../outputs/external_validation/e001_phase3b_external_dataset_freeze.json).
It binds the private manifest checksum and the canonical external-dataset SHA-256.

## Hard scoring boundary

Phase 3B did not import or load the Random Forest and did not call `predict()` or
`predict_proba()`. It calculated no accuracy, balanced accuracy, precision, recall, F1, ROC-AUC,
average precision, confusion matrix, or other external performance statistic.

Phase 3C subsequently performed the separately controlled one-time evaluation. The immutable Phase
3B receipt remains the pre-score dataset record; the result and spent-test state are documented in
[`e001-phase-3c-external-evaluation.md`](e001-phase-3c-external-evaluation.md).
