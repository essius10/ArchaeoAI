# E001 Phase 2B — bounded terrain pilot and dataset foundation

**Decision: GO FOR FULL TERRAIN DATASET**

**Decision date:** 28 August 2026

**Scope:** terrain acquisition and deterministic preprocessing only; no background set, split, model,
metric, prediction, or archaeological discovery.

## What passed

The required sequence was followed:

1. synthetic raster metadata, clipping, boundary, multi-source mosaic, no-data, and representation
   tests;
2. one real approved record acquired and visually checked;
3. five real records from distinct provisional geographic groups and survey years;
4. aggregate-only workload and spatial-integrity estimation for all 261 accepted records;
5. no full acquisition was started.

The five-site pilot passed 5/5. Each response was a 128×128 pixel, 1 m, EPSG:27700 GeoTIFF with
0% no-data. The tracked evidence is in `outputs/terrain/`; raw rasters, arrays, exact locations,
receipts, and QA PNGs remain in ignored controlled storage.

## Runtime decision

Phase 2B adds only:

- NumPy `>=2.5,<3` for terrain arrays and deterministic transforms;
- Rasterio `>=1.5,<2` for GDAL-backed GeoTIFF I/O, mosaics, windows, and metadata;
- PyProj `>=3.7,<4` for explicit CRS validation.

NumPy 2.5.2, Rasterio 1.5.1 with GDAL 3.12.4, and PyProj 3.7.2 with PROJ 9.5.1 installed and
passed on CPython 3.14.7. Official PyPI files were checked for CPython 3.12 and 3.14 Windows x86-64
wheels before installation. CPython 3.12 is not installed on this machine, so reference-runtime
reproduction remains outstanding and is not claimed.

No Shapely, GeoPandas, Pandas, SciPy, matplotlib, scikit-learn, PyTorch, or TensorFlow dependency was
added.

## Terrain source and access

| Field | Recorded value |
|---|---|
| Dataset | Environment Agency LIDAR Composite Digital Terrain Model (DTM) — 1 m |
| Dataset record | `13787b9a-26a4-4775-8523-806d13af58fc` |
| Edition | 2022 composite; dataset record revised 15 December 2023 |
| Survey period represented | through 2 April 2022 |
| Licence | Open Government Licence v3.0 |
| Attribution | © Environment Agency copyright and/or database right 2022. All rights reserved. |
| Horizontal CRS | EPSG:27700, OSGB36 / British National Grid |
| Vertical datum | Ordnance Datum Newlyn |
| Nominal output resolution | 1 m |
| Access | Persistent Environment Agency WCS 2.0.1 endpoint, bounded `GetCoverage` |
| Coverage | `…__Lidar_Composite_Elevation_DTM_1m` |

The official product is also organized as 5 km OS National Grid tiles. E001 does not download those
complete tiles. It requests one exact 128 m window per approved site. This preserves the scientific
grid while reducing the projected raw transfer from a 20.0 GB uncompressed full-tile equivalent to
about 17.2 MB of bounded GeoTIFF responses.

The real manifest is `data/manifests/e001-ea-lidar-dtm.toml`. Its `verified` status is scoped only to
the five-site pilot, and its checksum is the digest of a sorted sample-ID/raw-GeoTIFF checksum
inventory. It does not imply that all 261 rasters have been acquired.

## Private location reconstruction

`scripts/reconstruct_e001_sites.py` reads the 261 accepted stable List Entry IDs, resolves their
current Easting/Northing attributes through the official Historic England NHLE feature service, and
writes one controlled cache under `data/private/e001/`. It verifies that its destination is both
inside `data/private/` and ignored by Git before writing.

The tracked repository contains no exact easting, northing, NGR, geometry, bounding box, WCS subset,
or georeferenced site raster. A GeoTIFF transform itself is location-bearing, so site-linked raw and
processed rasters remain under `data/private/`, not merely `data/raw/`.

## Patch specification

The primary patch is a configurable **128 m square at 1 m resolution** (128×128 pixels). This was
selected before modelling and without using any test-set performance.

A coordinate-free parser found a usable mound diameter in 184 of the 261 accepted official
descriptions: median 20 m, 90th percentile 35 m, and maximum 55 m. A 64 m square leaves almost no
context around the largest described mound. A 128 m square retains room for a surrounding ditch,
modest location/designation uncertainty, and a 16 m local-relief window. The 192 m and 256 m options
would add substantially more broad landscape context, increasing the risk that future models learn
location or landform rather than earthwork morphology. The pipeline does not hard-code input size;
configuration validation requires only an integer pixel count.

Patch centres are snapped deterministically to the 1 m BNG grid. Bounds are half-open, and 5 km grid
discovery includes every intersected cell without adding a merely touching neighbor.

## Raster core and rejection rules

The raster core:

- opens only local `.tif`/`.tiff` files;
- reads band count, data type, CRS, transform, resolution, no-data, dimensions, and bounds;
- rejects non-EPSG:27700 sources and non-1 m inputs;
- mosaics supplied sources in sorted order with a deterministic first-valid rule;
- extracts a pixel-aligned patch with an exact expected transform;
- never silently fills no-data;
- calculates SHA-256 checksums for raw artifacts and content digests for patches.

Stable rejection codes are: `crs_mismatch`, `resolution_mismatch`, `dimensions_mismatch`,
`nonfinite_values`, `nodata_excess`, `missing_coverage`, `elevation_range`,
`source_metadata_missing`, and `boundary_mismatch`. Current defaults reject a patch above 20% no-data
or outside a deliberately broad −500 to 2000 m safety interval. These are engineering guards, not
claims about archaeological terrain.

## Terrain representations

Exactly four interpretable arrays are produced:

