"""Build a deterministic public-safe Phase 5E external-review bundle."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from archaeoai.review_evidence import ReviewEvidenceError, build_review_bundle

ROOT = Path(__file__).resolve().parents[1]


def _clean_worktree() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return not result.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commit", default="HEAD", help="Exact commit or revision to bundle")
    parser.add_argument(
        "--output",
        type=Path,
        help="Destination under outputs/review/ (must not already exist)",
    )
    args = parser.parse_args(argv)
    if not _clean_worktree():
        parser.error("the working tree must be clean before building a review bundle")
    short_sha = subprocess.run(
        ["git", "rev-parse", "--short=12", f"{args.commit}^{{commit}}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    output = args.output or Path(f"outputs/review/phase5e-{short_sha}")
    if output.is_absolute():
        parser.error("--output must be repository-relative under outputs/review")
    try:
        manifest = build_review_bundle(ROOT, ROOT / output, revision=args.commit)
    except ReviewEvidenceError as exc:
        parser.error(str(exc))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    print(f"Bundle written to {output.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
