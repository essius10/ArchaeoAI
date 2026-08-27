# Environment audit — 27 August 2026

## Observed

| Area | Finding | Consequence |
|---|---|---|
| OS | Windows (PowerShell 7.6.4) | Use PowerShell-friendly setup commands. |
| Python | CPython 3.14.7 is installed at `C:\Users\athar\AppData\Local\Python\pythoncore-3.14-64\python.exe`; the repository `.venv` uses that runtime. | Phase 1 can be developed locally. CPython 3.12 remains the reference runtime; supported range is `>=3.12,<3.15`. |
| GPU | NVIDIA GeForce RTX 5060, 8,151 MiB reported; CUDA driver supports 13.3 | Enough for modest CNN experiments later; no need to design around large models. |
| Disk | ~697 GiB free on C: | Enough for selected LiDAR tiles, subject to a data budget. |
| Git | Git 2.53.0 is available; `main` tracks `origin/main`. | Phase 1 changes are versioned and pushed through normal, non-force updates. |
| Python package | Editable `archaeoai` 0.1.0 installation with pytest 9.1.1 and Ruff 0.16.5 in `.venv`. | Configuration and manifest logic can be tested without Phase 2 dependencies. |
| GitHub connection | `origin` is `https://github.com/essius10/ArchaeoAI.git`. | GitHub `main` is the authoritative branch. |

## Before executable E001

1. Complete dataset decision D001, including label license and heritage-sensitivity review.
2. Establish a CPython 3.12 reference environment and test the future geospatial dependency set separately.
3. Implement and test raster metadata validation before processing real terrain.
4. Record Python, GDAL, Rasterio, GeoPandas, and any later CUDA/PyTorch versions in run metadata.

## Deliberate non-actions

Phase 1 installed only pytest and Ruff as development tools. No geospatial/ML dependency, bulk data download, model training, archaeological coordinate, prediction, or experimental result was created.
