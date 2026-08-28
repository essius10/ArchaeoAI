# E001 Phase 2B.5 — full positive-terrain acquisition and freeze

**Decision: GO FOR BACKGROUND AND SPLIT DESIGN**

**Acquisition date:** 28 August 2026

**Freeze audit completed:** 29 August 2026

**Scope:** approved positive terrain only; no background, split, model, metric, prediction, site
search, or archaeological discovery.

## Outcome

Phase 2B.5 produced a complete, controlled positive-terrain dataset for the 261 accepted E001
scheduled single bowl-barrow records. Five valid pilot artifacts were checksum-verified and reused;
256 new 128 m windows were requested from the Environment Agency WCS. Every raw patch and every
frozen representation passed the automatic gates.

| Gate | Count |
|---|---:|
| Accepted labels | 261 |
| Terrain attempted | 261 |
| Pilot caches reused | 5 |
| New bounded WCS downloads | 256 |
| Raw terrain passed / failed | 261 / 0 |
| Four-representation archives passed / failed | 261 / 0 |
| Request retries / failures | 0 / 0 |

The two-worker run began at `2026-08-28T07:09:35Z`, ended at `07:12:46Z`, and took 190.919
seconds. The interrupted Codex session occurred after acquisition and initial cache revalidation;
resumption reused the complete cache and made no additional Environment Agency request.

## Acquisition and resume policy

`scripts/acquire_e001_full_terrain.py` performs one bounded 128 m WCS request per missing or invalid
approved sample. It uses at most four workers, defaults to two, applies bounded retries with backoff,
checks response type, size, completeness, and TIFF signature, writes through a partial file, and
atomically accepts only a raster that passes QA. A private state record is written after each site.

On resume, the runner verifies the expected raw checksum, reopens the GeoTIFF, regenerates the four
representations, and verifies the processed archive. A valid cache is skipped; a bad artifact is
reason-coded and quarantined rather than silently repaired. The full run observed no network,
service, raster, or representation failure, so no quarantine was needed.

## Raw and representation QA

Every patch was independently reopened during the freeze audit. All 261 matched their raw-file,
terrain-content, and processed-file SHA-256 digests. Each patch was EPSG:27700, 1 m resolution,
128×128 pixels, pixel-aligned to its requested 128 m footprint, finite, and within the broad
engineering elevation guard. No patch contained no-data.

The observed raw elevation minima across patches ranged from approximately −0.005 m to 478.872 m;
the observed maxima ranged from 2.004 m to 485.528 m. These are dataset QA statistics, not
archaeological measurements.

Every processed archive contains exactly:

1. median-normalized elevation;
2. slope in degrees;
3. fixed 315° azimuth / 45° altitude hillshade;
4. 16 m-radius local relief.

Shapes, no-data propagation, finite ranges, representation completeness, and deterministic
regeneration passed for all 261. No new representation was added and no parameter was tuned using
model performance.

## Eight cross-cell cases

All eight predicted 5 km cell-boundary cases were present. The WCS responses supplied a complete
128×128 footprint with the expected transform and dimensions. Eight internal boundaries were
checked: none had a duplicated boundary row or column. The largest median elevation step at a cell
boundary was 0.184 m and ranked at the 78.95th percentile of ordinary adjacent-pixel steps within
its patch, rather than as an exceptional discontinuity. Slope and local-relief generation passed.

All eight were also included in the private visual sample. No obvious acquisition seam or derived
boundary artifact was observed. Exact sites, boundary positions, and figures remain private.

## Deterministic visual QA

The private sample contains 25 patches selected before inspection using a recorded seed. It spans
17 geographic groups, every one of the eight survey-year/provenance combinations, all eight
cross-cell cases, all seven overlap components, and six records from the small/large ends of the
description-derived diameter distribution.

Each private panel presents raw elevation, normalized elevation, slope, hillshade, and local relief.
All 25 passed technical visual QA: no missing terrain, invalid clipping, bad processing, or obvious
cell seam was found. The observations below are terrain confounds, not archaeological
interpretations or discoveries.

