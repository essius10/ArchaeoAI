# Environment audit — 27 August 2026

## Observed

| Area | Finding | Consequence |
|---|---|---|
| OS | Windows (PowerShell 7.6.4) | Use PowerShell-friendly setup commands. |
| Python | CPython 3.14.7 is installed at `C:\Users\athar\AppData\Local\Python\pythoncore-3.14-64\python.exe`; the repository `.venv` uses that runtime. | Phase 1 can be developed locally. CPython 3.12 remains the reference runtime; supported range is `>=3.12,<3.15`. |
| GPU | NVIDIA GeForce RTX 5060, 8,151 MiB reported; CUDA driver supports 13.3 | Enough for modest CNN experiments later; no need to design around large models. |
| Disk | ~697 GiB free on C: | Enough for selected LiDAR tiles, subject to a data budget. |
| Git | Git 2.53.0 is available; `main` tracks `origin/main`. | Phase 1 changes are versioned and pushed through normal, non-force updates. |
| Python package | Editable `archaeoai` 0.1.0 installation with pytest 9.1.1 and Ruff 0.16.5 in `.venv`. | Configuration and manifest logic can be tested. |
| GitHub connection | `origin` is `https://github.com/essius10/ArchaeoAI.git`. | GitHub `main` is the authoritative branch. |

## Before executable E001

1. Complete dataset decision D001, including label license and heritage-sensitivity review.
2. Establish a CPython 3.12 reference environment and test the Phase 2B geospatial dependency set separately.
3. Implement and test raster metadata validation before processing real terrain.
4. Record Python, GDAL, Rasterio, GeoPandas, and any later CUDA/PyTorch versions in run metadata.

## Deliberate non-actions

Phase 1 installed only pytest and Ruff as development tools. Phase 2B adds the minimum raster
runtime described below; it does not add a modelling framework.

## Phase 2B dependency gate — 28 August 2026

The Windows launcher lists only CPython 3.14.7. CPython 3.12 is **not installed**, so no 3.12
reproduction is claimed. The current environment may still be used because the official PyPI
release metadata was checked before installation:

| Package | Selected range | Release checked | CPython 3.12 Windows x86-64 wheel | CPython 3.14 Windows x86-64 wheel | Purpose |
|---|---|---:|---:|---:|---|
| NumPy | `>=2.5,<3` | 2.5.2 | Yes | Yes | Deterministic terrain arrays and numerical transforms |
| Rasterio | `>=1.5,<2` | 1.5.1 | Yes | Yes | GeoTIFF I/O, GDAL-backed metadata, windows, and mosaics |
| PyProj | `>=3.7,<4` | 3.7.2 | Yes | Yes | Explicit CRS identity and transformation checks |

Rasterio's wheel bundles the required GDAL runtime, avoiding an unmanaged local GDAL build. NumPy,
Rasterio, and PyProj are the entire Phase 2B runtime addition. Shapely, GeoPandas, Pandas, SciPy,
matplotlib, scikit-learn, PyTorch, and TensorFlow remain excluded because bounded raster processing
does not require them.

Installation and import smoke tests passed on CPython 3.14.7 with NumPy 2.5.2, Rasterio 1.5.1
(GDAL 3.12.4), and PyProj 3.7.2 (PROJ 9.5.1). `pip check` reported no broken requirements, and
PyProj resolved EPSG:27700 as OSGB36 / British National Grid.

Reference verification remains a release gate: repeat the full checks in a clean CPython 3.12
environment when that interpreter is made available. This does not require changing the supported
project range of `>=3.12,<3.15`.
