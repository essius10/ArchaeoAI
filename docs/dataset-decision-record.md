# Dataset decision record — D001

## Decision pending: select a lawful, non-sensitive label source before data download

### Candidate terrain source

England Environment Agency National LIDAR Programme DTM (reported 1 m coverage). This is attractive because it is public, national in scale, and relevant to earthwork microtopography.

### Required label criteria

1. Public, documented provenance and explicit reuse terms.
2. A single feature class whose morphology is interpretable from a DTM.
3. At least 3 geographically separated regions with enough labels in each.
4. Coordinates may be stored privately; public releases must use aggregated, masked, or permission-cleared representations.
5. Evidence of condition/date and source uncertainty where available.

### Leading study design

Use a documented, non-sensitive class such as scheduled earthwork remains only if a lawful source supports it. Sample negatives in the same regional/acquisition strata, excluding buffers around all known labels. Hold out one region entirely.

### Rejection criteria

Reject a source if its terms prohibit extraction/redistribution, it exposes vulnerable locations without a mitigation plan, labels are not spatially precise enough for patch creation, or it cannot support regional separation.

### Data registry schema

Each entry must record: source URL, access date, license/terms, CRS, resolution, vertical datum, acquisition date, tile ID, checksum, processing command/version, label provenance, and sensitivity classification.
