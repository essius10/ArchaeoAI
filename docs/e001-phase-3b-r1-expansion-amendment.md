# E001 Phase 3B-R1 — external sample expansion amendment

## Decision

**READY FOR MULTI-REGION DATASET CONSTRUCTION — NO SCORE.** Phase 3B-R1 adds four
preselected 25 km British National Grid cells to the external-data construction scope. The
selection was made from official Historic England designation metadata and Environment Agency
coverage/provenance metadata only. No terrain raster was downloaded, no supplementary record was
archaeologically curated, and the Random Forest was neither loaded nor scored.

The frozen machine-readable amendment is
[`configs/e001-phase-3b-r1-expansion-amendment.json`](../configs/e001-phase-3b-r1-expansion-amendment.json),
SHA-256 `330263472d6b947fa688cbe6a21a52f437fc7c206555a023b7e64900c7bf13f9`.

## Why an amendment was necessary

The first external cell produced 47 accepted records after strict review. Thirty-six were
rejected, three remained uncertain, and one still needed terrain-provenance review. Even the
maximum possible count of 48 could not meet the frozen 50-pair minimum. Those decisions remain
locked: sample-size pressure is not a reason to weaken or reinterpret the archaeological evidence
gate.

The preferred target remains 60 accepted positives plus 60 matched `unlabelled_background`
observations. The hard minimum remains 50 matched pairs.

## Selection rules were frozen before search

The first pre-search rule required one genuinely separated 25 km cell to contain at least 28
independent probable-title records passing 1 m DTM metadata QA. The value 28 was a planning
quantity, `ceil(15 / (47 / 87))`; it did not assume that title matches were labels. That rule is
frozen at SHA-256
`6e5f2992fe453601940792ad4c1f7be373c12724f5849f43926c7ea680459578`.

The subsequent NHLE-only search found 40 eligible cells, but the largest contained 11 records.
This was a valid single-cell no-go. Before any EA metadata query, a bounded fallback was therefore
frozen at SHA-256
`adaba743b3e5877a28f2d88b5f058b5c94fc261b9e97ddaa1f5a2a108b71408b`.
It preserves the 28-record threshold and every independence rule, but selects the shortest prefix
of the same deterministic ranking needed to reach 28 QA-pass records, with at most five cells.

## Coordinate-safe feasibility result

Nine cells contained at least four independent probable-title records and were eligible for EA
metadata checking. The ordering was fixed as: QA-pass count descending, independent probable
count descending, minimum separation from the first external cell descending, then cell ID
ascending.

| Rank | Coarse cell | Independent probable titles | Complete 1 m coverage | QA pass |
|---:|---|---:|---:|---:|
| 1 | `BNG_25KM_E19_N6` | 11 | 11 | 11 |
| 2 | `BNG_25KM_E19_N5` | 10 | 10 | 8 |
| 3 | `BNG_25KM_E18_N4` | 7 | 7 | 7 |
| 4 | `BNG_25KM_E20_N13` | 5 | 5 | 5 |
| 5 | `BNG_25KM_E21_N11` | 5 | 5 | 5 |
| 6 | `BNG_25KM_E12_N3` | 4 | 4 | 4 |
| 7 | `BNG_25KM_E12_N5` | 4 | 4 | 4 |
| 8 | `BNG_25KM_E18_N7` | 4 | 4 | 4 |
| 9 | `BNG_25KM_E16_N7` | 4 | 4 | 4 |

The shortest passing prefix is the first four cells. Together they contain 33 independent
probable-title records, of which 31 passed complete-patch 1 m DTM coverage and single-signature
provenance metadata QA. These are feasibility candidates, not accepted archaeological labels.
The aggregate receipt is
[`outputs/external_validation/e001_phase3b_r1_expansion_feasibility.json`](../outputs/external_validation/e001_phase3b_r1_expansion_feasibility.json).

Every selected record is outside cells occupied by E001 observations, at least 15 km from all 522
E001 observations, at least 15 km from the private Phase 2F domain, and in a cell at least 25 km
from the first external cell boundary. All 360 prior E001 review IDs and all 87 first-external-cell
review IDs were excluded.

## Frozen future analysis policy

If a later construction phase meets every unchanged data gate, the primary external result will
use all external observations combined and the unchanged primary metric, balanced accuracy. The
same frozen Random Forest and threshold will apply to every observation.

Two secondary descriptive strata are preregistered: the first external geography and all
supplementary geography combined. They may be reported only if each contains both classes and at
least 10 frozen matched pairs. They cannot tune or select the model, replace the primary combined
result, or support separate regional models.

## Unchanged boundaries

The positive evidence criteria, matched-background policy, terrain pipeline, frozen Random Forest,
classification threshold, metrics, privacy policy, 60-pair target, 50-pair minimum, and no-score
rule are unchanged. Record-level metadata and coordinates remain in a Git-ignored private manifest.

Phase 3B dataset construction may resume only under this amendment. Phase 3C scoring is not
authorized. No external performance claim exists.
