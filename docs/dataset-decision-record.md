# Dataset decision record — D001

## Final decision: NHLE bowl-barrows and EA Composite DTM pass the Phase 2A.5 gate

Phase 2A found a large, geographically broad pool of Scheduled Monument titles that plausibly
represent single bowl barrows. Historic England publishes the official NHLE layer under OGL, and a
30-record full-entry sample showed strong but imperfect title precision. See
[the Phase 2A audit](e001-feasibility-audit.md).

**Decision status: FINAL GO for Phase 2B planning.** A deterministic 360-record audit produced 261
positives that pass official full-entry review, designation-geometry QA, provisional 128 m terrain
coverage, and complete single-signature provenance. Twelve provisional groups contain at least 12
accepted sites and four pairwise nonadjacent groups are possible holdouts. See the
[Phase 2A.5 gate](e001-phase-2a5-curation-gate.md).

This approves the source strategy, not a final split or a model experiment. Phase 2B must match
backgrounds within geography and acquisition strata, run a National-LIDAR-Programme-only sensitivity
analysis, complete controlled attribution, and retain exact coordinates outside Git. Forty records
still require an actual independent human reliability review; no agreement claim is permitted yet.

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
