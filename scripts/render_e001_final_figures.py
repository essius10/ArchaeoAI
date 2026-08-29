# ruff: noqa: E501
"""Render coordinate-safe E001 aggregate result figures as dependency-free SVG."""

from __future__ import annotations

import html
import json

from archaeoai.paths import find_project_root

WIDTH = 760
HEIGHT = 520
PLOT_LEFT = 90
PLOT_TOP = 55
PLOT_WIDTH = 600
PLOT_HEIGHT = 380
COLORS = {"random": "#2b6cb0", "geographic": "#2f855a"}


def _svg_document(title: str, body: str) -> str:
    safe_title = html.escape(title)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">{safe_title}</title>
<desc id="desc">Coordinate-safe aggregate E001 result figure.</desc>
<rect width="100%" height="100%" fill="#ffffff"/>
<style>text {{ font-family: Arial, sans-serif; fill: #1a202c; }} .axis {{ stroke: #4a5568; stroke-width: 1.5; }} .grid {{ stroke: #e2e8f0; stroke-width: 1; }} .label {{ font-size: 14px; }} .small {{ font-size: 12px; }}</style>
<text x="{WIDTH / 2}" y="28" text-anchor="middle" font-size="20" font-weight="700">{safe_title}</text>
{body}
</svg>
"""


def _axes(*, x_label: str, y_label: str, show_numeric_x_ticks: bool = True) -> str:
    elements = []
    for tick in range(6):
        value = tick / 5
        y = PLOT_TOP + PLOT_HEIGHT * (1 - value)
        x = PLOT_LEFT + PLOT_WIDTH * value
        elements.append(
            f'<line class="grid" x1="{PLOT_LEFT}" y1="{y:.2f}" x2="{PLOT_LEFT + PLOT_WIDTH}" y2="{y:.2f}"/>'
        )
        elements.append(
            f'<text class="small" x="{PLOT_LEFT - 12}" y="{y + 4:.2f}" text-anchor="end">{value:.1f}</text>'
        )
        if show_numeric_x_ticks:
            elements.append(
                f'<text class="small" x="{x:.2f}" y="{PLOT_TOP + PLOT_HEIGHT + 22}" text-anchor="middle">{value:.1f}</text>'
            )
    elements.extend(
        [
            f'<line class="axis" x1="{PLOT_LEFT}" y1="{PLOT_TOP}" x2="{PLOT_LEFT}" y2="{PLOT_TOP + PLOT_HEIGHT}"/>',
            f'<line class="axis" x1="{PLOT_LEFT}" y1="{PLOT_TOP + PLOT_HEIGHT}" x2="{PLOT_LEFT + PLOT_WIDTH}" y2="{PLOT_TOP + PLOT_HEIGHT}"/>',
            f'<text class="label" x="{PLOT_LEFT + PLOT_WIDTH / 2}" y="{HEIGHT - 28}" text-anchor="middle">{html.escape(x_label)}</text>',
            f'<text class="label" x="22" y="{PLOT_TOP + PLOT_HEIGHT / 2}" text-anchor="middle" transform="rotate(-90 22 {PLOT_TOP + PLOT_HEIGHT / 2})">{html.escape(y_label)}</text>',
        ]
    )
    return "\n".join(elements)


def _polyline(points: list[list[float]], color: str) -> str:
    rendered = " ".join(
        f"{PLOT_LEFT + x * PLOT_WIDTH:.2f},{PLOT_TOP + (1 - y) * PLOT_HEIGHT:.2f}"
        for x, y in points
    )
    return f'<polyline points="{rendered}" fill="none" stroke="{color}" stroke-width="3"/>'


def _curve_figure(results: dict[str, object], *, curve: str) -> str:
    if curve == "roc":
        title = "E001 final ROC curves"
        x_label, y_label = "False-positive rate", "True-positive rate"
    else:
        title = "E001 final precision–recall curves"
        x_label, y_label = "Recall", "Precision"
    body = [_axes(x_label=x_label, y_label=y_label)]
    if curve == "roc":
        body.append(
            f'<line x1="{PLOT_LEFT}" y1="{PLOT_TOP + PLOT_HEIGHT}" x2="{PLOT_LEFT + PLOT_WIDTH}" y2="{PLOT_TOP}" stroke="#a0aec0" stroke-dasharray="6 6"/>'
        )
    for index, condition in enumerate(("random", "geographic")):
        item = results["conditions"][condition]
        body.append(_polyline(item["curves"][curve], COLORS[condition]))
        metric_name = "roc_auc" if curve == "roc" else "average_precision"
        metric = item["metrics"][metric_name]
        body.append(
            f'<rect x="{PLOT_LEFT + 390}" y="{PLOT_TOP + 18 + index * 28}" width="18" height="4" fill="{COLORS[condition]}"/>'
            f'<text class="small" x="{PLOT_LEFT + 416}" y="{PLOT_TOP + 25 + index * 28}">{condition.title()} ({metric:.3f})</text>'
        )
    return _svg_document(title, "\n".join(body))


def _balanced_accuracy_figure(results: dict[str, object]) -> str:
    title = "E001 final balanced accuracy with group-bootstrap 95% intervals"
    body = [
        _axes(
            x_label="Evaluation condition",
            y_label="Balanced accuracy",
            show_numeric_x_ticks=False,
        )
    ]
    positions = {"random": PLOT_LEFT + 200, "geographic": PLOT_LEFT + 420}
    for condition, x in positions.items():
        item = results["conditions"][condition]
        score = item["metrics"]["balanced_accuracy"]
        interval = item["bootstrap"]["intervals"]["balanced_accuracy"]
        y = PLOT_TOP + (1 - score) * PLOT_HEIGHT
        lower_y = PLOT_TOP + (1 - interval["lower"]) * PLOT_HEIGHT
        upper_y = PLOT_TOP + (1 - interval["upper"]) * PLOT_HEIGHT
        body.extend(
            [
                f'<rect x="{x - 48}" y="{y:.2f}" width="96" height="{PLOT_TOP + PLOT_HEIGHT - y:.2f}" fill="{COLORS[condition]}" opacity="0.85"/>',
                f'<line x1="{x}" y1="{upper_y:.2f}" x2="{x}" y2="{lower_y:.2f}" stroke="#1a202c" stroke-width="2"/>',
                f'<line x1="{x - 12}" y1="{upper_y:.2f}" x2="{x + 12}" y2="{upper_y:.2f}" stroke="#1a202c" stroke-width="2"/>',
                f'<line x1="{x - 12}" y1="{lower_y:.2f}" x2="{x + 12}" y2="{lower_y:.2f}" stroke="#1a202c" stroke-width="2"/>',
                f'<text class="label" x="{x}" y="{y - 10:.2f}" text-anchor="middle">{score:.3f}</text>',
                f'<text class="label" x="{x}" y="{PLOT_TOP + PLOT_HEIGHT + 44}" text-anchor="middle">{condition.title()}</text>',
            ]
        )
    return _svg_document(title, "\n".join(body))


def _confusion_figure(results: dict[str, object], condition: str) -> str:
    matrix = results["conditions"][condition]["metrics"]["confusion_matrix"]
    values = [
        matrix["true_unlabelled_background_predicted_unlabelled_background"],
        matrix["true_unlabelled_background_predicted_positive_bowl_barrow"],
        matrix["true_positive_bowl_barrow_predicted_unlabelled_background"],
        matrix["true_positive_bowl_barrow_predicted_positive_bowl_barrow"],
    ]
    title = f"E001 {condition} final confusion matrix"
    left, top, cell = 220, 100, 140
    body = [
        f'<text class="small" x="{left + cell}" y="72" text-anchor="middle">Predicted class</text>',
        f'<text class="small" x="72" y="{top + cell}" text-anchor="middle" transform="rotate(-90 72 {top + cell})">True class</text>',
        f'<text class="small" x="{left + cell / 2}" y="92" text-anchor="middle">Unlabelled background</text>',
        f'<text class="small" x="{left + cell * 1.5}" y="92" text-anchor="middle">Positive bowl barrow</text>',
        f'<text class="small" x="{left - 10}" y="{top + cell / 2}" text-anchor="end">Unlabelled background</text>',
        f'<text class="small" x="{left - 10}" y="{top + cell * 1.5}" text-anchor="end">Positive bowl barrow</text>',
    ]
    for index, value in enumerate(values):
        row, column = divmod(index, 2)
        opacity = 0.18 + 0.72 * value / 31
        x, y = left + column * cell, top + row * cell
        body.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" fill="{COLORS[condition]}" opacity="{opacity:.3f}" stroke="#ffffff" stroke-width="3"/>'
            f'<text x="{x + cell / 2}" y="{y + cell / 2 + 9}" text-anchor="middle" font-size="28" font-weight="700">{value}</text>'
        )
    body.append(
        f'<text class="small" x="{WIDTH / 2}" y="{HEIGHT - 42}" text-anchor="middle">n=62; 31 observations per class; threshold 0.5</text>'
    )
    return _svg_document(title, "\n".join(body))


def main() -> int:
    root = find_project_root()
    results = json.loads(
        (root / "outputs/modelling/e001_random_vs_geographic.json").read_text(encoding="utf-8")
    )
    if results.get("final_test_evaluated") is not True:
        raise ValueError("final figures require the frozen final result")
    figure_root = root / "outputs/modelling/figures"
    figure_root.mkdir(parents=True, exist_ok=True)
    figures = {
        "e001_balanced_accuracy_comparison.svg": _balanced_accuracy_figure(results),
        "e001_geographic_confusion_matrix.svg": _confusion_figure(results, "geographic"),
        "e001_random_confusion_matrix.svg": _confusion_figure(results, "random"),
        "e001_roc_curves.svg": _curve_figure(results, curve="roc"),
        "e001_precision_recall_curves.svg": _curve_figure(results, curve="precision_recall"),
    }
    for name, content in figures.items():
        destination = figure_root / name
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite final figure: {destination}")
        destination.write_text(content, encoding="utf-8")
    print(f"Rendered {len(figures)} coordinate-safe SVG figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
