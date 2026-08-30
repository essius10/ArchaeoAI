# Future E001 research-release checklist

This checklist prepares a possible future release. Phase 4B does **not** execute any item marked as
a publication or deployment action.

## Scientific freeze

- [x] Confirm Phase 3C result remains immutable and external test is marked spent.
- [x] Confirm Phase 4A is labelled `POST-HOC / EXPLORATORY` throughout.
- [x] Bind the manuscript to dataset, model, result, prediction-vector, and figure hashes.
- [x] Keep geographic final, five-fold robustness, CNN, and external results separate.
- [ ] Obtain independent scientific and archaeological review.
- [ ] Complete the frozen 40-record independent label-reliability review or report it unresolved.
- [ ] Reproduce the public package from a clean CPython 3.12 environment outside the authoring
  session.

## Claims and citations

- [x] State the 84.2% result as documented-terrain versus unlabelled-background classification.
- [x] State that model scores are not archaeological probabilities.
- [x] State that no archaeological discovery is claimed.
- [x] Mark incomplete literature work `CITATION_REVIEW_REQUIRED`.
- [ ] Complete and document a systematic literature search.
- [ ] Verify every reference, author list, title, venue, year, page range, and DOI.
- [ ] Obtain manuscript review; do not describe the draft as peer reviewed before that occurs.

## Data, privacy, and licensing

- [x] Confirm no precise coordinate, private terrain, row-level prediction, candidate table, or
  sensitive map is tracked.
- [x] Document source provenance and provider attribution.
- [x] State that private/location-linked material is intentionally withheld.
- [ ] Resolve repository copyright ownership and select licences for code, prose, and third-party
  derived artifacts.
- [ ] Resolve the Historic England attribution-wording discrepancy.
- [ ] Perform a fresh full-history secret, coordinate, large-file, and sensitive-extension scan.
- [ ] Obtain an external privacy review appropriate to archaeological location sensitivity.

## Engineering and archival readiness

- [x] Run tests, Ruff, validator, doctor, dependency, frozen-artifact, and figure-hash checks.
- [x] Maintain Linux CPython 3.12 GitHub Actions.
- [ ] Produce a dependency lock or archival environment specification.
- [ ] Perform a clean clone/install/test on Windows and Linux.
- [ ] Select a semantic version and freeze a release commit.
- [ ] Prepare release notes and a changelog entry.
- [ ] Decide whether to archive with Zenodo or another repository; do not mint a DOI prematurely.

## Publication/deployment actions — not executed

- [ ] Create a GitHub release.
- [ ] Mint a DOI.
- [ ] Submit or publish a preprint.
- [ ] Submit a journal manuscript.
- [ ] Deploy the website.
- [ ] Announce discovery or candidate locations.

Release is blocked until every required scientific, citation, licensing, privacy, and independent-
reproduction item has an accountable reviewer and recorded outcome.
