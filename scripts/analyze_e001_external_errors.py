# ruff: noqa: E501
"""Run deterministic post-hoc Phase 4A analysis without model access or rescoring.

The SVG builders intentionally keep complete elements as single string literals so the generated
coordinate-safe figures remain easy to inspect and deterministic byte-for-byte.
"""

from __future__ import annotations

import binascii
import hashlib
import json
import struct
import zlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import confusion_matrix, precision_recall_curve, roc_curve

from archaeoai.external_evaluation import (
    EXPECTED_DATASET_SHA256,
    EXPECTED_MODEL_STATE_SHA256,
    EXPECTED_PREDICTION_VECTOR_SHA256,
    canonical_sha256,
    reproduce_from_private_predictions,
    validate_external_evaluation_result,
)
from archaeoai.terrain.full_dataset import REPRESENTATION_NAMES, load_processed_archive
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping

ROOT = Path(__file__).resolve().parents[1]
PHASE3C_PATH = ROOT / "outputs/external_validation/e001_phase3c_external_evaluation.json"
PRIVATE_PREDICTIONS_PATH = ROOT / "data/private/e001/external/evaluation/prediction_vector.json"
PRIVATE_MANIFEST_PATH = ROOT / "data/private/e001/external/dataset/dataset_manifest.json"
PRIVATE_PANEL_ROOT = ROOT / "data/private/e001/external/error_analysis/panels"
PUBLIC_RESULT_PATH = ROOT / "outputs/external_validation/e001_phase4a_error_analysis.json"
FIGURE_ROOT = ROOT / "outputs/external_validation/figures"
ANALYSIS_LABEL = "POST-HOC / EXPLORATORY"
OUTCOME_ORDER = ("TP", "TN", "FP", "FN")
COLORS = {"TP": "#2a9d8f", "TN": "#457b9d", "FP": "#e9c46a", "FN": "#e76f51"}


def _summary(values: list[float] | np.ndarray) -> dict[str, float | int]:
    array = np.asarray(values, dtype=np.float64)
    if array.size == 0 or not np.isfinite(array).all():
        raise ValueError("aggregate summary requires finite values")
    return {
        "count": int(array.size),
        "mean": float(array.mean()),
        "minimum": float(array.min()),
        "quartile_25": float(np.quantile(array, 0.25)),
        "median": float(np.median(array)),
        "quartile_75": float(np.quantile(array, 0.75)),
        "maximum": float(array.max()),
    }


def _outcome(label: int, prediction: int) -> str:
    return {
        (1, 1): "TP",
        (0, 0): "TN",
        (0, 1): "FP",
        (1, 0): "FN",
    }[(label, prediction)]


def _group_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    labels = np.asarray([row["label"] for row in rows], dtype=np.int8)
    predictions = np.asarray([row["prediction"] for row in rows], dtype=np.int8)
    scores = np.asarray([row["score"] for row in rows], dtype=np.float64)
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    positive_count = int((labels == 1).sum())
    background_count = int((labels == 0).sum())
    positive_recall = float(tp / positive_count) if positive_count else None
    background_recall = float(tn / background_count) if background_count else None
    balanced_accuracy = (
        float((positive_recall + background_recall) / 2)
        if positive_recall is not None and background_recall is not None
        else None
    )
    return {
        "observations": len(rows),
        "positive_bowl_barrow": positive_count,
        "unlabelled_background": background_count,
        "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "balanced_accuracy": balanced_accuracy,
        "positive_recall": positive_recall,
        "unlabelled_background_recall": background_recall,
        "model_score": _summary(scores),
    }


def _patch_summaries(values: np.ndarray) -> dict[str, float]:
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if not finite.size:
        raise ValueError("representation contains no finite terrain values")
    return {
        "patch_mean": float(finite.mean()),
        "patch_standard_deviation": float(finite.std()),
        "patch_interquartile_range": float(np.quantile(finite, 0.75) - np.quantile(finite, 0.25)),
        "patch_p95_minus_p05": float(np.quantile(finite, 0.95) - np.quantile(finite, 0.05)),
    }


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    checksum = binascii.crc32(kind + payload) & 0xFFFFFFFF
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", checksum)


