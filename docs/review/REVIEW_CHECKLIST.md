# E001 independent review checklist

Use `Pass`, `Revise`, `Not assessed`, or `Not applicable` for each item and record evidence or page
references. A single reviewer is not expected to cover every discipline.

## Archaeology

- [ ] The bowl-barrow target definition is archaeologically coherent and appropriately narrow.
- [ ] Scheduled/documented-record selection bias is described accurately.
- [ ] `unlabelled_background` is never treated as known non-archaeology.
- [ ] No model output is presented as archaeological interpretation or discovery.
- [ ] The absence of field validation is given appropriate weight.

## Remote sensing and GIS

- [ ] DTM source, resolution, CRS, provenance, patch size, and transforms are adequately specified.
- [ ] Elevation, slope, hillshade, and local-relief processing is technically reproducible.
- [ ] Geographic blocks, buffers, overlap components, and terrain-window leakage controls are sound.
- [ ] External cells support only the stated bounded geographic conclusion.

## Machine learning

- [ ] Model selection is separated from both final tests.
- [ ] Random Forest parameters and 4 × 4 pooled inputs are fully specified.
- [ ] Metadata, coordinates, paths, and provenance are excluded from model features.
- [ ] The CNN comparison is explicitly post-hoc and limited to the current data scale.
- [ ] Scores are not described as calibrated archaeological probabilities.

## Statistics

- [ ] Balanced accuracy is appropriate and correctly interpreted.
- [ ] The 60-pair cluster bootstrap preserves the intended matching structure.
- [ ] Confidence intervals are not interpreted as proof of universal generalization.
- [ ] Confirmatory and exploratory analyses remain clearly separated.
- [ ] Sample-size and geographic-coverage limitations are adequately emphasized.

## Privacy and responsible archaeology

- [ ] No exact coordinate, NGR, heritage ID, candidate row, private path, or sensitive map appears.
- [ ] Withholding raw/location-linked terrain is justified and consistently documented.
- [ ] Phase 2F review material remains private and unreviewed.
- [ ] Future review or release steps include explicit location-risk assessment.

## Reproducibility

- [ ] A clean public clone installs on the stated Python range.
- [ ] Tests, Ruff, validator, doctor, and dependency checks pass.
- [ ] Frozen hashes and coordinate-safe figures validate without private data.
- [ ] Steps requiring private coordinates, terrain, model state, or predictions are identified.
- [ ] The public reproducibility classification is accurate and not overstated.

## Citations and licensing

- [ ] Every citation’s identity and claim fit is verified.
- [ ] Important archaeological and remote-sensing literature omissions are recorded.
- [ ] Historic England, Ordnance Survey, Environment Agency, and OGL attribution is adequate.
- [ ] The absence of a repository-wide licence is visible and treated as a release blocker.
- [ ] No affiliation, endorsement, publication, or peer-review status is implied.
