"""Validate Phase 5E evidence, derived status, or a generated review bundle."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from archaeoai.review_evidence import (
    ReviewEvidenceError,
    assert_review_commit_available,
    evaluate_review_gate,
    expected_review_bundle_manifest_sha256,
    load_review_record,
    review_record_sha256,
    verify_review_bundle,
)

ROOT = Path(__file__).resolve().parents[1]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--review", type=Path, help="Completed review JSON to validate")
    selection.add_argument("--verify-bundle", type=Path, help="Generated review bundle directory")
    args = parser.parse_args(argv)
    try:
        if args.review:
            review = load_review_record(args.review)
            assert_review_commit_available(ROOT, review["reviewed_repository_commit"])
            expected_manifest = expected_review_bundle_manifest_sha256(
                ROOT, revision=review["reviewed_repository_commit"]
            )
            if review["review_bundle_manifest_sha256"] != expected_manifest:
                raise ReviewEvidenceError("review bundle manifest hash does not match the commit")
            payload = {
                "status": "VALID_COMPLETED_REVIEW",
                "review_id": review["review_id"],
                "review_domain": review["review_domain"],
                "record_sha256": review_record_sha256(review),
            }
        elif args.verify_bundle:
            manifest = verify_review_bundle(args.verify_bundle)
            payload = {
                "status": "VALID_REVIEW_BUNDLE",
                "repository": manifest["repository"],
                "reviewed_repository_commit": manifest["reviewed_repository_commit"],
                "file_count": len(manifest["files"]),
            }
        else:
            payload = evaluate_review_gate(ROOT)
    except ReviewEvidenceError as exc:
        parser.error(str(exc))
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
