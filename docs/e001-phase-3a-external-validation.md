# E001 Phase 3A — independent external geographic validation design

## Decision

**READY FOR PHASE 3B EXTERNAL DATASET CONSTRUCTION, with no model access.** Phase 3A freezes a
new geographic evaluation design for the existing E001 Random Forest. It does not create an
external dataset, download terrain, load the model, calculate a metric, or establish external
generalization.

The public protocol is
[`configs/e001-phase-3a-external-validation.json`](../configs/e001-phase-3a-external-validation.json).
Its SHA-256 is
`af4e0a8f0eac93ef999934bd94aa6393d55bb486c061e5dbf9f5d02f47caebcc`.

## Research question and claim boundary

Can the already-frozen E001 Random Forest transfer to a newly curated geographic sample of the
same archaeological target—documented bowl barrows—without using any external observation to
change the model, threshold, features, protocol, or sample size?

If all later gates are followed, the completed study may be described as **independent external
geographic validation**. It must not be described that way if an external label, terrain patch, or
model output changes any part of the protocol. Failure is publishable evidence; it is not a reason
to retune the RF within this study.

The unreviewed Phase 2F candidate packet is excluded. It is neither a label source nor an external
test set.

## External geography

The frozen public geography is the 25 km British National Grid feasibility cell
`BNG_25KM_E16_N5`, described coarsely as **central Salisbury Plain, Wiltshire**. This is a coarse
study boundary, not a publication of any site location.

It was chosen using only pre-score evidence:

- live official NHLE label metadata;
- live Environment Agency terrain-coverage metadata;
- private overlap checks against all 522 E001 observation centres; and
- a private overlap check against the one Phase 2F domain.

The private audit found zero E001 positive centres and zero E001 background centres inside this
cell. Every retained external positive and background must also be at least 15 km from every E001
observation centre and from the Phase 2F private domain. Exact 128 m windows must be disjoint. All
360 records previously reviewed during E001 curation are ineligible, even if they were not used for
training.

This is stronger than merely avoiding identical patches. The cell and buffer were chosen before any
external model access. It is still a geographic—not data-source—shift: both E001 and the proposed
external study use NHLE labels and the EA 1 m DTM. Conclusions must retain that limitation.

## Coordinate-safe feasibility result

The metadata audit ran on 30 August 2026 and retained no record-level rows or coordinates.

| Pre-score gate | Aggregate result |
|---|---:|
| Previously unreviewed probable-title records in the cell | 96 |
| Eligible after the 15 km E001 and Phase 2F separation checks | 87 |
| Complete nominal 128 m coverage in the EA 1 m DTM | 87/87 |
| One resolved survey-provenance signature | 86/87 |
| Terrain-provenance review needed | 1/87 |
| Verified external positives | **0 — not curated yet** |

The 87 records are a screening pool, not labels. A title that says “bowl barrow” is insufficient by
itself. The only planning estimate is that E001 retained 261 of 360 fully reviewed records (72.5%);
applying that historical yield to 87 gives approximately 63. That estimate is not a verified count
and may not transfer to this region.

## Sample size frozen before performance

The target is **120 observations: 60 positives and 60 matched unlabelled backgrounds**. The
minimum viable dataset is 100 observations: 50 matched pairs.

- If at least 60 positives pass every gate, select exactly 60 by the frozen SHA-256 ranking rule.
- If 50–59 pass, use every accepted positive and one background per positive. The smaller size is
  determined by label/terrain availability, never model performance.
- If fewer than 50 pass, stop before RF access and report `MORE_DATA_REQUIRED`.

No optional stopping, post-score expansion, or performance-driven record exclusion is allowed.

## Positive curation gate

Each positive must be a Scheduled Monument in the official National Heritage List for England and
must independently pass the E001 label philosophy:

1. the official full entry supports bowl-barrow identity;
2. one monument can be isolated;
3. surviving upstanding relief is explicitly supported;
4. designation geometry is compact, single-part, and credibly centred;
5. a complete 128 m patch has 1 m DTM coverage;
6. the patch has one resolved acquisition-provenance signature; and
7. the external cell, prior-review exclusion, and 15 km separation rules pass.

Private states are `accepted`, `rejected`, `uncertain`, and `terrain_review_needed`. Uncertain or
unresolved records cannot enter the frozen test merely to reach the target.

