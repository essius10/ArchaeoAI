# E001 Phase 2F-A: controlled Random-Forest inference design

## Status and boundary

**READY_NO_REAL_SCAN.** Phase 2F-A freezes an inference design, fits the already-selected Random
Forest once on the complete 522-observation E001 modelling dataset, and prepares coordinate-safe
software. It does not load or score a new terrain domain, create candidate locations, contact an
archaeologist, or build a website.

The aim is to rank unseen terrain patches by similarity to terrain patterns learned in E001. It is
not to declare archaeological sites. The Phase 2D geographic final balanced accuracy of 0.870968
remains the primary confirmatory result; the later Random-Forest geographic-CV mean of 0.823406 and
CNN mean of 0.700866 remain post-hoc robustness and stronger-model evidence.

## Frozen model and full-data fit

The model is exactly the selected Phase 2D Random Forest: 300 trees, maximum depth 8, minimum leaf
size 5, `sqrt` feature sampling, one CPU job, and seed 20260829. Its configuration SHA-256 remains
`20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4`.

All confirmatory and robustness evaluation is complete, so the inference model is fitted once on
all 522 curated modelling observations: 261 `positive_bowl_barrow` and 261
`unlabelled_background`. This does not alter any historical result. Labels come only from the
frozen modelling index. Sample identifiers locate private terrain archives but never become model
features. Coordinates, geographic groups, provenance, survey year, source resolution, filenames,
and paths are excluded from the feature matrix. Candidate results cannot trigger retraining in
Phase 2F-A.

The fitted model and fit receipt are stored below `data/private/e001/inference/`, which Git ignores.
The public protocol records only coordinate-safe data and model checksums. The learned model-state
SHA-256 is `e3b0c072f437e889f09a2a2cf5a37f19b2f483eb5188e102b132a89ee76d1939`;
an independent refit reproduced it exactly.

## Controlled terrain domain

The first research domain is bounded to one contiguous 5 km × 5 km area, publicly named only
`CONTROLLED_DOMAIN_001`. It must use public Environment Agency 1 m LiDAR DTM in EPSG:27700 and one
compatible acquisition where practical. It must not overlap any E001 modelling window. DSM data,
unclear licences, incompatible CRS or resolution, score-selected geography, and more than one
domain are excluded.

The exact extent must be selected without model scores and written to an ignored private domain
receipt before acquisition or scoring. The public repository will not contain its boundary, tile
identifier, coordinates, source filenames, or a reversible token. If this private binding is
missing, the inference run must stop.

## Patch and feature pipeline

The grid uses 128 m × 128 m patches at 1 m resolution and a frozen 64 m stride. It is anchored to
the private domain raster's upper-left pixel grid and traversed in row-major order. A complete
5,000 × 5,000 pixel domain therefore has 77 × 77 = 5,929 windows before QA and covers at most
24.920064 km² after the final partial edge strip is excluded. The stride cannot be changed after
scores are observed, and manual browsing cannot select windows before scoring.

Every patch uses the existing E001 automatic patch QA and representation QA. The feature order is:

1. per-patch median-normalized elevation;
2. slope in degrees;
3. hillshade at azimuth 315° and altitude 45°;
4. local relief using a 16 m radius.

Each 128 × 128 representation is reduced by the existing deterministic non-overlapping 4 × 4 mean
pool to 32 × 32, giving 1,024 values per channel and 4,096 total terrain-only features. Synthetic
equivalence tests require inference assembly to match the training implementation numerically.

## Score semantics and ranking

Allowed descriptions are **model score**, **terrain-similarity score**, **bowl-barrow-class score**,
and **candidate-ranking score**. The score is not calibrated archaeological probability:

> A score of 0.90 does not mean there is a 90% chance archaeology exists.

All valid windows must be scored before review. They are ordered by descending model score with a
private-token tie-break. Phase 2F does not threshold them into “site” and “no site.”

Deterministic greedy non-maximum suppression handles overlapping windows. A lower-ranked window is
suppressed when its centre is less than 128 m from an already retained representative or its patch
intersection-over-union exceeds 0.25. The highest score, followed by the private-token tie-break,
selects the representative. This prevents adjacent windows over the same landform from being
reported as independent candidates.

After deduplication, the blinded review queues are frozen as follows:

- highest-score queue: representatives at or above the 99th percentile, maximum 25;
- medium diagnostic queue: inclusive 45th–55th percentile, SHA-256 ranked, maximum 25;
- random reference queue: SHA-256 ranked from remaining representatives, maximum 25;
- deterministic review seed: 20260829.

No best threshold, band, or seed is selected from observed spatial patterns.

## Blinded review and record cross-check

Where practical, the reviewer initially receives patches without scores or queue labels. Allowed
categories are `mound-like terrain morphology`, `modern/engineered feature`,
`geomorphic/natural relief`, `ambiguous`, and `insufficient evidence`. A visual category is not an
archaeological identification.

Scores, ranking, deduplication, and blinded review must be frozen before a heritage-record
cross-check. That later diagnostic can ask whether ranked terrain resembles documented mound-like
features or common modern, geological, forestry, agricultural, road, track, drainage, and boundary
confounds. Absence from a database is never evidence of a new discovery.

## Privacy and public outputs

Exact domain and candidate locations, NGRs, grid references, coordinate tables, GeoJSON, rasters,
georeferenced images, source filenames, private window tokens, private ranked tables, and review
receipts stay under the ignored private tree. Tracked outputs may contain only aggregate window
counts, score distributions, review-band/category counts, non-identifying coarse summaries,
checksums, versions, and performance measurements.

A future research API may expose a model version, score-semantics statement, aggregate counts,
aggregate distributions, and pipeline status. It must never expose exact locations, source paths,
private tokens, sample identifiers, ranked candidate tables, or georeferenced media. No API or
website is built in Phase 2F-A.

## Synthetic CPU readiness check

After the protocol commit, a coordinate-free 32-patch synthetic smoke test exercised model loading,
terrain representations, pooling, scoring, ranking, deduplication, and all three review queues. On
this machine it measured approximately 0.055 seconds to load the private 1,300,710-byte model,
496 synthetic patches/second for in-memory terrain preprocessing, 3,516 patches/second for batched
model scoring, and 0.284 ms model latency per patch. Combined in-memory throughput was about 435
patches/second with a measured process peak working set of 158,953,472 bytes (about 152 MiB).

The corresponding 6,411 km²/hour grid-footprint calculation is explicitly an in-memory synthetic
upper bound. It excludes terrain download, GeoTIFF I/O, mosaicking, and provider latency and must not
be presented as field-ready throughput. Representation generation and pooling were the measured
bottleneck. These checks support a bounded CPU backend; they provide no archaeological evidence.

## Stop conditions

Inference must stop before review if any frozen hash changes; the private domain receipt is absent
or trackable; the domain exceeds one 5 km square; terrain type, licence, CRS, or resolution is
incompatible; an E001 window overlaps the domain; feature equivalence fails; exact locations would
be tracked; more than 20% of windows are rejected/no-data; fewer than 100 valid windows remain; or
candidate evidence is proposed as a reason to retune.

The run cannot stop early because scores look weak or strong. If started, every valid window in the
frozen domain must be processed.

## Machine-readable protocol

The authoritative protocol is `configs/e001-phase-2f-a-inference-protocol.json`. Its SHA-256 is a
canonical JSON digest excluding only its own `protocol_sha256` field. The protocol and fitted-model
checksum were committed before any real candidate score was produced. Protocol SHA-256:
`fa1f9cd12230df3f7c83c45febd5ec0ba751f371a098600873380bc47c624095`.
