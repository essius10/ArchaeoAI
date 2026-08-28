# E001 Phase 2C — unlabelled backgrounds and frozen validation splits

**Decision: GO FOR BASELINE MODELLING, subject to explicit Phase 2D approval.**

Phase 2C freezes the coordinate-safe E001 modelling dataset and two evaluation conditions. It does
not train a model, compute predictive metrics, inspect predictions, or claim archaeological
discovery.

## Dataset meaning and size

E001 now contains 522 QA-passed observations:

- 261 `positive_bowl_barrow` patches from the frozen Phase 2B.5 positive dataset;
- 261 `unlabelled_background` patches generated at a pre-specified 1:1 ratio;
- 254 independent assignment groups after the seven retained two-positive overlap components are
  treated as inseparable.

`unlabelled_background` means only that no target bowl-barrow label was known at the sampled
location under the exclusions used here. It does not mean no archaeology exists. The forbidden
interpretations `true_negative`, `non_archaeology`, and `no_archaeology` are not dataset labels.

The 1:1 ratio was chosen before modelling. It gives every curated positive one matched background,
keeps the primary comparison balanced and interpretable, and avoids allowing a large background
pool to dominate the first baseline. A 2:1 ratio was considered but deferred; 5:1 or greater may be
used only as a later, separately declared prevalence stress test. No ratio was selected from model
performance.

## Frozen background unit and processing

Each background is a 128 m × 128 m, 1 m-resolution Environment Agency LIDAR Composite DTM patch in
EPSG:27700. It uses the same extraction, no-data threshold, raster validation, checksum logic,
processing version, and four representations as a positive:

1. per-patch median-normalized elevation;
2. slope in degrees;
3. fixed 315° / 45° hillshade;
4. 16 m-radius local relief.

There is no class-specific array shape, image format, or transformation. Class labels come from the
safe modelling index, not filenames. Raw elevation is retained privately for QA but is not one of
the four frozen model representations; this matters because the descriptive audit found different
absolute-elevation distributions between classes.

## Deterministic sampling policy

Version `e001-background-v1` uses seed `E001-Phase-2C-2026-08-29`. For each positive, SHA-256-derived
angle and area-uniform radius values generate candidates in a 1–5 km annulus. Stable opaque IDs and
tie-breaking make reruns deterministic. Exact coordinates and candidate histories remain ignored
under `data/private/`.

An accepted candidate must:

- stay in the associated positive's 100 km BNG group;
- be at least 500 m from every positive centre;
- be at least 256 m from every previously selected background centre;
- have no intersecting Scheduled Monument in a conservative 250 m square query envelope;
- match the associated positive's exact EA survey year, programme, source resolution, and
  provenance ID;
- pass the same 128×128 raster and representation QA.

The 500 m positive exclusion exceeds the 128 m footprint and leaves room for designation
uncertainty, complexes, nearby earthworks, and spatial autocorrelation. The 256 m background spacing
prevents overlapping or immediately adjacent background windows without forcing samples into
unrelated landscapes. These distances were selected before modelling and are not tunable from
scores.

## Known archaeology and lawful source use

Candidate selection transiently queried the Historic England National Heritage List for England
(NHLE) Scheduled Monuments layer. Historic England provides NHLE spatial downloads and services
through its Open Data Hub and identifies Scheduled Monuments as available spatial data. Its Open
Data terms apply the Open Government Licence v3.0 and require source acknowledgement. Only safe
aggregate counts and service provenance are tracked; no national coordinate cache or exclusion
geometry is committed.

This is a limited exclusion, not proof of archaeology-free terrain. It does not exhaust local
Historic Environment Records, undesignated archaeology, inaccurate coordinates, or unknown sites.

Sources accessed 29 August 2026:

