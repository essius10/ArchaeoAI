"""Execute the single frozen E001 Phase 2F-B private inference run."""

from __future__ import annotations

import csv
import ctypes
import hashlib
import json
import secrets
import struct
import subprocess
import time
import zlib
from ctypes import wintypes
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

from archaeoai.inference import (
    DOMAIN_SIZE_PIXELS,
    PATCH_SIZE_PIXELS,
    PixelWindow,
    PrivateScoredWindow,
    deduplicate_ranked,
    features_from_elevation,
    generate_patch_grid,
    load_private_model,
    private_scored_window_payload,
    safe_public_summary,
    score_feature_matrix,
    select_review_queues,
    validate_inference_protocol,
)
from archaeoai.terrain.acquisition import EA_DTM_DATASET_ID, fetch_wcs_payload
from archaeoai.terrain.patches import Bounds
from archaeoai.terrain.privacy import (
    assert_coordinate_safe_mapping,
    ensure_private_output,
    verify_git_ignored,
)
from archaeoai.terrain.raster import read_raster_metadata
from archaeoai.terrain.representations import terrain_representations
from archaeoai.terrain.validation import validate_raster_metadata

EXPECTED_HEAD_PARENT = "111493f9f621bf7a067f984b0cf54f33a714e3e3"
EXPECTED_PROTOCOL_SHA256 = "fa1f9cd12230df3f7c83c45febd5ec0ba751f371a098600873380bc47c624095"
DOMAIN_ALIAS = "CONTROLLED_DOMAIN_001"
PRIVATE_RUN_RELATIVE = Path("data/private/e001/inference/controlled_domain_001")
PUBLIC_SUMMARY_RELATIVE = Path("outputs/inference/e001_phase2f_b_summary.json")
PUBLIC_FIGURE_RELATIVE = Path("outputs/inference/figures/e001_phase2f_b_score_distribution.svg")
ALLOWED_REVIEW_CATEGORIES = (
    "mound-like terrain morphology",
    "modern/engineered feature",
    "geomorphic/natural relief",
    "ambiguous",
    "insufficient evidence",
)


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=root, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _verify_clean_committed_start(root: Path) -> str:
    head = _git(root, "rev-parse", "HEAD")
    origin = _git(root, "rev-parse", "origin/main")
    if head != origin:
        raise ValueError("local main must equal origin/main before private inference")
    if _git(root, "status", "--porcelain"):
        raise ValueError("private inference requires a clean working tree")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", EXPECTED_HEAD_PARENT, head],
        cwd=root,
        check=False,
    )
    if ancestry.returncode != 0:
        raise ValueError("the approved GitHub-polish HEAD is not in current history")
    return head


def _verify_frozen_artifacts(root: Path, protocol: dict[str, Any]) -> None:
    if protocol["protocol_sha256"] != EXPECTED_PROTOCOL_SHA256:
        raise ValueError("unexpected Phase 2F-A protocol")
    for relative, expected in protocol["immutable_artifact_sha256"].items():
        observed = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        if observed != expected:
            raise ValueError(f"frozen artifact checksum mismatch: {relative}")


def _private_training_centres(root: Path) -> tuple[tuple[float, float], ...]:
    positives = json.loads(
        (root / "data/private/e001/approved-site-locations.json").read_text(encoding="utf-8")
    )["records"]
    backgrounds = json.loads(
        (root / "data/private/e001/backgrounds/sampling_state.json").read_text(encoding="utf-8")
    )["records"].values()
    centres = tuple(
        (float(record["easting"]), float(record["northing"]))
        for record in [*positives, *backgrounds]
        if record.get("selection_status", "selected") == "selected"
    )
    if len(centres) != 522:
        raise ValueError("private overlap audit requires all 522 E001 centres")
    return centres


def _overlaps_training(bounds: Bounds, centres: tuple[tuple[float, float], ...]) -> bool:
    margin = PATCH_SIZE_PIXELS
    return any(
        bounds.left - margin <= easting <= bounds.right + margin
        and bounds.bottom - margin <= northing <= bounds.top + margin
        for easting, northing in centres
    )