def _write_grayscale_png(path: Path, pixels: np.ndarray) -> None:
    image = np.asarray(pixels, dtype=np.uint8)
    height, width = image.shape
    scanlines = b"".join(b"\x00" + image[row].tobytes() for row in range(height))
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(scanlines, level=9))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def _scaled_channel(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    finite = array[np.isfinite(array)]
    lower, upper = np.quantile(finite, [0.02, 0.98])
    if upper <= lower:
        return np.zeros(array.shape, dtype=np.uint8)
    scaled = np.clip((array - lower) / (upper - lower), 0, 1)
    scaled[~np.isfinite(scaled)] = 0
    return np.rint(scaled * 255).astype(np.uint8)


def _write_private_panels(rows: list[dict[str, Any]]) -> tuple[int, str]:
    PRIVATE_PANEL_ROOT.mkdir(parents=True, exist_ok=True)
    for existing in PRIVATE_PANEL_ROOT.glob("*.png"):
        existing.unlink()
    selected: list[dict[str, Any]] = []
    for outcome in OUTCOME_ORDER:
        candidates = [row for row in rows if row["outcome"] == outcome]
        ranked = sorted(
            candidates,
            key=lambda row: hashlib.sha256(
                f"phase4a-exemplar-v1:{outcome}:{row['sample_id']}".encode()
            ).hexdigest(),
        )
        selected.extend(ranked[:2])
    bundle = hashlib.sha256()
    for index, row in enumerate(selected):
        _, _, representations = load_processed_archive(ROOT / row["processed_path"])
        canvas = np.full((258, 258), 255, dtype=np.uint8)
        positions = ((0, 0), (0, 130), (130, 0), (130, 130))
        for name, (top, left) in zip(REPRESENTATION_NAMES, positions, strict=True):
            canvas[top : top + 128, left : left + 128] = _scaled_channel(representations[name])
        outcome_index = sum(item["outcome"] == row["outcome"] for item in selected[: index + 1])
        filename = f"{row['outcome']}_{outcome_index:02d}.png"
        destination = PRIVATE_PANEL_ROOT / filename
        _write_grayscale_png(destination, canvas)
        payload = destination.read_bytes()
        bundle.update(filename.encode())
        bundle.update(hashlib.sha256(payload).digest())
    return len(selected), bundle.hexdigest()


def _svg_start(title: str, description: str, *, width: int = 900, height: int = 540) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{title}</title>',
        f'<desc id="desc">{description}</desc>',
        '<rect width="100%" height="100%" fill="#fbfaf7"/>',
        f'<text x="{width / 2}" y="34" text-anchor="middle" font-family="Arial" font-size="22" font-weight="700" fill="#17324d">{title}</text>',
    ]


def _write_svg(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join([*lines, "</svg>", ""]), encoding="utf-8")


def _performance_figure() -> None:
    labels = ("Geographic final", "Geographic CV", "Compact CNN", "External test")
    values = (0.870968, 0.823406, 0.700866, 0.841667)
    intervals = ((0.774194, 0.951613), None, None, (0.775, 0.900))
    lines = _svg_start(
        "E001 performance context",
        "Coordinate-safe comparison across distinct confirmatory and post-hoc designs; values are not pooled.",
    )
    baseline_y, chart_height = 450, 330
    lines.extend(
        [
            '<line x1="90" y1="450" x2="850" y2="450" stroke="#17324d"/>',
            '<line x1="90" y1="120" x2="90" y2="450" stroke="#17324d"/>',
        ]
    )
    for tick in range(0, 11, 2):
        value = tick / 10
        y = baseline_y - value * chart_height
        lines.append(f'<line x1="85" y1="{y:.1f}" x2="850" y2="{y:.1f}" stroke="#d6d8dc"/>')
        lines.append(
            f'<text x="78" y="{y + 5:.1f}" text-anchor="end" font-family="Arial" font-size="12">{value:.1f}</text>'
        )
    for index, (label, value, interval) in enumerate(zip(labels, values, intervals, strict=True)):
        x = 130 + index * 185
        y = baseline_y - value * chart_height
        color = "#2a9d8f" if index == 3 else "#457b9d" if index < 2 else "#8d6a9f"
        lines.append(
            f'<rect x="{x}" y="{y:.1f}" width="95" height="{baseline_y - y:.1f}" rx="4" fill="{color}"/>'
        )
        lines.append(
            f'<text x="{x + 47.5}" y="{y - 10:.1f}" text-anchor="middle" font-family="Arial" font-size="14" font-weight="700">{value:.3f}</text>'
        )
        if interval is not None:
            low_y = baseline_y - interval[0] * chart_height
            high_y = baseline_y - interval[1] * chart_height
            centre = x + 47.5
            lines.extend(
                [
                    f'<line x1="{centre}" y1="{high_y:.1f}" x2="{centre}" y2="{low_y:.1f}" stroke="#111" stroke-width="2"/>',
                    f'<line x1="{centre - 9}" y1="{high_y:.1f}" x2="{centre + 9}" y2="{high_y:.1f}" stroke="#111" stroke-width="2"/>',
                    f'<line x1="{centre - 9}" y1="{low_y:.1f}" x2="{centre + 9}" y2="{low_y:.1f}" stroke="#111" stroke-width="2"/>',
                ]
            )
        lines.append(
            f'<text x="{x + 47.5}" y="478" text-anchor="middle" font-family="Arial" font-size="13">{label}</text>'
        )
    lines.append(
        '<text x="470" y="518" text-anchor="middle" font-family="Arial" font-size="12" fill="#52606d">External test: 120 observations; matched-pair 95% CI. Designs differ and are not pooled.</text>'
    )
    _write_svg(FIGURE_ROOT / "e001_phase3c_performance_context.svg", lines)


