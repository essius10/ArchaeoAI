# Data directory

No archaeological or terrain dataset is included in this repository.

Tracked metadata belongs in `data/manifests/`. Raw, interim, processed, and sensitive files are excluded by `.gitignore` and must be obtained only after the applicable license, provenance, and heritage-sensitivity review is complete.

`data/manifests/example-dataset.toml` is deliberately fictional. It demonstrates the schema but is not evidence that any dataset has been selected, accessed, downloaded, or verified.

Phase 2A.5 may use `data/private/e001_full_entry_reviews.json` as a local, ignored evidence cache.
It is recreated from the deterministic public List Entry queue and the official Historic England
Reasons and Details sections. It must not contain coordinates, National Grid References, maps, or
polygons. Exact designation and EA index geometry is queried transiently and discarded.
