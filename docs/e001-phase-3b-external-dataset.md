# E001 Phase 3B — external dataset construction gate

## Decision

**INSUFFICIENT EXTERNAL SAMPLE.** Phase 3B stopped at the frozen positive-curation gate. It did
not construct backgrounds, download terrain rasters, generate model inputs, freeze an external
dataset, load the Random Forest, produce predictions, or calculate performance metrics.

The 87 records frozen by Phase 3A were reviewed against their official Historic England full
entries. Forty-seven passed the complete label, geometry, 1 m coverage, and provenance gates;
36 were rejected; three remained uncertain; and one required terrain-provenance review. Even if
that final terrain case passed, only 48 records would be available, below the pre-registered
minimum of 50 matched pairs.

## Why construction stopped

The Phase 3A protocol forbids loosening the inclusion rule, expanding the geography, or loading
the model to compensate for a small sample. The 50-pair minimum therefore acts as a hard research
gate rather than a target to be reached through discretionary inclusion.

The coordinate-safe aggregate receipt is
[`outputs/external_validation/e001_phase3b_curation_gate.json`](../outputs/external_validation/e001_phase3b_curation_gate.json).
The complete record-level review and exact locations remain under the Git-ignored private data
tree. Its SHA-256 receipt is public, but its contents are not.

## Allowed next step

Phase 3C external evaluation is **not authorized**. A future continuation would require a separate,
pre-score protocol amendment that identifies additional independent geography and preserves the
same target definition, inclusion rules, model, preprocessing, and privacy boundary. The existing
47 accepted records must remain untouched by model output during that decision.

No external RF scoring occurred. No external performance metric was calculated.