def _confusion_figure() -> None:
    matrix = ((52, 8), (11, 49))
    lines = _svg_start(
        "External-test confusion matrix",
        "Aggregate counts from the frozen 120-observation Phase 3C evaluation.",
        width=760,
        height=560,
    )
    x0, y0, size = 230, 100, 170
    maximum = max(max(row) for row in matrix)
    for row in range(2):
        for column in range(2):
            count = matrix[row][column]
            opacity = 0.18 + 0.72 * count / maximum
            x, y = x0 + column * size, y0 + row * size
            lines.append(
                f'<rect x="{x}" y="{y}" width="{size}" height="{size}" fill="#2a6f97" fill-opacity="{opacity:.3f}" stroke="#ffffff" stroke-width="3"/>'
            )
            lines.append(
                f'<text x="{x + size / 2}" y="{y + size / 2 + 12}" text-anchor="middle" font-family="Arial" font-size="34" font-weight="700" fill="#102a43">{count}</text>'
            )
    for index, label in enumerate(("Background", "Bowl barrow")):
        lines.append(
            f'<text x="{x0 + index * size + size / 2}" y="465" text-anchor="middle" font-family="Arial" font-size="15">Predicted {label}</text>'
        )
        lines.append(
            f'<text x="185" y="{y0 + index * size + size / 2}" text-anchor="middle" font-family="Arial" font-size="15" transform="rotate(-90 185 {y0 + index * size + size / 2})">Observed {label}</text>'
        )
    lines.append(
        '<text x="380" y="525" text-anchor="middle" font-family="Arial" font-size="12" fill="#52606d">Background denotes unlabelled terrain, not confirmed archaeology-free terrain.</text>'
    )
    _write_svg(FIGURE_ROOT / "e001_phase3c_confusion_matrix.svg", lines)


def _curve_path(x_values: np.ndarray, y_values: np.ndarray, *, x0: int, y0: int, size: int) -> str:
    points = [
        f"{x0 + float(x) * size:.2f},{y0 + (1 - float(y)) * size:.2f}"
        for x, y in zip(x_values, y_values, strict=True)
    ]
    return "M " + " L ".join(points)


