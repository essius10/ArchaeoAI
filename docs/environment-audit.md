# Environment audit — 27 August 2026

## Observed

| Area | Finding | Consequence |
|---|---|---|
| OS | Windows (PowerShell 7.6.4) | Use PowerShell-friendly setup commands. |
| Python | `python` was not found on `PATH` | No Python pipeline was installed or run. |
| GPU | NVIDIA GeForce RTX 5060, 8,151 MiB reported; CUDA driver supports 13.3 | Enough for modest CNN experiments later; no need to design around large models. |
| Disk | ~697 GiB free on C: | Enough for selected LiDAR tiles, subject to a data budget. |
| Git | Git 2.53.0 is available; an empty repository was initialized during setup. The sandbox cannot write `.git/*.lock` because the directory is owned by the Windows user rather than the sandbox account. | Working files are version-control ready, but commit/branch operations must run from the user's terminal or a session with Git-metadata write access. |
| Existing ArchaeoAI files | None; workspace contained only `outputs/` and `work/` | This is a fresh bootstrap, not an audit of an existing codebase. |
| GitHub connection | No installed repository matched `archaeo` | A remote has not been assumed or created. |

## Before E001

1. Install a supported Python 3.12+ distribution and confirm `python --version` works in a new terminal.
2. From the user's normal terminal, rename the initial branch to `main` if needed and make an initial commit.
3. Create a virtual environment and install only the pinned dependencies selected after the data format is known.
4. Record `python`, `gdal`, `rasterio`, `geopandas`, and CUDA/PyTorch versions in the experiment log.

## Deliberate non-actions

No package installation, bulk data download, neural-network training, or remote repository creation was performed. Each would be premature while label provenance and the study area remain undecided.
