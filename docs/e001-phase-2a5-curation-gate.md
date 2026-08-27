# E001 Phase 2A.5 — curated label, geometry, and terrain gate

## Decision

**FINAL GO for D001, with Phase 2B controls.** The frozen audit produced 261 records that pass the
official-entry, single-monument, upstanding-relief, designation-geometry, 128 m terrain-coverage,
and survey-provenance gates. Twelve provisional 100 km groups contain at least 12 accepted sites,
and four pairwise nonadjacent groups are plausible holdout candidates.

This decision approves the label and terrain **source strategy** for the next phase. It is not a
model result, a final split, permission to publish coordinates, or evidence that survey confounding
has been eliminated. Phase 2A.5 downloaded no raster, sampled no background, and trained no model.

The coordinate-free result snapshot was generated on 27 August 2026 from the live source services.

## 1. Frozen target and review schema

The target remains one Scheduled Monument in England whose official Historic England entry
supports all of the following:

1. explicit bowl-barrow identity;
2. one isolatable archaeological monument;
3. surviving upstanding mound or terrain expression;
4. compact, single-part designation geometry with a credible centre;
5. complete nominal 1 m-or-better Composite DTM coverage for a provisional 128 m square; and
6. one complete survey-provenance signature across that square.

`src/archaeoai/curation.py` defines typed evidence, review, QA, and exclusion values. Accepted
records must pass every gate. Controlled exclusions distinguish type, multiplicity, relief,
geometry, coverage, and provenance problems. `src/archaeoai/terrain_metadata.py` contains the
data-free geometry and metadata checks.

Tracked rows use the stable public List Entry Number, status values, concise evidence codes, broad
group, dates, capture scale, and coarse terrain provenance. They do not contain coordinates,
National Grid References, bounding boxes, or polygons.

## 2. Deterministic geographically stratified queue

The queue contains 360 records from the Phase 2A `probable_bowl_candidate` pool. The selection
method is deterministic:

1. assign candidates to coordinate-safe 100 km British National Grid cells in memory;
2. rank records inside each cell by SHA-256 of the seed and List Entry Number; and
3. select in seeded round-robin order across all occupied cells.

The seed is `E001-Phase-2A5-2026-08-28`. This prevents a few dense areas from filling the review
queue and reproduces the same IDs independent of source ordering.

## 3. Full-entry primary review

Every one of the 360 queue IDs was loaded from its official Historic England list-entry page. The
review used the complete `Reasons for Designation` and `Details` sections, not the title alone. The
frozen rubric looked for explicit type, one usable monument, and surviving relief, and conservatively
handled cropmarks, levelled or destroyed mounds, cairns, multiple features, and insufficient text.

One page provided Reasons but no Details and was retained as uncertain. No accepted record relied on
that entry. Review notes are short classifications, not copied descriptions.

This was a structured primary review performed in one Codex session. It was not an independent
human review and no agreement statistic is claimed.

### Primary-review outcomes before spatial QA

| Outcome | Count |
|---|---:|
| Passed archaeological text rubric and moved to geometry QA | 311 |
| Clear archaeological rejection | 22 |
| Insufficient evidence / uncertain | 27 |
| Total | 360 |

The 22 clear archaeological exclusions comprise two cairns, one cropmark-only record, 12 without
surviving upstanding relief, and seven without adequate bowl-barrow identity in the official text.

## 4. Designation geometry QA

Exact EPSG:27700 polygons and source centroids were fetched transiently from the official NHLE
Scheduled Monuments layer. The code required:

- one exterior polygon part;
- the source centre to lie inside that part;
- the source centre to remain near the polygon's calculated planar centroid;
- designation area no greater than 0.5 ha; and
- maximum polygon span no greater than 200 m.

All 311 records forwarded from text review passed these checks. There were no missing, multipart,
off-centre, or unusually large cases in this selected queue under the frozen thresholds. This does
not turn a designation boundary into a mound segmentation mask. Phase 2B must retain that distinction
when it defines patch centres and performs terrain visual checks.

No exact geometry was written to a tracked artifact.

## 5. Terrain coverage and provenance

For each of the 311 geometry-passed records, the runner queried the official Environment Agency /
Defra OGC Features index around a provisional 128 m square. Nine test points—the centre, corners,
and edge midpoints—had to fall inside 1 m-or-better Composite DTM extent polygons.

| Terrain QA result | Count |
|---|---:|
| Full patch coverage | 308 |
| No 1 m coverage | 2 |
| Incomplete patch-edge coverage | 1 |
| Metadata-query errors in the final low-concurrency run | 0 |

Provenance had to supply polygon ID, source year, source resolution, flight start and end dates,
and an identifiable source survey/programme. A patch intersecting more than one provenance
signature was not accepted automatically.

| Provenance QA result | Count |
|---|---:|
| One complete usable signature | 261 |
| Mixed signatures requiring terrain review | 47 |
| Failed provenance | 0 |

Among the 261 accepted records, 258 use the National LIDAR Programme source and three use another
identified EA Composite source survey. Source resolution is 1 m for 259 and 0.5 m for two. Observed
source years range from 2009 to 2022: 2009 (1), 2016 (2), 2017 (11), 2018 (65), 2019 (38), 2020
(75), 2021 (59), and 2022 (10). NHLE capture scale is 1:10,000 for 257 and 1:2,500 for four.

