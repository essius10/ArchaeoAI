# Dataset decision record — D001

## Conditional decision: NHLE bowl-barrows pass metadata feasibility, not final data approval

Phase 2A found a large, geographically broad pool of Scheduled Monument titles that plausibly
represent single bowl barrows. Historic England publishes the official NHLE layer under OGL, and a
30-record full-entry sample showed strong but imperfect title precision. See
[the Phase 2A audit](e001-feasibility-audit.md).

**Decision status: CONDITIONAL GO.** D001 is not finally approved for terrain extraction. Exact
labels must still pass full-entry review, geometry QA, Environment Agency 1 m DTM coverage and
survey-provenance checks, geographic grouping, attribution review, and controlled-coordinate
handling.

### Candidate terrain source

England Environment Agency National LIDAR Programme DTM (reported 1 m coverage). This is attractive because it is public, national in scale, and relevant to earthwork microtopography.

Phase 2A verified the Environment Agency 2022 LIDAR Composite DTM as the initial candidate: nominal
1 m resolution, approximately 99% England coverage, EPSG:27700, Ordnance Datum Newlyn, 5 km GeoTIFF
tiles, and OGL. Its survey index exposes source resolution and acquisition dates. Composite survey
heterogeneity remains a mandatory confound check.

### Required label criteria

1. Public, documented provenance and explicit reuse terms.
2. A single feature class whose morphology is interpretable from a DTM.
3. At least 3 geographically separated regions with enough labels in each.
4. Coordinates may be stored privately; public releases must use aggregated, masked, or permission-cleared representations.
5. Evidence of condition/date and source uncertainty where available.

### Leading study design

Use scheduled single bowl barrows that survive as discrete upstanding mounds, after full official-
entry and geometry review. Sample backgrounds in the same regional/acquisition strata, excluding
buffers around all known labels. Use multiple buffered geographic groups, with at least two
nonadjacent final test groups if the audited set permits it.

### Rejection criteria

Reject a source if its terms prohibit extraction/redistribution, it exposes vulnerable locations without a mitigation plan, labels are not spatially precise enough for patch creation, or it cannot support regional separation.

### Data registry schema

Each entry must record: source URL, access date, license/terms, CRS, resolution, vertical datum, acquisition date, tile ID, checksum, processing command/version, label provenance, and sensitivity classification.
