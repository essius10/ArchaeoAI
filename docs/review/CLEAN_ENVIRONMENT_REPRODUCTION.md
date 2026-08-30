# Clean-environment reproduction audit

**Classification: PARTIALLY REPRODUCIBLE — PRIVATE DATA REQUIRED FOR SPECIFIC STEPS**

## Public clean-clone test

On 30 August 2026, commit `8d4fa58747729bccf3061e009d67c98643e10882` was cloned into a
new temporary directory and installed into a new CPython 3.14.7 virtual environment with
`pip install -e ".[dev]"`. A deeply nested temporary path first hit the Windows maximum-path limit
inside PyTorch's packaged licence files. Repeating the documented install from a short temporary
path succeeded. This is installation friction, not a scientific-result failure; Windows users
should clone to a short path until the dependency layout changes.

The first clean-clone test found a strict but portable-hash defect: Git can expand every line ending
in historical mixed-line-ending JSON files on Windows. The check was corrected to compare the exact
SHA-256 of LF-normalized repository content, while retaining the original native receipt. It still
rejects any non-line-ending content change. The final Phase 4C commit was retested after this fix.

The clean environment can validate the public package without coordinates, rasters, model files,
or row-level predictions. The automated suite checks exact aggregate results, frozen configurations
and hashes, figure hashes, spent-test state, claim boundaries, and privacy guards. Ruff, project
validation, the environment doctor, and dependency consistency are also part of the audit.

## What public evidence reproduces

- installation and imports on the supported Python range;
- exact stored Phase 2D, Phase 2E, Phase 3C, and Phase 4A aggregate values;
- frozen protocol, configuration, dataset-receipt, prediction-receipt, model-state, manuscript,
  and figure bindings;
- coordinate-safe figures and manuscript evidence validation;
- guards against retraining, rescoring the spent external test, and tracking sensitive files.

## What requires private material

The public checkout cannot reconstruct source labels, extract the exact terrain patches, recompute
features from private rasters, refit the byte-identical model, reproduce row-level predictions, or
inspect the Phase 2F candidate packet. Those steps require exact archaeological locations,
location-linked terrain, private provenance manifests, model/checkpoint files, or the private
prediction vector. These materials are deliberately ignored or withheld for responsible
archaeological-location handling.

Accordingly, the repository publicly reproduces the coordinate-safe evidence and integrity checks,
but not every data-construction and model-execution step. Independent full-data reproduction remains
a future controlled-review task.
