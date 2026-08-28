# Data directory

No archaeological or terrain dataset is included in this repository.

Tracked metadata belongs in `data/manifests/`. Raw, interim, processed, and sensitive files are excluded by `.gitignore` and must be obtained only after the applicable license, provenance, and heritage-sensitivity review is complete.

`data/manifests/example-dataset.toml` is deliberately fictional. It demonstrates the schema but is not evidence that any dataset has been selected, accessed, downloaded, or verified.

`data/manifests/e001-ea-lidar-dtm.toml` is the real E001 source manifest. It records the verified
261-record Phase 2B.5 positive-terrain freeze, aggregate inventory checksum, versions, and private
storage scope. The public manifest contains no extent or coordinate.

Phase 2A.5 may use `data/private/e001_full_entry_reviews.json` as a local, ignored evidence cache.
It is recreated from the deterministic public List Entry queue and the official Historic England
Reasons and Details sections. It must not contain coordinates, National Grid References, maps, or
polygons. Exact designation and EA index geometry is queried transiently and discarded.

## Phase 2B controlled storage

Site-linked terrain is georeferenced and therefore coordinate-bearing even when it contains no
coordinate table. All such material is stored under the ignored `data/private/e001/` boundary:

- `approved-site-locations.json`: reconstructable local link from approved List Entry IDs to BNG;
- `terrain/raw/`: unmodified bounded WCS GeoTIFF responses;
- `terrain/processed/`: deterministic arrays and representations;
- `terrain/qa/`: local visual-QA images and private acquisition receipts.

The generic `data/raw/`, `data/interim/`, and `data/processed/` paths remain ignored for future
non-sensitive workflows, but E001 site rasters must stay inside `data/private/` because a GeoTIFF
transform reveals its location. Only coordinate-safe manifests, checksums, aggregate reports, and
the terrain index may be tracked. Git LFS is unnecessary for this bounded design.

## Phase 2C background and split storage

Precise background sampling locations can reveal exclusion geometry and therefore remain private,
even though they are not known archaeological locations. Controlled files live under
`data/private/e001/backgrounds/`:

- `sampling_state.json`: deterministic candidate lineage, exact locations, and reason-coded state;
- `raw/` and `processed/`: georeferenced WCS terrain and the frozen arrays;
- `qa/`: private strips, contact sheets, selection receipt, and technical/confound review.

Tracked Phase 2C artifacts use only opaque sample and observation-group IDs, coarse BNG groups,
terrain provenance, checksums, aggregate rejection/audit counts, and frozen partition assignments.
They must never contain Easting, Northing, bounding boxes, geometry, exact positive distance, or
reconstructable sampling coordinates.
