# Claims register

Every public statement about ArchaeoAI must be entered here before it appears in a README, presentation, application, report, or social post.

| Claim ID | Proposed claim | Evidence artifact | Scope / wording limit | Reviewer | Status |
|---|---|---|---|---|---|
| C001 | Terrain representation affects baseline performance on this task. | E001 report and split manifest | Name dataset version, feature class, regions, metric, and confidence interval. Do not generalize beyond them. | Pending | Pending |
| C002 | Random patch splits can overestimate performance relative to a geographic holdout. | E001 paired split results | Say “in this study” unless independently replicated. | Pending | Pending |
| C003 | ArchaeoAI is reproducible. | Clean rerun log and environment lockfile | Claim only after a second person/session regenerates the headline result. | Pending | Pending |
| C004 | Official NHLE metadata suggests that scheduled single bowl barrows are viable for an E001 label-curation study. | Phase 2A audit code, coordinate-free outputs, and 30-entry manual sample | Say “conditional GO” and name the 27 August 2026 service snapshot. Counts are title-triage queues, not final labels; make no terrain or model claim. | Pending | Evidence recorded; review pending |
| C005 | A coordinate-safe Phase 2A.5 audit found 261 scheduled bowl-barrow records that passed the frozen full-entry, geometry, 128 m coverage, and provenance gates. | `e001_curation_summary.json`, curated-record table, code, tests, and Phase 2A.5 report | Name the 27 August 2026 source snapshot. Say “curated records,” not ground truth. State that 40 records await independent review, groups and holdouts are provisional, and Phase 2A.5 itself contains no raster or model result; cite C006 separately for the later pilot. | Pending | Evidence recorded; independent review pending |
| C006 | A five-site, coordinate-controlled pilot reproducibly acquired and validated 128 m EA DTM patches for approved E001 records. | Phase 2B manifest, pilot summary, terrain index, synthetic tests, private checksums, and QA log | Say 5/5 pilot patches, not all 261. State CPython 3.14.7, bounded WCS access, and zero pilot no-data. Do not infer archaeological visibility, dataset-wide completeness, model performance, or discovery. | Pending | Evidence recorded; CPython 3.12 reproduction pending |

## Rule

If the evidence does not exist, the status remains **Pending** and the claim is not used.