def _bind_private_domain(root: Path) -> dict[str, Any]:
    run_root = ensure_private_output(root, root / PRIVATE_RUN_RELATIVE)
    receipt_path = run_root / "domain_receipt.json"
    verify_git_ignored(root, receipt_path)
    if receipt_path.exists():
        return json.loads(receipt_path.read_text(encoding="utf-8"))

    centres = _private_training_centres(root)
    salt = secrets.token_hex(32)
    candidates: set[tuple[int, int]] = set()
    for easting, northing in centres:
        base_e = int(easting // 5000) * 5000
        base_n = int(northing // 5000) * 5000
        for east_offset, north_offset in (
            (-2, -1),
            (-2, 0),
            (-2, 1),
            (-1, -2),
            (-1, 2),
            (0, -2),
            (0, 2),
            (1, -2),
            (1, 2),
            (2, -1),
            (2, 0),
            (2, 1),
        ):
            candidates.add((base_e + east_offset * 5000, base_n + north_offset * 5000))
    ordered = sorted(
        candidates,
        key=lambda item: hashlib.sha256(f"{salt}:{item[0]}:{item[1]}".encode()).hexdigest(),
    )
    selected: Bounds | None = None
    for left, bottom in ordered:
        candidate = Bounds(left, bottom, left + 5000, bottom + 5000)
        if not _overlaps_training(candidate, centres):
            selected = candidate
            break
    if selected is None:
        raise ValueError("no score-independent non-overlapping private domain was available")

    receipt = {
        "schema_version": "e001-phase-2f-b-private-domain-v1",
        "warning": "PRIVATE: exact domain receipt; never commit or publish",
        "public_alias": DOMAIN_ALIAS,
        "left": selected.left,
        "bottom": selected.bottom,
        "right": selected.right,
        "top": selected.top,
        "width_m": 5000,
        "height_m": 5000,
        "crs": "EPSG:27700",
        "resolution_m": 1.0,
        "source_dataset_id": EA_DTM_DATASET_ID,
        "source_type": "Environment Agency LiDAR Composite DTM 1m",
        "license": "Open Government Licence v3.0",
        "selection_method": "private_hash_ranked_near_coverage_cell_before_model_scoring",
        "selection_salt": salt,
        "selection_score_independent": True,
        "approved_by": "user_authorized_Phase_2F_B_request",
        "training_or_evaluation_window_overlap": False,
        "bound_at": datetime.now(UTC).isoformat(),
    }
    run_root.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def _receipt_bounds(receipt: dict[str, Any]) -> Bounds:
    required = {"left", "bottom", "right", "top"}
    if not required <= receipt.keys():
        raise ValueError("private domain receipt is incomplete")
    bounds = Bounds(*(float(receipt[key]) for key in ("left", "bottom", "right", "top")))
    if bounds.width != 5000 or bounds.height != 5000:
        raise ValueError("private domain is not exactly 5 km by 5 km")
    return bounds


def _acquire_domain(root: Path, bounds: Bounds) -> tuple[Path, dict[str, Any]]:
    run_root = root / PRIVATE_RUN_RELATIVE
    raster_path = run_root / "domain_dtm_1m.tif"
    verify_git_ignored(root, raster_path)
    started = time.perf_counter()
    if raster_path.exists():
        payload_sha256 = hashlib.sha256(raster_path.read_bytes()).hexdigest()
        acquisition = {"cache_reused": True, "attempts": 0, "retries": 0}
    else:
        payload = fetch_wcs_payload(
            bounds,
            maximum_bytes=256 * 1024 * 1024,
            maximum_attempts=4,
            timeout_seconds=300,
        )
        raster_path.write_bytes(payload.content)
        payload_sha256 = payload.sha256
        acquisition = {
            "cache_reused": False,
            "attempts": payload.attempts,
            "retries": payload.retries,
        }
    metadata = read_raster_metadata(raster_path)
    validate_raster_metadata(metadata, expected_crs="EPSG:27700", expected_resolution_m=1.0)
    if (metadata.width, metadata.height) != (DOMAIN_SIZE_PIXELS, DOMAIN_SIZE_PIXELS):
        raise ValueError("private domain raster must be exactly 5000 by 5000 pixels")
    if any(
        abs(observed - expected) > 1e-6
        for observed, expected in zip(metadata.bounds.as_tuple(), bounds.as_tuple(), strict=True)
    ):
        raise ValueError("private raster extent differs from the bound receipt")
    return raster_path, {
        **acquisition,
        "sha256": payload_sha256,
        "bytes": raster_path.stat().st_size,
        "seconds": time.perf_counter() - started,
    }


def _read_domain(path: Path) -> tuple[np.ndarray, np.ndarray]:
    with rasterio.open(path) as dataset:
        band = dataset.read(1, masked=True)
    data = np.asarray(np.ma.filled(band, np.nan), dtype=np.float32)
    mask = np.ma.getmaskarray(band) | ~np.isfinite(data)
    return data, mask


def _score_all_windows(
    data: np.ndarray,
    mask: np.ndarray,
    windows: tuple[PixelWindow, ...],
    model: Any,
) -> tuple[tuple[PrivateScoredWindow, ...], list[dict[str, Any]], dict[str, float]]:
    started = time.perf_counter()
    feature_rows: list[np.ndarray] = []
    valid_windows: list[PixelWindow] = []
    rejected: dict[str, str] = {}
    for window in windows:
        row = window.row_offset
        column = window.column_offset
        patch = data[row : row + window.size_pixels, column : column + window.size_pixels]
        patch_mask = mask[row : row + window.size_pixels, column : column + window.size_pixels]
        try:
            feature_rows.append(features_from_elevation(patch, patch_mask))
            valid_windows.append(window)
        except ValueError as error:
            rejected[window.private_token] = str(error).split(":", maxsplit=1)[0]
    preprocessing_seconds = time.perf_counter() - started

    scoring_started = time.perf_counter()
    matrix = np.asarray(feature_rows, dtype=np.float32)
    scores = score_feature_matrix(model, matrix)
    scoring_seconds = time.perf_counter() - scoring_started
    scored = tuple(
        PrivateScoredWindow(window, float(score))
        for window, score in zip(valid_windows, scores, strict=True)
    )
    by_token = {item.window.private_token: item.model_score for item in scored}
    rows = []
    for window in windows:
        score = by_token.get(window.private_token)
        rows.append(
            {
                "private_token": window.private_token,
                "row_offset": window.row_offset,
                "column_offset": window.column_offset,
                "size_pixels": window.size_pixels,
                "qa_status": "valid" if score is not None else "rejected",
                "rejection_reason": "" if score is not None else rejected[window.private_token],
                "model_score": "" if score is None else format(score, ".17g"),
            }
        )
    return (
        scored,
        rows,
        {
            "preprocessing_seconds": preprocessing_seconds,
            "scoring_seconds": scoring_seconds,
        },
    )


def _write_private_score_table(root: Path, rows: list[dict[str, Any]]) -> tuple[Path, str]:
    path = root / PRIVATE_RUN_RELATIVE / "complete_score_table.csv"
    verify_git_ignored(root, path)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    receipt = root / PRIVATE_RUN_RELATIVE / "score_table_freeze_receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "score_table_sha256": digest,
                "rows": len(rows),
                "frozen_before_ranking_deduplication_or_interpretation": True,
                "frozen_at": datetime.now(UTC).isoformat(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path, digest


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload))
    )