## Matched unlabelled backgrounds

Every positive receives exactly one `unlabelled_background`; this term does not mean
non-archaeological or archaeology-free terrain. The Phase 2C design is retained:

- deterministic area-uniform sampling in a 1–5 km annulus;
- at least 500 m from any accepted positive;
- at least 250 m from any known Scheduled Monument returned by the NHLE query;
- at least 256 m from another selected background;
- the same 25 km external cell and the same 15 km prior-study separation gate;
- exact match on terrain resolution, source survey/programme, year, and provenance signature;
- landscape matching, modern-feature screening, and no-data QA; and
- one private observation-group identifier linking each matched pair.

The known-monument exclusion is incomplete relative to local HERs, undesignated archaeology, and
unknown sites. That uncertainty is recorded rather than converted into a false-negative claim.

## Terrain and frozen model pipeline

The only allowed terrain source is the Environment Agency **LIDAR Composite Digital Terrain Model
(DTM) – 1m**, in EPSG:27700. The official dataset record describes approximately 99% coverage of
England, 1 m resolution, OGL v3 licensing, and a composite derived from time-stamped and National
LIDAR Programme surveys. Phase 3B must verify each patch and provenance signature rather than rely
on national coverage alone.

The model input remains exactly:

1. 128 × 128 pixels covering 128 m × 128 m;
2. median-normalized elevation;
3. slope in degrees;
4. hillshade at azimuth 315° and altitude 45°;
5. local relief with 16 m radius;
6. non-overlapping 4 × 4 mean pooling to 32 × 32 per channel; and
7. 4,096 terrain-only features.

The bound model is the private full-fit Random Forest with 300 trees, maximum depth 8, minimum leaf
size 5, `max_features="sqrt"`, and seed 20260829. The model-state SHA-256 is
`e3b0c072f437e889f09a2a2cf5a37f19b2f483eb5188e102b132a89ee76d1939`. Retraining,
recalibration, threshold changes, representation changes, or a new model are prohibited.

## Evaluation and uncertainty

The primary metric is **balanced accuracy** at the frozen 0.5 classification threshold. Secondary
metrics are accuracy, precision, recall, F1, ROC-AUC, average precision, and the confusion matrix.

The 95% interval uses a pre-registered nonparametric matched-pair cluster bootstrap:

- one cluster is a positive and its matched unlabelled background;
- sample the observed number of pairs with replacement;
- retain both observations whenever a pair is drawn;
- run 10,000 replicates with seed 20260830; and
- report the 2.5th and 97.5th percentiles.

This keeps both classes in every resampled pair and respects the matched sampling unit. It does not
remove the limitation of having one 25 km external region.

The interpretation rule is frozen:

- `MORE_DATA_REQUIRED`: fewer than 50 complete pairs or metrics cannot be estimated;
- `EXTERNAL_GENERALIZATION_SUPPORTED`: balanced accuracy ≥ 0.75 and its lower 95% bound > 0.5;
- `EXTERNAL_GENERALIZATION_PARTIALLY_SUPPORTED`: balanced accuracy > 0.5 but the supported rule is
  not met; and
- `EXTERNAL_GENERALIZATION_NOT_SUPPORTED`: balanced accuracy ≤ 0.5.

Every point estimate and interval must still be reported, including a poor result.

## Freeze sequence and next gate

Phase 3B may curate records and acquire terrain privately, but it may not load the RF. Before any
scoring, a separate commit must freeze:

- the complete private positive/background manifest and its checksum;
- a coordinate-safe count and provenance receipt;
- proof of zero prior-study overlap;
- all terrain and representation checksums; and
- the exact number of complete matched pairs.

Only a later, explicitly authorized one-way evaluation may load the model and calculate metrics.

## Sources and licensing

- [Historic England NHLE data downloads](https://historicengland.org.uk/listing/the-list/data-downloads)
- [Environment Agency LIDAR Composite DTM 1m](https://environment.data.gov.uk/dataset/13787b9a-26a4-4775-8523-806d13af58fc)
- [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)

Historic England describes the NHLE as the official current register of nationally protected sites
in England and publishes GIS data through its Open Data Hub. The tracked Phase 3A output is only an
aggregate feasibility receipt. Exact designations, terrain, locations, geometry, and QA imagery
remain private and Git-ignored.