def _curve_figure(rows: list[dict[str, Any]]) -> None:
    labels = np.asarray([row["label"] for row in rows], dtype=np.int8)
    scores = np.asarray([row["score"] for row in rows], dtype=np.float64)
    false_positive_rate, true_positive_rate, _ = roc_curve(labels, scores)
    precision, recall, _ = precision_recall_curve(labels, scores)
    lines = _svg_start(
        "Frozen external score curves",
        "ROC and precision-recall curves from the spent Phase 3C score vector; model score is not archaeological probability.",
        width=960,
        height=520,
    )
    for x0, title in ((90, "ROC"), (540, "Precision–recall")):
        lines.extend(
            [
                f'<rect x="{x0}" y="90" width="330" height="330" fill="#fff" stroke="#17324d"/>',
                f'<text x="{x0 + 165}" y="72" text-anchor="middle" font-family="Arial" font-size="17" font-weight="700">{title}</text>',
            ]
        )
    lines.append(
        '<path d="M 90,420 L 420,90" fill="none" stroke="#b8b8b8" stroke-dasharray="6 5"/>'
    )
    lines.append(
        f'<path d="{_curve_path(false_positive_rate, true_positive_rate, x0=90, y0=90, size=330)}" fill="none" stroke="#2a9d8f" stroke-width="3"/>'
    )
    lines.append(
        '<path d="M 540,255 L 870,255" fill="none" stroke="#b8b8b8" stroke-dasharray="6 5"/>'
    )
    lines.append(
        f'<path d="{_curve_path(recall, precision, x0=540, y0=90, size=330)}" fill="none" stroke="#e76f51" stroke-width="3"/>'
    )
    lines.extend(
        [
            '<text x="255" y="455" text-anchor="middle" font-family="Arial" font-size="13">False-positive rate</text>',
            '<text x="705" y="455" text-anchor="middle" font-family="Arial" font-size="13">Recall</text>',
            '<text x="40" y="255" text-anchor="middle" font-family="Arial" font-size="13" transform="rotate(-90 40 255)">True-positive rate</text>',
            '<text x="490" y="255" text-anchor="middle" font-family="Arial" font-size="13" transform="rotate(-90 490 255)">Precision</text>',
            '<text x="480" y="493" text-anchor="middle" font-family="Arial" font-size="12" fill="#52606d">ROC-AUC 0.927778 · average precision 0.942058 · exploratory visualization of frozen confirmatory scores</text>',
        ]
    )
    _write_svg(FIGURE_ROOT / "e001_phase3c_roc_pr_curves.svg", lines)


def _score_distribution_figure(rows: list[dict[str, Any]]) -> None:
    bins = np.linspace(0, 1, 11)
    lines = _svg_start(
        "Post-hoc external model-score distributions",
        "Exploratory histogram counts by frozen confusion outcome. Scores are terrain-similarity scores, not archaeological probabilities.",
    )
    maximum = 1
    counts_by_outcome: dict[str, np.ndarray] = {}
    for outcome in OUTCOME_ORDER:
        values = [row["score"] for row in rows if row["outcome"] == outcome]
        counts, _ = np.histogram(values, bins=bins)
        counts_by_outcome[outcome] = counts
        maximum = max(maximum, int(counts.max()))
    x0, y0, width, height = 90, 90, 740, 350
    lines.extend(
        [
            f'<rect x="{x0}" y="{y0}" width="{width}" height="{height}" fill="#fff" stroke="#17324d"/>',
            f'<text x="{x0 + width / 2}" y="490" text-anchor="middle" font-family="Arial" font-size="14">Frozen model score</text>',
        ]
    )
    for outcome_index, outcome in enumerate(OUTCOME_ORDER):
        points = []
        for bin_index, count in enumerate(counts_by_outcome[outcome]):
            x = x0 + (bin_index + 0.5) / 10 * width
            y = y0 + height - count / maximum * height
            points.append(f"{x:.1f},{y:.1f}")
        lines.append(
            f'<polyline points="{" ".join(points)}" fill="none" stroke="{COLORS[outcome]}" stroke-width="3"/>'
        )
        legend_x = 115 + outcome_index * 175
        lines.append(
            f'<line x1="{legend_x}" y1="60" x2="{legend_x + 26}" y2="60" stroke="{COLORS[outcome]}" stroke-width="4"/>'
        )
        lines.append(
            f'<text x="{legend_x + 34}" y="65" font-family="Arial" font-size="13">{outcome}</text>'
        )
    lines.append(
        '<text x="450" y="520" text-anchor="middle" font-family="Arial" font-size="12" fill="#52606d">POST-HOC / EXPLORATORY · fixed 0.1-wide bins · no threshold optimization</text>'
    )
    _write_svg(FIGURE_ROOT / "e001_phase4a_score_distributions.svg", lines)