The 47 mixed-signature patches remain `needs_terrain_review`; they are not part of the 261 accepted
pool. A programme-restricted sensitivity set can remove the three non-National-Programme records and
still retain 258 positives.

## 6. Verified final status counts

The five statuses partition all 360 reviewed records.

| Final status | Count |
|---|---:|
| `accepted` | 261 |
| `rejected` | 25 |
| `uncertain` | 27 |
| `needs_geometry_review` | 0 |
| `needs_terrain_review` | 47 |

The 25 rejections are the 22 archaeological exclusions plus the three terrain-coverage failures.
Geometry failures are zero. Terrain-provenance failures are zero; 47 mixed-provenance cases remain
unresolved and excluded from the accepted count.

## 7. Provisional geographic groups

The 261 accepted sites occupy 23 coarse 100 km cells. A provisional group is considered viable at
12 or more accepted positives for this decision gate. Twelve groups meet that rule:

| Provisional group | Accepted |
|---|---:|
| `BNG_100KM_E2_N0` | 14 |
| `BNG_100KM_E2_N1` | 14 |
| `BNG_100KM_E3_N1` | 15 |
| `BNG_100KM_E3_N2` | 16 |
| `BNG_100KM_E3_N3` | 16 |
| `BNG_100KM_E3_N5` | 15 |
| `BNG_100KM_E4_N2` | 14 |
| `BNG_100KM_E4_N3` | 12 |
| `BNG_100KM_E4_N5` | 15 |
| `BNG_100KM_E5_N1` | 12 |
| `BNG_100KM_E5_N2` | 13 |
| `BNG_100KM_E5_N4` | 15 |

The deterministic nonadjacency rule selected four possible holdouts:

- `BNG_100KM_E3_N2` — 16 accepted;
- `BNG_100KM_E3_N5` — 15 accepted;
- `BNG_100KM_E5_N4` — 15 accepted; and
- `BNG_100KM_E2_N0` — 14 accepted.

No pair shares an edge or corner. These are candidates only. Phase 2B must define buffers, examine
site clustering and patch autocorrelation, and calculate uncertainty before freezing a split.

## 8. Terrain-provenance confound finding

The accepted pool is not fatally separated by resolution or capture scale: every accepted terrain
source is 1 m or better, 98.9% use the National LIDAR Programme, and 98.5% of designation geometries
were captured at 1:10,000. Survey year nevertheless varies geographically, and three groups have
only one observed accepted-site survey year.

A positive-only audit cannot show that a classifier will not learn survey characteristics. The
required Phase 2B control is to sample backgrounds inside the same geographic/acquisition strata,
record the same provenance fields for positives and backgrounds, report per-group provenance, and
run a National-Programme-only sensitivity analysis. If matched backgrounds cannot be formed, the
split must be redesigned.

## 9. Second-review system

The tracked queue contains 40 deterministic records: 20 accepted, 12 needing terrain review, five
rejected, and three uncertain. Every row requests `independent_human_full_entry_review`.

No second reviewer has completed this queue. There is no inter-reviewer agreement estimate. Before
publication or a strong label-reliability claim, a different human reviewer should apply the frozen
rubric blind to the primary decision, disagreements should be adjudicated, and outcomes should be
recorded without coordinates.

## 10. Privacy and recreation

`data/private/` is ignored by Git. The local full-entry evidence cache is stored there and is not
tracked. It contains only the official Reasons and Details sections for the fixed IDs—no National
Grid Reference, coordinate, map, or polygon. Exact NHLE geometry and EA index geometry are held in
memory during the run and discarded.

To recreate the audit:

1. run `curate_e001_labels.py --print-queue` to reproduce the 360 stable IDs;
2. load each official Historic England entry and record its Reasons and Details into the ignored
   `data/private/e001_full_entry_reviews.json` input schema;
3. run `curate_e001_labels.py` at low concurrency; and
4. verify that the access date and live source version are recorded before comparing counts.

Tracked outputs deliberately make source records auditable through public IDs without publishing a
machine-ready coordinate table.

## 11. Gate checklist

| Condition | Result |
|---|---|
| At least 250 fully reviewed and terrain-usable positives | **PASS — 261** |
| At least eight viable provisional groups | **PASS — 12** |
| At least two nonadjacent holdout candidates | **PASS — 4** |
| Complete 1 m-or-better patch coverage | **PASS for all 261 accepted** |
| Complete single-signature provenance | **PASS for all 261 accepted** |
| No fatal observed provenance confound | **PASS with mandatory Phase 2B matching/sensitivity control** |
| Exact coordinates and polygons absent from Git | **PASS** |
| Independent label review completed | **NOT YET — 40-record queue prepared** |

The independent review is a reliability follow-up, not grounds to relabel unreviewed records as
accepted. D001 moves to FINAL GO because the accepted pool meets the numeric,
geographic, terrain, provenance, and privacy gate without counting those unresolved records.

## Reproduction

From the installed project environment:

```powershell
.\.venv\Scripts\python.exe .\scripts\curate_e001_labels.py --print-queue
.\.venv\Scripts\python.exe .\scripts\curate_e001_labels.py --terrain-workers 2
```

The second command requires the ignored review input and network access to official metadata
services. It writes only the coordinate-free files in `outputs/feasibility/`.