- [Historic England NHLE data downloads](https://historicengland.org.uk/listing/the-list/data-downloads/)
- [Historic England Open Data Hub terms](https://historicengland.org.uk/terms/website-terms-conditions/open-data-hub/)
- [National Heritage List for England](https://historicengland.org.uk/listing/the-list)

## Modern-feature and hard-confound policy

A candidate is technically invalid if the terrain is largely occupied by a major building complex,
major water body, quarry/excavation, or sharply engineered occupation, or if raster QA fails. Roads,
tracks, field boundaries, drainage, forestry striping, and difficult anthropogenic relief are valid
hard backgrounds unless they meet that invalid threshold. Difficult terrain is not removed merely
because it could confuse a later model, and a background is never rejected because it looks
barrow-like.

The 40-record pilot included a deterministic private 25-record visual review spanning all 23
groups and all eight year/provenance combinations. All 25 passed technical review. The retained
observations included 10 road/track, eight field-boundary/drainage, nine forestry-pattern, and seven
hard-anthropogenic-relief flags; records can have more than one flag. No sample met the hard-invalid
threshold.

## Staged evidence

The required sequence was followed:

1. 112 synthetic tests passed before real background acquisition;
2. 10/10 real backgrounds passed raster and representation QA;
3. 40/40 real backgrounds passed; 25/25 deterministic private visual examples passed;
4. the pilot showed all 23 groups and all eight provenance combinations, with realistic hard
   confounds retained;
5. only then was the full dataset produced;
6. 261/261 full backgrounds passed raw and four-representation QA.

The full sampler evaluated 573 candidates. Of the 312 rejected candidates, 46 intersected the
Scheduled Monument exclusion, 40 lacked required terrain, 64 crossed the coarse group boundary,
156 mismatched provenance, and six violated the positive buffer. There were zero WCS retries and
zero post-selection terrain failures.

## Provenance and geography controls

Every background is matched to its associated positive's joint coarse group, survey year, and exact
provenance ID. Consequently, class counts are exactly equal in every observed
group/provenance/year cell: 23 geographic groups, eight provenance IDs, and eight survey years.
There is no observed class/provenance or class/coarse-geography association in those counts.

This does not make local landscape identical. The aggregate descriptive audit found:

| Patch-level quantity | Positives median (IQR) | Backgrounds median (IQR) |
|---|---:|---:|
| Raw median elevation, m | 161.96 (76.93–227.76) | 101.05 (53.07–182.15) |
| Mean slope, degrees | 3.60 (2.58–5.81) | 4.06 (2.69–7.23) |
| Mean absolute 16 m local relief, m | 0.150 (0.102–0.254) | 0.160 (0.097–0.297) |

Absolute elevation is therefore a documented imbalance, but it is removed from the frozen
median-normalized elevation representation. Slope and relief distributions overlap substantially;
their residual differences remain a limitation to inspect after, not before, the final test is
evaluated.

## Observational hierarchy and overlap constraints

The assignment hierarchy is:

`terrain representation → sample → matched observation group → overlap component → BNG block`.

Each ordinary positive and its background share one observation group. Each of the seven retained
overlapping-positive pairs and both associated backgrounds share one observation group and the same
overlap-component ID. All four records must remain in one partition. Representations are never split
as separate observations.

## Frozen random condition

The comparison condition uses SHA-256-ranked observation groups and seed
`E001-group-aware-random-v1-2026-08-29`. It is group-aware, not naive patch randomization. It freezes
the same class counts as the geographic condition:

| Partition | Positives | Backgrounds | Total |
|---|---:|---:|---:|
| Train | 216 | 216 | 432 |
| Development | 14 | 14 | 28 |
| Final test | 31 | 31 | 62 |

The assignment SHA-256 in the random manifest is a change guard. Any assignment change invalidates
the manifest and must be treated as a new split version.

## Frozen geographic condition

Complete 100 km BNG blocks define the primary evaluation condition:

- development: `BNG_100KM_E2_N0` — 14 positives and 14 matched backgrounds;
- final test: `BNG_100KM_E3_N2` and `BNG_100KM_E5_N4` — 31 positives and 31 matched backgrounds;
- train: all remaining blocks — 216 positives and 216 matched backgrounds.

The two final-test block envelopes are nonadjacent with a 141.421 km lower-bound separation. They
were selected before modelling because together they provide two separated regions and 31 positive
examples. `BNG_100KM_E3_N5` was not selected because it is a single, smaller test block;
`BNG_100KM_E4_N5` was not selected because of concentrated provenance; `BNG_100KM_E2_N0` was
reserved for development because it contains 14 positives across five provenance IDs.

The coordinate-private freeze audit also enforces a 1 km minimum centre-to-centre buffer across all
geographic partitions. It found zero violations. Only that threshold and aggregate result are
tracked; exact nearest-neighbour distances remain private.

A train/development/final-test structure is justified at this sample size: development permits
threshold or representation decisions without viewing the final geographic result, while the final
test still has 31 positives across two regions. The final assignment digest is frozen in the
geographic manifest.

## Leakage, duplicate, and privacy audit

The coordinate-private audit found:

- zero duplicate sample IDs and zero duplicate terrain-content checksums;
- zero positive/background 500 m buffer violations;
- zero background/background 256 m spacing violations;
- zero geographic assignment mismatches;
- zero cross-partition terrain-window overlaps in either condition;
- zero 1 km cross-partition centre-buffer violations in the geographic condition;
- all 254 observation groups and all seven overlap components intact;
- exact frozen-assignment digest matches for both conditions.

Tracked indexes contain opaque IDs, coarse groups, provenance, QA, safe group relationships,
checksums, and split labels. They exclude Easting, Northing, bounding boxes, geometry, exact distance
to positives, and reconstructable sampling coordinates. Raw TIFFs, processed NPZ archives, private
QA figures, and coordinate-bearing state remain ignored.

## Machine-readable evidence

- `outputs/background/e001_background_index.csv`
- `outputs/background/e001_background_full_summary.json`
- `outputs/background/e001_background_pilot40_visual_qa.json`
- `outputs/dataset/e001_modelling_index.csv`
- `outputs/dataset/e001_random_split_manifest.json`
- `outputs/dataset/e001_geographic_split_manifest.json`
- `outputs/dataset/e001_dataset_audit.json`

## Limitations and remaining gates

- A different human reviewer has not completed the frozen 40-record label review.
- CPython 3.12 reference-runtime reproduction remains outstanding; work is verified locally on
  CPython 3.14.7.
- Scheduled Monument exclusion is incomplete relative to all known and unknown archaeology.
- Coarse geographic/provenance matching does not perfectly match local landscape.
- The final geographic test must remain untouched during Phase 2D development.
- No model, metric, prediction, discovery, or generalization result exists yet.

Phase 2D may begin only after explicit approval.