def _write_grayscale_png(path: Path, values: np.ndarray) -> None:
    finite = values[np.isfinite(values)]
    if not finite.size:
        raise ValueError("cannot render a fully masked review patch")
    low, high = np.quantile(finite, [0.02, 0.98])
    if high <= low:
        high = low + 1
    image = np.clip((values - low) / (high - low), 0, 1)
    image = np.where(np.isfinite(image), image, 0)
    pixels = np.asarray(np.rint(image * 255), dtype=np.uint8)
    scanlines = b"".join(b"\x00" + row.tobytes() for row in pixels)
    header = struct.pack(">IIBBBBB", pixels.shape[1], pixels.shape[0], 8, 0, 0, 0, 0)
    payload = b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", header)
    payload += _png_chunk(b"IDAT", zlib.compress(scanlines, level=9))
    payload += _png_chunk(b"IEND", b"")
    path.write_bytes(payload)


def _write_blinded_packet(
    root: Path,
    data: np.ndarray,
    mask: np.ndarray,
    queues: Any,
) -> tuple[int, Path]:
    packet_root = root / PRIVATE_RUN_RELATIVE / "blinded_review_packet"
    images_root = packet_root / "images"
    images_root.mkdir(parents=True, exist_ok=True)
    queue_items = [
        *(("HIGH", item) for item in queues.high),
        *(("MEDIUM", item) for item in queues.medium),
        *(("RANDOM", item) for item in queues.reference),
    ]
    ordered = sorted(
        queue_items,
        key=lambda pair: hashlib.sha256(
            f"20260829:blind:{pair[1].window.private_token}".encode()
        ).hexdigest(),
    )
    manifest_rows = []
    hidden_rows = []
    ranked_tokens = {
        item.window.private_token: rank
        for rank, item in enumerate(deduplicate_ranked(tuple(item for _, item in ordered)), start=1)
    }
    for index, (band, item) in enumerate(ordered, start=1):
        blind_id = f"REVIEW_{index:03d}"
        filename = f"{blind_id}.png"
        window = item.window
        row, column = window.row_offset, window.column_offset
        patch = data[row : row + window.size_pixels, column : column + window.size_pixels]
        patch_mask = mask[row : row + window.size_pixels, column : column + window.size_pixels]
        representation = terrain_representations(
            patch,
            resolution_m=1.0,
            mask=patch_mask,
            local_relief_radius_m=16.0,
            hillshade_azimuth_deg=315.0,
            hillshade_altitude_deg=45.0,
        )["hillshade_315_45"]
        _write_grayscale_png(images_root / filename, representation)
        manifest_rows.append(
            {
                "blind_id": blind_id,
                "image": f"images/{filename}",
                "review_category": "",
                "review_notes": "",
            }
        )
        hidden_rows.append(
            {
                "blind_id": blind_id,
                "queue_band": band,
                "deduplicated_rank": ranked_tokens[item.window.private_token],
                **private_scored_window_payload(item),
            }
        )
    manifest = {
        "schema_version": "e001-phase-2f-b-blinded-review-v1",
        "status": "READY_UNREVIEWED",
        "instructions": "Classify terrain morphology only; do not infer archaeological status.",
        "allowed_categories": list(ALLOWED_REVIEW_CATEGORIES),
        "score_rank_band_location_and_known_heritage_status_hidden": True,
        "items": manifest_rows,
    }
    (packet_root / "review_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (root / PRIVATE_RUN_RELATIVE / "blinded_review_hidden_mapping.json").write_text(
        json.dumps(
            {"warning": "PRIVATE: keep hidden from reviewer", "items": hidden_rows}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    return len(manifest_rows), packet_root


def _peak_working_set_bytes() -> int | None:
    if not hasattr(ctypes, "windll"):
        return None

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
            ("PrivateUsage", ctypes.c_size_t),
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    process = ctypes.windll.kernel32.GetCurrentProcess()
    if not ctypes.windll.psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb):
        return None
    return int(counters.PeakWorkingSetSize)


def _score_histogram_svg(scores: np.ndarray) -> str:
    counts, edges = np.histogram(scores, bins=np.linspace(0, 1, 21))
    width, height = 840, 460
    left, top, plot_width, plot_height = 70, 45, 730, 340
    maximum = max(int(counts.max()), 1)
    bars = []
    for index, count in enumerate(counts):
        x = left + index * plot_width / len(counts)
        bar_width = plot_width / len(counts) - 2
        bar_height = plot_height * int(count) / maximum
        y = top + plot_height - bar_height
        bars.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" '
            f'height="{bar_height:.1f}" fill="#2f6b5f"/>'
        )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        '<rect width="100%" height="100%" fill="white"/>\n'
        '<text x="70" y="27" font-family="Arial" font-size="18" font-weight="bold">'
        "Controlled-domain terrain-similarity score distribution</text>\n"
        f'<line x1="{left}" y1="{top + plot_height}" x2="{left + plot_width}" '
        f'y2="{top + plot_height}" stroke="#222"/>\n'
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + plot_height}" stroke="#222"/>\n'
        + "\n".join(bars)
        + '\n<text x="390" y="430" font-family="Arial" font-size="14">'
        "Model score (not archaeological probability)</text>\n"
        '<text x="18" y="250" transform="rotate(-90 18 250)" '
        'font-family="Arial" font-size="14">Valid windows</text>\n'
        f'<text x="65" y="410" font-family="Arial" font-size="12">{edges[0]:.1f}</text>\n'
        f'<text x="785" y="410" font-family="Arial" font-size="12">{edges[-1]:.1f}</text>\n'
        "</svg>\n"
    )


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    run_started = time.perf_counter()
    starting_head = _verify_clean_committed_start(root)
    protocol = validate_inference_protocol(root / "configs/e001-phase-2f-a-inference-protocol.json")
    _verify_frozen_artifacts(root, protocol)
    receipt = _bind_private_domain(root)
    bounds = _receipt_bounds(receipt)
    if _overlaps_training(bounds, _private_training_centres(root)):
        raise ValueError("bound private domain overlaps frozen E001 windows")
    raster_path, acquisition = _acquire_domain(root, bounds)
    data, mask = _read_domain(raster_path)

    load_started = time.perf_counter()
    model = load_private_model(
        root,
        root / "data/private/e001/inference/e001_phase2f_random_forest.pkl",
        expected_artifact_sha256=protocol["model"]["private_model_artifact_sha256"],
        expected_state_sha256=protocol["model"]["model_state_sha256"],
    )
    model_load_seconds = time.perf_counter() - load_started
    windows = generate_patch_grid(data.shape, private_domain_salt=receipt["selection_salt"])
    if len(windows) != 5929:
        raise ValueError("pre-QA grid differs from the frozen 5,929-window design")
    scored, private_rows, timings = _score_all_windows(data, mask, windows, model)
    _, score_table_sha256 = _write_private_score_table(root, private_rows)

    rejected_count = len(windows) - len(scored)
    no_data_count = sum(
        "missing_coverage" in row["rejection_reason"]
        for row in private_rows
        if row["qa_status"] == "rejected"
    )
    if rejected_count / len(windows) > 0.20 or len(scored) < 100:
        raise ValueError("frozen terrain-QA stopping criterion reached")

    representatives = deduplicate_ranked(scored)
    queues = select_review_queues(representatives)
    packet_count, packet_root = _write_blinded_packet(root, data, mask, queues)
    score_values = np.asarray([item.model_score for item in scored], dtype=np.float64)
    public = safe_public_summary(
        total_windows=len(windows),
        valid_scores=score_values,
        rejected_windows=rejected_count,
        no_data_windows=no_data_count,
        representative_count=len(representatives),
        queues=queues,
        model_state_checksum=protocol["model"]["model_state_sha256"],
    )
    total_seconds = time.perf_counter() - run_started
    public.update(
        {
            "phase": "2F-B",
            "status": "READY_FOR_BLINDED_HUMAN_MORPHOLOGY_REVIEW",
            "starting_head": starting_head,
            "protocol_sha256": protocol["protocol_sha256"],
            "primary_config_sha256": protocol["primary_config_sha256"],
            "private_score_table_sha256": score_table_sha256,
            "score_table_frozen_before_interpretation": True,
            "score_distribution_extended": {
                "mean": float(score_values.mean()),
                "standard_deviation": float(score_values.std()),
                "q90": float(np.quantile(score_values, 0.90)),
                "q95": float(np.quantile(score_values, 0.95)),
                "q99": float(np.quantile(score_values, 0.99)),
            },
            "controlled_domain": {
                "public_alias": DOMAIN_ALIAS,
                "count": 1,
                "area_km2": 25.0,
                "private_receipt_present": True,
                "training_or_evaluation_overlap": False,
                "terrain_source": "Environment Agency LiDAR Composite DTM 1m",
                "terrain_crs": "EPSG:27700",
                "terrain_resolution_m": 1.0,
            },
            "pipeline": {
                "patch_dimensions_m": [128, 128],
                "stride_m": 64,
                "representations": list(protocol["preprocessing"]["representations_in_order"]),
                "pooling": "non_overlapping_4_by_4_mean",
                "feature_count": 4096,
                "model_retrained_or_tuned": False,
            },
            "runtime": {
                "total_seconds": total_seconds,
                "terrain_acquisition_seconds": acquisition["seconds"],
                "model_load_seconds": model_load_seconds,
                **timings,
                "valid_patches_per_second_excluding_acquisition": len(scored)
                / max(timings["preprocessing_seconds"] + timings["scoring_seconds"], 1e-12),
                "model_latency_ms_per_patch": 1000
                * timings["scoring_seconds"]
                / max(len(scored), 1),
                "peak_working_set_bytes": _peak_working_set_bytes(),
                "private_model_size_bytes": (
                    root / "data/private/e001/inference/e001_phase2f_random_forest.pkl"
                )
                .stat()
                .st_size,
                "bottleneck": "terrain_representation_and_pooling",
            },
            "review": {
                "blinded_packet_status": "READY_UNREVIEWED",
                "blinded_packet_items": packet_count,
                "score_rank_band_location_and_known_heritage_status_hidden": True,
                "human_morphology_review_performed": False,
                "heritage_record_cross_check_performed": False,
            },
            "interpretation": {
                "archaeological_probability_claimed": False,
                "discovery_claimed": False,
                "required_statement": protocol["score_semantics"]["required_statement"],
            },
            "privacy": {
                "aggregate_only": True,
                "exact_locations_written": False,
                "candidate_identifiers_written": False,
                "georeferenced_outputs_written": False,
                "private_artifacts_git_ignored": True,
                "coordinates_committed": False,
                "private_review_packet_git_ignored": True,
            },
        }
    )
    assert_coordinate_safe_mapping(public)
    public_path = root / PUBLIC_SUMMARY_RELATIVE
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_text(json.dumps(public, indent=2) + "\n", encoding="utf-8")
    figure_path = root / PUBLIC_FIGURE_RELATIVE
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    figure_path.write_text(_score_histogram_svg(score_values), encoding="utf-8")

    private_receipt = {
        "status": "READY_UNREVIEWED",
        "complete_score_table_sha256": score_table_sha256,
        "ranked_representatives": [private_scored_window_payload(item) for item in representatives],
        "queue_counts": {
            "HIGH": len(queues.high),
            "MEDIUM": len(queues.medium),
            "RANDOM": len(queues.reference),
        },
        "blinded_packet_relative_path": str(packet_root.relative_to(root)),
        "review_completed": False,
        "heritage_cross_check_completed": False,
    }
    (root / PRIVATE_RUN_RELATIVE / "inference_receipt.json").write_text(
        json.dumps(private_receipt, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": public["status"],
                "total_windows": public["total_windows"],
                "valid_windows": public["valid_windows"],
                "rejected_windows": public["rejected_windows"],
                "deduplicated_representatives": public["deduplicated_representatives"],
                "review_queue_counts": public["review_queue_counts"],
                "private_score_table_sha256": score_table_sha256,
                "total_seconds": total_seconds,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
