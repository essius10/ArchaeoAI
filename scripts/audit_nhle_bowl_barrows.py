"""Run the coordinate-safe Phase 2A NHLE metadata feasibility audit."""

from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from pathlib import Path

from archaeoai.nhle_audit import (
    build_audit_summary,
    fetch_all_list_entry_ids,
    fetch_barrow_records,
    fetch_source_metadata,
    fetch_total_record_count,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit official NHLE Scheduled Monument titles without retaining coordinates."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("outputs/feasibility"),
        help="Directory for coordinate-free JSON and CSV summaries.",
    )
    parser.add_argument("--sample-size", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.sample_size < 0:
        raise SystemExit("--sample-size must not be negative")

    accessed_at = datetime.now(UTC)
    service_metadata, layer_metadata = fetch_source_metadata()
    total_features = fetch_total_record_count()
    all_list_entries = fetch_all_list_entry_ids()
    distinct_list_entries = len(set(all_list_entries))
    if len(all_list_entries) != total_features:
        raise RuntimeError("Paged List Entry query did not match the feature count")
    records = fetch_barrow_records()
    summary, rows = build_audit_summary(
        total_features=total_features,
        distinct_list_entries=distinct_list_entries,
        barrow_records=records,
        service_metadata=service_metadata,
        layer_metadata=layer_metadata,
        accessed_at=accessed_at,
        sample_size=args.sample_size,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = args.output_dir / "bowl_barrow_summary.json"
    counts_path = args.output_dir / "bowl_barrow_counts.csv"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with counts_path.open("w", encoding="utf-8", newline="") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    counts = summary["counts"]
    print(
        f"NHLE Scheduled Monuments examined: {counts['total_scheduled_monument_records_examined']}"
    )
    print(f"Duplicate List Entry features: {counts['duplicate_list_entry_features']}")
    print(f"Broad barrow candidates: {counts['broad_barrow_candidates']}")
    print(f"Probable bowl-barrow title candidates: {counts['probable_bowl_candidates']}")
    print(f"Clear title exclusions: {counts['clear_title_exclusions']}")
    print(f"Manual title review required: {counts['manual_review_required']}")
    print(f"Wrote {summary_path} and {counts_path}; no coordinates or geometry were retained.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
