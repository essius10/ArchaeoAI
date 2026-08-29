# ruff: noqa: E501
"""Render coordinate-safe aggregate Phase 2E-B CNN figures as SVG."""

from __future__ import annotations

import csv
import html
import json
from collections import defaultdict

from archaeoai.paths import find_project_root

WIDTH = 820
HEIGHT = 520
LEFT = 88
TOP = 58
PLOT_WIDTH = 660
PLOT_HEIGHT = 370
BLUE = "#2b6cb0"
ORANGE = "#c05621"
GREEN = "#2f855a"
RED = "#c53030"


def _document(title: str, description: str, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">{html.escape(title)}</title>
<desc id="desc">{html.escape(description)}</desc>
<rect width="100%" height="100%" fill="#ffffff"/>
<style>text {{ font-family: Arial, sans-serif; fill: #1a202c; }} .axis {{ stroke: #4a5568; stroke-width: 1.5; }} .grid {{ stroke: #e2e8f0; stroke-width: 1; }} .label {{ font-size: 13px; }} .small {{ font-size: 11px; }}</style>
<text x="{WIDTH / 2}" y="29" text-anchor="middle" font-size="19" font-weight="700">{html.escape(title)}</text>
{body}
</svg>
"""


def _axes(label: str) -> list[str]:
    body = []
    for tick in range(6):
        value = tick / 5
        y = TOP + PLOT_HEIGHT * (1 - value)
        body.append(
            f'<line class="grid" x1="{LEFT}" y1="{y:.2f}" x2="{LEFT + PLOT_WIDTH}" y2="{y:.2f}"/>'
        )
        body.append(
            f'<text class="small" x="{LEFT - 12}" y="{y + 4:.2f}" text-anchor="end">{value:.1f}</text>'
        )
    body.extend(
        [
            f'<line class="axis" x1="{LEFT}" y1="{TOP}" x2="{LEFT}" y2="{TOP + PLOT_HEIGHT}"/>',
            f'<line class="axis" x1="{LEFT}" y1="{TOP + PLOT_HEIGHT}" x2="{LEFT + PLOT_WIDTH}" y2="{TOP + PLOT_HEIGHT}"/>',
            f'<text class="label" x="22" y="{TOP + PLOT_HEIGHT / 2}" text-anchor="middle" transform="rotate(-90 22 {TOP + PLOT_HEIGHT / 2})">{html.escape(label)}</text>',
        ]
    )
    return body


def _comparison(summary: dict[str, object]) -> str:
    body = _axes("Balanced accuracy")
    rows = summary["fold_comparison"]
    spacing = PLOT_WIDTH / len(rows)
    for index, row in enumerate(rows):
        centre = LEFT + spacing * (index + 0.5)
        for offset, key, color in (
            (-23, "cnn_mean_balanced_accuracy", BLUE),
            (23, "rf_balanced_accuracy", ORANGE),
        ):
            value = row[key]
            y = TOP + (1 - value) * PLOT_HEIGHT
            body.append(
                f'<rect x="{centre + offset - 19:.2f}" y="{y:.2f}" width="38" height="{TOP + PLOT_HEIGHT - y:.2f}" fill="{color}" opacity="0.86"/>'
            )
            body.append(
                f'<text class="small" x="{centre + offset:.2f}" y="{y - 7:.2f}" text-anchor="middle">{value:.3f}</text>'
            )
        body.append(
            f'<text class="label" x="{centre:.2f}" y="{TOP + PLOT_HEIGHT + 24}" text-anchor="middle">Fold {index + 1}</text>'
        )
    body.extend(
        [
            f'<rect x="{LEFT + 220}" y="{HEIGHT - 35}" width="13" height="13" fill="{BLUE}"/><text class="small" x="{LEFT + 239}" y="{HEIGHT - 24}">Compact CNN mean</text>',
            f'<rect x="{LEFT + 390}" y="{HEIGHT - 35}" width="13" height="13" fill="{ORANGE}"/><text class="small" x="{LEFT + 409}" y="{HEIGHT - 24}">Frozen Random Forest</text>',
        ]
    )
    return _document(
        "E001 post-hoc CNN versus Random Forest by geographic fold",
        "Five coordinate-safe fold-level balanced accuracy comparisons.",
        "\n".join(body),
    )


def _seed_stability(summary: dict[str, object]) -> str:
    body = _axes("Mean balanced accuracy across five folds")
    rows = summary["seed_mean_balanced_accuracy"]
    spacing = PLOT_WIDTH / len(rows)
    for index, row in enumerate(rows):
        value = row["mean_balanced_accuracy"]
        x = LEFT + spacing * (index + 0.5)
        y = TOP + (1 - value) * PLOT_HEIGHT
        body.extend(
            [
                f'<rect x="{x - 48:.2f}" y="{y:.2f}" width="96" height="{TOP + PLOT_HEIGHT - y:.2f}" fill="{GREEN}" opacity="0.86"/>',
                f'<text class="small" x="{x:.2f}" y="{y - 8:.2f}" text-anchor="middle">{value:.3f}</text>',
                f'<text class="small" x="{x:.2f}" y="{TOP + PLOT_HEIGHT + 24}" text-anchor="middle">{row["seed"]}</text>',
            ]
        )
    return _document(
        "E001 compact-CNN seed stability",
        "Mean geographic balanced accuracy for each of three frozen seeds.",
        "\n".join(body),
    )


def _training_history(rows: list[dict[str, str]]) -> str:
    title = "E001 compact-CNN aggregate training history"
    body = _axes("BCE loss")
    per_epoch: dict[int, dict[str, list[float]]] = defaultdict(
        lambda: {"training": [], "validation": []}
    )
    for row in rows:
        epoch = int(row["epoch"])
        per_epoch[epoch]["training"].append(float(row["training_loss"]))
        per_epoch[epoch]["validation"].append(float(row["internal_validation_loss"]))
    maximum_epoch = max(per_epoch)
    for key, color, label in (
        ("training", BLUE, "Training"),
        ("validation", RED, "Internal validation"),
    ):
        points = []
        for epoch, values in sorted(per_epoch.items()):
            mean = sum(values[key]) / len(values[key])
            x = LEFT + (epoch - 1) / max(1, maximum_epoch - 1) * PLOT_WIDTH
            y = TOP + (1 - mean) * PLOT_HEIGHT
            points.append(f"{x:.2f},{y:.2f}")
        body.append(
            f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="3"/>'
        )
        legend_x = LEFT + (230 if key == "training" else 390)
        body.append(
            f'<line x1="{legend_x}" y1="{HEIGHT - 28}" x2="{legend_x + 25}" y2="{HEIGHT - 28}" stroke="{color}" stroke-width="3"/><text class="small" x="{legend_x + 32}" y="{HEIGHT - 24}">{label}</text>'
        )
    body.append(
        f'<text class="label" x="{LEFT + PLOT_WIDTH / 2}" y="{TOP + PLOT_HEIGHT + 30}" text-anchor="middle">Epoch (means include runs still active)</text>'
    )
    return _document(
        title, "Aggregate coordinate-safe training and internal-validation loss.", "\n".join(body)
    )


def _confusion(summary: dict[str, object]) -> str:
    values = summary["aggregate_confusion_across_15_runs"]
    cells = [
        ("TN", values["tn"], BLUE, 185, 125),
        ("FP", values["fp"], ORANGE, 455, 125),
        ("FN", values["fn"], RED, 185, 315),
        ("TP", values["tp"], GREEN, 455, 315),
    ]
    body = []
    for label, value, color, x, y in cells:
        body.extend(
            [
                f'<rect x="{x}" y="{y}" width="180" height="130" rx="8" fill="{color}" opacity="0.20" stroke="{color}" stroke-width="2"/>',
                f'<text x="{x + 90}" y="{y + 52}" text-anchor="middle" font-size="18" font-weight="700">{label}</text>',
                f'<text x="{x + 90}" y="{y + 93}" text-anchor="middle" font-size="30">{value}</text>',
            ]
        )
    body.append(
        f'<text class="small" x="{WIDTH / 2}" y="{HEIGHT - 24}" text-anchor="middle">Each of 522 observations contributes once per seed; unlabelled background is not proven negative terrain.</text>'
    )
    return _document(
        "E001 aggregate compact-CNN confusion across 15 runs",
        "Aggregate true and false classifications across five folds and three seeds.",
        "\n".join(body),
    )


def main() -> int:
    root = find_project_root()
    summary = json.loads(
        (root / "outputs/deep_learning/e001_cnn_summary.json").read_text(encoding="utf-8")
    )
    if summary.get("status") != "COMPLETE" or summary.get("primary_runs_completed") != 15:
        raise ValueError("CNN figures require all frozen primary runs and final interpretation")
    with (root / "outputs/deep_learning/e001_cnn_training_history.csv").open(
        encoding="utf-8", newline=""
    ) as handle:
        history = list(csv.DictReader(handle))
    figures = {
        "e001_cnn_vs_rf_by_fold.svg": _comparison(summary),
        "e001_cnn_seed_stability.svg": _seed_stability(summary),
        "e001_cnn_training_history.svg": _training_history(history),
        "e001_cnn_confusion_summary.svg": _confusion(summary),
    }
    figure_root = root / "outputs/deep_learning/figures"
    figure_root.mkdir(parents=True, exist_ok=True)
    for name, content in figures.items():
        destination = figure_root / name
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite CNN figure: {destination}")
        destination.write_text(content, encoding="utf-8")
    print(f"Rendered {len(figures)} coordinate-safe CNN SVG figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