def _representation_figure(
    representation_rows: dict[str, dict[str, list[float]]],
) -> None:
    lines = _svg_start(
        "Post-hoc terrain variability by error group",
        "Exploratory group medians of per-patch representation standard deviation, standardized only for display.",
        width=980,
        height=560,
    )
    names = list(REPRESENTATION_NAMES)
    display = {
        "elevation_normalized": "Elevation",
        "slope_degrees": "Slope",
        "hillshade_315_45": "Hillshade",
        "local_relief_r16m": "Local relief",
    }
    standardized: dict[str, dict[str, float]] = defaultdict(dict)
    for name in names:
        all_values = np.concatenate(
            [
                representation_rows[outcome][f"{name}:patch_standard_deviation"]
                for outcome in OUTCOME_ORDER
            ]
        )
        centre, scale = float(all_values.mean()), float(all_values.std())
        for outcome in OUTCOME_ORDER:
            median = float(
                np.median(representation_rows[outcome][f"{name}:patch_standard_deviation"])
            )
            standardized[outcome][name] = (median - centre) / scale if scale else 0.0
    x0, y_mid, group_width = 115, 285, 205
    lines.extend(
        [
            '<line x1="80" y1="285" x2="930" y2="285" stroke="#17324d"/>',
            '<text x="35" y="290" font-family="Arial" font-size="12">0</text>',
        ]
    )
    for name_index, name in enumerate(names):
        base_x = x0 + name_index * group_width
        for outcome_index, outcome in enumerate(OUTCOME_ORDER):
            value = standardized[outcome][name]
            bar_height = abs(value) * 115
            x = base_x + outcome_index * 34
            y = y_mid - bar_height if value >= 0 else y_mid
            lines.append(
                f'<rect x="{x}" y="{y:.1f}" width="25" height="{bar_height:.1f}" fill="{COLORS[outcome]}"/>'
            )
        lines.append(
            f'<text x="{base_x + 51}" y="450" text-anchor="middle" font-family="Arial" font-size="14">{display[name]}</text>'
        )
    for outcome_index, outcome in enumerate(OUTCOME_ORDER):
        x = 235 + outcome_index * 135
        lines.append(f'<rect x="{x}" y="68" width="18" height="18" fill="{COLORS[outcome]}"/>')
        lines.append(
            f'<text x="{x + 27}" y="82" font-family="Arial" font-size="13">{outcome}</text>'
        )
    lines.extend(
        [
            '<text x="28" y="285" text-anchor="middle" font-family="Arial" font-size="12" transform="rotate(-90 28 285)">Standardized group median</text>',
            '<text x="490" y="505" text-anchor="middle" font-family="Arial" font-size="12" fill="#52606d">POST-HOC / EXPLORATORY · descriptive terrain summaries only · not model attribution</text>',
        ]
    )
    _write_svg(FIGURE_ROOT / "e001_phase4a_error_representation_summary.svg", lines)


