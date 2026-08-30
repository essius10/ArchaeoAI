# E001 future release plan

## Current state

Phase 4B prepares a manuscript and reproducibility package for review. It does not publish a
preprint, create a GitHub release, mint a DOI, deploy the website, or redistribute private data.
The current manuscript is a project draft, not peer-reviewed work.

## Proposed release contents

A future coordinate-safe research release may contain:

- tagged source code, tests, configurations, and CI workflow;
- the manuscript and completed citation record;
- coordinate-safe aggregate JSON/CSV evidence and SVG figures;
- data-method, provenance, licensing, and privacy documentation;
- the manuscript evidence manifest and release-verification report;
- environment lock/specification and independent clean-rerun record.

It must not contain exact archaeological coordinates, raw or location-linked terrain, private
manifests, row-level external predictions, model-selected candidate locations, private inference
domains, checkpoints, or review media.

## Gates

### Gate R1 — scientific review

An independent reviewer checks the research question, data definitions, split logic, statistical
wording, evidence hierarchy, and distinction between confirmatory and exploratory analyses. Any
correction to a frozen scientific result requires a transparent amendment, never silent rewriting.

### Gate R2 — citation and authorship review

Complete the literature search and resolve `CITATION_REVIEW_REQUIRED`. Verify bibliographic
metadata from primary sources. Confirm authorship and contributions without inventing professor,
university, institutional, or peer-review involvement.

### Gate R3 — licensing and provenance review

Resolve ownership of original code and prose, select appropriate licences, preserve Historic
England, Ordnance Survey, Environment Agency, and OGL notices, and confirm which aggregate
source-derived artifacts may be redistributed. No release should imply provider endorsement.

### Gate R4 — privacy review

Scan the complete tracked history and proposed archive for coordinates, fine grid references,
geometries, private tokens, raw terrain, record-level predictions, and candidate material. A second
person should review the release tree. Privacy decisions must be based on archaeological risk, not
only whether a file is technically public elsewhere.

### Gate R5 — independent reproduction

From a clean clone, reproduce installation, all public tests, validators, aggregate hashes, and
manuscript bindings on CPython 3.12. Record platform and dependency versions. A full private-data
rerun is a separate controlled exercise and must not rerun the spent Phase 3C model evaluation.

### Gate R6 — release authorization

Choose a version, prepare release notes, approve the exact Git tree, and decide separately whether
to create a GitHub release, archival deposit, DOI, preprint, or website deployment. Each is an
external publication action requiring explicit authorization at that future time.

## Versioning and future model generations

The reported E001 Random Forest must remain bound to its original training data and frozen hashes.
If Phase 3 external observations are used for training, the result is a new model generation. It
must receive a new model identifier, configuration, training-data manifest, version, and genuinely
new independent evaluation dataset. It cannot replace the existing Phase 3C result.

## Stop conditions

Do not release if citations remain materially unresolved, ownership or licence scope is unclear,
private files are tracked, the manuscript evidence manifest fails, CI is not green, or claims imply
archaeological discovery, calibrated probability, England-wide performance, institutional
endorsement, or completed peer review.