1. **Median-normalized elevation:** `z' = z - median(z_valid)` within one patch. No statistic is
   shared across sites.
2. **Slope:** `atan(sqrt((dz/dE)^2 + (dz/dN)^2))`, reported in degrees.
3. **Hillshade:** dot product of the unit surface normal with a fixed sun vector at azimuth 315° and
   altitude 45°, clipped to `[0, 1]`.
4. **Local relief:** elevation minus a no-data-aware square-window mean with a 16 m radius.

Masked pixels remain non-finite in derived arrays. No global normalization parameter is learned. If
Phase 2C later requires a fitted normalization, it must be fitted on training groups only.

## Pilot evidence

| Safe sample | NHLE ID | Provisional group | Survey year | 5 km cells | Raw size | No-data | QA |
|---|---:|---|---:|---:|---:|---:|---|
| `E001P-c13d981438dd` | 1009114 | `BNG_100KM_E3_N4` | 2020 | 1 | 65,955 B | 0% | Pass |
| `E001P-dbe1e64705ea` | 1012089 | `BNG_100KM_E4_N4` | 2018 | 1 | 65,955 B | 0% | Pass |
| `E001P-398e3e398328` | 1020357 | `BNG_100KM_E5_N1` | 2021 | 1 | 65,955 B | 0% | Pass |
| `E001P-7fcb5e488cac` | 1021126 | `BNG_100KM_E5_N3` | 2017 | 1 | 65,955 B | 0% | Pass |
| `E001P-a686988f538b` | 1011521 | `BNG_100KM_E3_N1` | 2019 | 1 | 65,955 B | 0% | Pass |

Local 2×2 QA mosaics use normalized elevation, hillshade, slope, and local relief in that order.
They intentionally contain no geotransform and remain ignored. All five were visually inspected.
No seam, empty quadrant, or processing failure was seen. The images did show heterogeneous forestry
striping, linear features, isolated local objects, and contrast saturation. Those observations
reinforce the need for provenance-matched backgrounds and modern-feature screening; they do not
identify archaeology and are not model results.

## Full acquisition estimate

| Quantity | Estimate / verified count |
|---|---:|
| Accepted sites / required bounded WCS requests | 261 / 261 |
| Metadata-screened complete coverage | 261 |
| Pixel-verified complete coverage | 5 |
| Unique intersected 5 km cells if tile download were used | 200 |
| Sites crossing a 5 km cell boundary | 8 |
| Estimated bounded raw WCS transfer | 17,214,255 B (16.4 MiB) |
| Estimated compressed processed storage | 60,241,097 B (57.5 MiB) |
| Deterministic uncompressed arrays | 89,800,704 B (85.6 MiB) |
| Full-cell uncompressed alternative | 20,000,000,000 B (18.6 GiB) |
| Pilot-rate sequential runtime | ~702 s (~11.7 min) |

The storage and time projections extrapolate five samples and do not include service variability,
rate limits, or retry delays. “Metadata-screened complete” is not the same as pixel-verified. Full
acquisition should retain per-request retries and reject any site that fails raster QA.

Across the 261 private centres there were no exact-location duplicates. Seven 128 m patch pairs
overlap; all are within the same provisional geographic group. No cross-group overlap was found.
Those overlapping pairs must remain together and must not be treated as independent evidence in a
future split.

## Coordinate-safe dataset index

`outputs/terrain/e001_terrain_index.csv` contains one row per successfully generated pilot patch:
opaque sample ID, public NHLE ID, provisional coarse group, opaque terrain-provenance ID, survey
year, source resolution, processing version, patch size, representation availability, QA status,
and a private-patch content digest. It contains no coordinate, extent, tile ID, geometry, or file
path. Duplicate sample IDs and duplicate source observations are rejected.

## Background and split boundary

Phase 2B creates only a policy contract. Future samples must be labelled
`unlabelled_background`, never `true_negative`, and must support positive/known-archaeology
exclusion buffers, landscape and survey-provenance matching, provisional geographic groups,
deterministic seeds, minimum separation, modern-feature screening, and terrain-QA rejection.

No background was generated. No train/test assignment or holdout was finalized. The seven observed
positive-patch overlaps must inform the future grouping/buffer design.

## Known service behavior and failed attempts

- The persistent EA WCS endpoint and `DescribeCoverage` request succeeded. A first local PowerShell
  attempt constructed an invalid URI because `?` followed an unbraced variable name; it failed
  before any HTTP request and was corrected with explicit variable bracing.
- WCS `GetCoverage` returns the no-data sentinel `-3.4028235e+38`; Rasterio correctly exposes it as
  masked data.
- The first intentionally non-georeferenced QA PNG emitted Rasterio's expected
  `NotGeoreferencedWarning`. The writer now suppresses only that warning because removing location
  metadata is the privacy requirement.
- A first idempotent rerun reused the five local GeoTIFFs and therefore made the network-time
  estimate too optimistic. An explicit `--refresh` mode was added; a bounded five-response refresh
  preserved every checksum and supplies the reported ~702 s full-dataset projection.
- No real pilot download failed and no failed patch was concealed.

## Remaining blockers and next gate

- Re-run the complete suite in a clean CPython 3.12 environment.
- Complete the frozen 40-record independent human label review.
- Acquire and pixel-validate the remaining 256 positive patches only after this gate is accepted.
- Review the seven overlapping pairs before any split.
- Specify and review lawful other-archaeology and modern-feature exclusion data.
- Generate matched `unlabelled_background` only in the next approved phase.
- Freeze splits and normalization only after dataset QA; do not train until Phase 2C is explicitly
  approved.

**Phase 2B decision: GO FOR FULL TERRAIN DATASET.** This is permission evidence for a bounded
positive-terrain acquisition step, not approval to start Phase 2C or machine learning.