def analyze() -> dict[str, Any]:
    phase3c = validate_external_evaluation_result(PHASE3C_PATH)
    reproduce_from_private_predictions(PRIVATE_PREDICTIONS_PATH, PHASE3C_PATH)
    private_predictions = json.loads(PRIVATE_PREDICTIONS_PATH.read_text(encoding="utf-8"))
    if canonical_sha256(private_predictions["rows"]) != EXPECTED_PREDICTION_VECTOR_SHA256:
        raise ValueError("frozen prediction vector changed")
    manifest = json.loads(PRIVATE_MANIFEST_PATH.read_text(encoding="utf-8"))
    if manifest["dataset_sha256"] != EXPECTED_DATASET_SHA256:
        raise ValueError("external dataset changed")
    manifest_by_id = {row["sample_id"]: row for row in manifest["observations"]}
    rows: list[dict[str, Any]] = []
    representation_rows: dict[str, dict[str, list[float]]] = {
        outcome: defaultdict(list) for outcome in OUTCOME_ORDER
    }
    nodata_by_outcome: dict[str, list[float]] = defaultdict(list)
    for prediction in private_predictions["rows"]:
        manifest_row = manifest_by_id[prediction["sample_id"]]
        label = 1 if prediction["class_label"] == "positive_bowl_barrow" else 0
        outcome = _outcome(label, int(prediction["prediction"]))
        row = {
            "sample_id": prediction["sample_id"],
            "pair_id": prediction["pair_id"],
            "label": label,
            "prediction": int(prediction["prediction"]),
            "score": float(prediction["score"]),
            "outcome": outcome,
            "region": prediction["region"],
            "survey_year": str(manifest_row["terrain_year"]),
            "survey_program": manifest_row["survey_program"],
            "terrain_provenance_id": manifest_row["terrain_provenance_id"],
            "source_resolution_m": float(manifest_row["source_resolution_m"]),
            "nodata_fraction": float(manifest_row["nodata_fraction"]),
            "processed_path": manifest_row["processed_path"],
        }
        rows.append(row)
        nodata_by_outcome[outcome].append(row["nodata_fraction"])
        _, _, representations = load_processed_archive(ROOT / row["processed_path"])
        for name in REPRESENTATION_NAMES:
            for statistic, value in _patch_summaries(representations[name]).items():
                representation_rows[outcome][f"{name}:{statistic}"].append(value)
    if Counter(row["outcome"] for row in rows) != {"TN": 52, "FP": 8, "FN": 11, "TP": 49}:
        raise ValueError("post-hoc confusion groups do not reproduce Phase 3C")

    score_groups = {
        outcome: _summary([row["score"] for row in rows if row["outcome"] == outcome])
        for outcome in OUTCOME_ORDER
    }
    representation_summary: dict[str, Any] = {}
    for outcome in OUTCOME_ORDER:
        representation_summary[outcome] = {}
        for name in REPRESENTATION_NAMES:
            representation_summary[outcome][name] = {
                statistic: _summary(representation_rows[outcome][f"{name}:{statistic}"])
                for statistic in (
                    "patch_mean",
                    "patch_standard_deviation",
                    "patch_interquartile_range",
                    "patch_p95_minus_p05",
                )
            }
    regions = {
        region: {
            "analysis_label": ANALYSIS_LABEL,
            "high_uncertainty_small_stratum": len(
                {row["pair_id"] for row in rows if row["region"] == region}
            )
            < 10,
            "matched_pairs": len({row["pair_id"] for row in rows if row["region"] == region}),
            **_group_metrics([row for row in rows if row["region"] == region]),
        }
        for region in sorted({row["region"] for row in rows})
    }
    survey_years = {
        year: {
            "analysis_label": ANALYSIS_LABEL,
            **_group_metrics([row for row in rows if row["survey_year"] == year]),
        }
        for year in sorted({row["survey_year"] for row in rows})
    }
    provenance = {
        f"year_{year}__1m__National_LIDAR_Programme": {
            "analysis_label": ANALYSIS_LABEL,
            **_group_metrics(
                [
                    row
                    for row in rows
                    if row["terrain_provenance_id"] == provenance_id and row["survey_year"] == year
                ]
            ),
        }
        for provenance_id, year in sorted(
            {(row["terrain_provenance_id"], row["survey_year"]) for row in rows},
            key=lambda item: item[1],
        )
    }
    panel_count, panel_bundle_sha256 = _write_private_panels(rows)
    _performance_figure()
    _confusion_figure()
    _curve_figure(rows)
    _score_distribution_figure(rows)
    _representation_figure(representation_rows)
    figure_paths = sorted(FIGURE_ROOT.glob("e001_phase*.svg"))
    figure_hashes = {
        str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in figure_paths
        if "phase3c" in path.name or "phase4a" in path.name
    }
    output: dict[str, Any] = {
        "schema_version": "e001-phase-4a-external-error-analysis-v1",
        "phase": "4A post-hoc external error analysis and scientific consolidation",
        "status": "COMPLETE_EXPLORATORY",
        "analysis_label": ANALYSIS_LABEL,
        "confirmatory_result_unchanged": True,
        "external_test_spent": True,
        "source_bindings": {
            "phase3c_result_sha256": phase3c["result_sha256"],
            "dataset_sha256": EXPECTED_DATASET_SHA256,
            "model_state_sha256": EXPECTED_MODEL_STATE_SHA256,
            "prediction_vector_sha256": EXPECTED_PREDICTION_VECTOR_SHA256,
            "phase3c_balanced_accuracy": phase3c["primary"]["metrics"]["balanced_accuracy"],
            "phase3c_lower_95": phase3c["primary"]["confidence_interval"]["lower_95"],
            "phase3c_upper_95": phase3c["primary"]["confidence_interval"]["upper_95"],
        },
        "error_groups": dict(sorted(Counter(row["outcome"] for row in rows).items())),
        "model_score_distributions": score_groups,
        "terrain_representation_summaries": representation_summary,
        "nodata_fraction_by_error_group": {
            outcome: _summary(nodata_by_outcome[outcome]) for outcome in OUTCOME_ORDER
        },
        "regional_descriptive_results": regions,
        "provenance_descriptive_results": {
            "survey_year": survey_years,
            "terrain_provenance": provenance,
            "survey_program_counts": dict(
                sorted(Counter(row["survey_program"] for row in rows).items())
            ),
            "source_resolution_m_counts": {
                str(key): value
                for key, value in sorted(
                    Counter(row["source_resolution_m"] for row in rows).items()
                )
            },
            "causal_interpretation_allowed": False,
        },
        "strongest_exploratory_patterns": [
            {
                "pattern": "false negatives have weaker local terrain variability than true positives",
                "evidence": {
                    "slope_standard_deviation_median_FN": 0.85538,
                    "slope_standard_deviation_median_TP": 2.232815,
                    "hillshade_standard_deviation_median_FN": 0.014815,
                    "hillshade_standard_deviation_median_TP": 0.028856,
                    "local_relief_standard_deviation_median_FN": 0.095638,
                    "local_relief_standard_deviation_median_TP": 0.181609,
                },
                "interpretation_limit": "descriptive association, not feature attribution or causality",
            },
            {
                "pattern": "false-positive backgrounds have stronger local terrain variability than true negatives",
                "evidence": {
                    "slope_standard_deviation_median_FP": 3.152518,
                    "slope_standard_deviation_median_TN": 2.089191,
                    "hillshade_standard_deviation_median_FP": 0.038626,
                    "hillshade_standard_deviation_median_TN": 0.024433,
                    "local_relief_standard_deviation_median_FP": 0.220089,
                    "local_relief_standard_deviation_median_TN": 0.166352,
                },
                "interpretation_limit": "eight false positives only; background archaeology remains unknown",
            },
            {
                "pattern": "false negatives are concentrated in the first external geography and 2021 stratum",
                "evidence": {
                    "first_geography_false_negatives": 9,
                    "all_other_geographies_false_negatives": 2,
                    "year_2021_positive_recall": 0.756757,
                    "year_2020_positive_recall": 0.882353,
                    "year_2019_positive_recall": 1.0,
                },
                "interpretation_limit": "region, sample composition, and survey year are confounded",
            },
            {
                "pattern": "missing terrain pixels do not distinguish error groups",
                "evidence": {"maximum_nodata_fraction_all_groups": 0.0},
                "interpretation_limit": "other acquisition or processing differences may still exist",
            },
        ],
        "private_exemplars": {
            "count": panel_count,
            "per_error_group": 2,
            "selection": "lowest_SHA256_rank_within_frozen_error_group",
            "coordinate_or_identifier_metadata_written": False,
            "git_ignored": True,
            "bundle_sha256": panel_bundle_sha256,
        },
        "figures": figure_hashes,
        "hypotheses": [
            {
                "id": "H4A-01",
                "statement": "documented bowl-barrow patches with weaker slope, hillshade, and local-relief variability may be more likely to become false negatives",
                "future_test": "pre-register relief-stratified evaluation on a new independent dataset",
            },
            {
                "id": "H4A-02",
                "statement": "high-variability unlabelled terrain may increase false-positive classifications",
                "future_test": "collect independently reviewed hard-background terrain contexts without relabelling the spent sample",
            },
            {
                "id": "H4A-03",
                "statement": "fixed single-azimuth hillshade may represent some low-relief barrow morphology less consistently",
                "future_test": "compare frozen single- and multi-azimuth designs as a new model generation with new independent evaluation data",
            },
            {
                "id": "H4A-04",
                "statement": "regional terrain context or year-linked acquisition differences may contribute to the concentration of false negatives",
                "future_test": "use a prospectively balanced multi-region and multi-year validation design that separates geography from provenance",
            },
            {
                "id": "H4A-05",
                "statement": "model scores near the fixed threshold may identify morphologically ambiguous terrain rather than calibrated archaeological uncertainty",
                "future_test": "pre-register an ambiguity or abstention study on new data without changing the reported Phase 3C threshold",
            },
        ],
        "scientific_status": {
            "preferred_current_model": "frozen E001 Random Forest",
            "phase3_external_data_used_for_current_model_training": False,
            "future_model_using_phase3_data_is_new_model_generation": True,
            "new_independent_evaluation_required_for_future_model": True,
            "retraining_performed": False,
            "rescoring_performed": False,
            "threshold_changed": False,
            "observations_removed_or_relabelled": False,
        },
        "privacy": {
            "aggregate_only": True,
            "coordinates_written": False,
            "sample_identifiers_written": False,
            "private_prediction_rows_written": False,
            "maps_created": False,
            "private_panels_tracked": False,
        },
    }
    assert_coordinate_safe_mapping(output)
    output["analysis_sha256"] = canonical_sha256(output, omit="analysis_sha256")
    PUBLIC_RESULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_RESULT_PATH.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return output


if __name__ == "__main__":
    analyze()
