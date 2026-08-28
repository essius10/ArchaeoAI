"""Reconstruct approved E001 locations into ignored controlled local storage."""

from __future__ import annotations

import argparse
from pathlib import Path

from archaeoai.paths import find_project_root
from archaeoai.terrain.acquisition import (
    load_accepted_sites,
    reconstruct_private_locations,
    write_private_locations,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/private/e001/approved-site-locations.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = find_project_root()
    accepted = load_accepted_sites(root / "outputs/feasibility/e001_curated_records.csv")
    locations = reconstruct_private_locations(accepted)
    output = write_private_locations(
        locations,
        destination=(root / args.output).resolve(),
        project_root=root,
    )
    print(f"Reconstructed {len(locations)} approved locations in controlled storage: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