| Aggregate visual observation | Panels |
|---|---:|
| Extreme local object | 12 |
| Modern linear feature | 11 |
| Forestry striping | 5 |
| Strong local contrast | 5 |
| Road or track | 4 |
| Steep terrain | 4 |
| General terrain striping | 2 |
| Building or structure | 1 |
| Smooth low relief | 1 |
| Unusual local objects | 1 |

A panel may have more than one observation. These findings strengthen the need for matched
backgrounds, explicit modern-feature policy, and future error analysis; they do not invalidate the
positive terrain freeze.

## Seven overlapping positive pairs

All seven overlaps are pairs of distinct scheduled entries within one provisional geographic group.
Their official descriptions distinguish separate mounds, dimensions, or landscape positions; two
explicitly describe members of a pair or line of barrows. Raw, patch-content, and processed
checksums are unique, so none is an exact terrain duplicate.

Every pair is classified `retain_grouped`. Each receives a stable `overlap_group_id` in the safe
terrain index. A future split generator must assign an entire overlap group to one partition. No
observation was deleted, merged, or assigned to a split in this phase.

## Coordinate-safe index, manifest, and privacy

`outputs/terrain/e001_terrain_index.csv` has 261 unique opaque sample IDs and 261 unique permitted
public source IDs. It records only coarse provisional groups, opaque provenance and overlap IDs,
survey year, resolution, patch size, versions, QA states, safe checksums, and a cross-cell flag. It
contains no easting, northing, NGR, geometry, WCS bounds, tile ID, path, or coordinate table.

The real manifest records 261 requested, 261 acquired, zero rejected, access date, source/service
metadata, acquisition and processing versions, sensitivity, controlled storage, and the aggregate
inventory digest. The digest covers sorted opaque sample IDs and raw, content, and processed
checksums; it contains no coordinates.

Raw GeoTIFFs, processed NPZ files, private state, review receipts, and non-georeferenced PNGs remain
under ignored `data/private/`. No bulk or coordinate-bearing file is tracked.

## Storage and estimate comparison

| Controlled category | Actual bytes | Approximate MiB |
|---|---:|---:|
| Raw GeoTIFFs | 17,214,255 | 16.42 |
| Processed NPZ archives | 58,522,332 | 55.81 |
| Private QA PNGs | 2,518,093 | 2.40 |
| Private metadata, cache, and receipts | 1,297,578 | 1.24 |
| Total controlled E001 data | 79,564,680 | 75.88 |

The raw total exactly matched the Phase 2B estimate. Processed storage was 1,718,765 bytes (2.85%)
below the 60,241,097-byte estimate. The 190.919-second two-worker acquisition was 511.081 seconds
shorter than the deliberately conservative 702-second sequential pilot projection; the comparison
does not promise future service speed.

## Aggregate coverage and provenance

The 261 patches span 23 occupied 100 km BNG groups, with 3–16 records per occupied group. Survey
years are 2009 (1), 2016 (2), 2017 (11), 2018 (65), 2019 (38), 2020 (75), 2021 (59), and 2022
(10). There are eight opaque terrain-provenance IDs: 258 records are attributed to the National
LIDAR Programme and three to an EA Composite source survey. Every source resolution is 1 m.

These remain provisional grouping and provenance facts. No train, validation, or test assignment
exists.

## Outstanding limitations and scope boundary

- CPython 3.12 reference-runtime reproduction is outstanding because only CPython 3.14.7 is
  installed on this machine. No system runtime was installed in this phase.
- The frozen 40-record independent human label review is outstanding. Codex's work is not a second
  independent archaeological review.
- Accepted records are curated research positives, not unquestionable ground truth or segmentation
  masks.
- Unknown terrain is not a verified negative. No background sample exists.
- No geographic split is frozen, no model is trained, and no performance or discovery claim exists.

## Gate decision

The complete positive dataset has 261 QA-passed patches, all frozen representations, valid
cross-cell cases, explicit overlap constraints, preserved provenance, and a passing privacy
boundary.

**Phase 2B.5 decision: GO FOR BACKGROUND AND SPLIT DESIGN.** This permits a separately approved
design phase only. It does not itself authorize background generation, split assignment, machine
learning, evaluation, prediction, unknown-terrain search, or a website.
