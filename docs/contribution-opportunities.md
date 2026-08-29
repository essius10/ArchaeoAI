# Contribution opportunities

ArchaeoAI welcomes small, reviewable improvements that strengthen reproducibility and responsible
geospatial research. Open an issue before substantial work so scope and evidence expectations are
clear. Every task below can and should be completed without sensitive coordinates or private
terrain.

## 1. Improve aggregate result visualizations

Make the existing coordinate-safe evaluation figures easier to read in print and on small screens.
Useful improvements include accessible colour contrast, clearer uncertainty annotations, and tests
for deterministic SVG output. Do not add maps or sample-level predictions.

## 2. Add synthetic terrain examples

Create small, clearly fictional elevation arrays illustrating median normalization, slope,
hillshade, local relief, and 4×4 pooling. Add focused tests and documentation explaining the
expected transform behavior. No downloaded or real archaeological terrain is needed.

## 3. Strengthen cross-platform setup checks

Improve environment guidance or public, data-free diagnostics for Linux and macOS while preserving
the Windows workflow. Keep hosted checks independent of CUDA, private model files, and local terrain.

## 4. Benchmark the inference components

Extend coordinate-free synthetic benchmarks for patch preprocessing, pooled feature assembly, model
loading, and CPU scoring. Clearly separate in-memory upper bounds from download, raster I/O, and
mosaicking. Never publish a real candidate table or location.

## 5. Review research documentation and terminology

Check that summaries consistently distinguish documented positives, `unlabelled_background`, model
scores, and archaeological evidence. Improve navigation between protocols, results, limitations,
and the claims register without strengthening any claim beyond its evidence.

## Before contributing

Read [CONTRIBUTING.md](../CONTRIBUTING.md), [SECURITY.md](../SECURITY.md), and the
[claims register](claims-register.md). Use synthetic fixtures, run the public CI commands locally,
and disclose any methodology or privacy impact in the pull request.
