# ruff: noqa: E501
"""Render coordinate-safe Phase 2E-A robustness figures as SVG."""

from __future__ import annotations

import html
import json

from archaeoai.paths import find_project_root

WIDTH = 820
HEIGHT = 520
LEFT = 88
TOP = 58
PLOT_WIDTH = 660
PLOT_HEIGHT = 370
GREEN = "#2f855a"
BLUE = "#2b6cb0"
ORANGE = "#c05621"


def _document(title: str, body: str) -> str:
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">
<title id="title">{html.escape(title)}</title>
<desc id="desc">Coordinate-safe aggregate E001 post-hoc robustness figure.</desc>
<rect width="100%" height="100%" fill="#ffffff"/>
<style>text {{ font-family: Arial, sans-serif; fill: #1a202c; }} .axis {{ stroke: #4a5568; stroke-width: 1.5; }} .grid {{ stroke: #e2e8f0; stroke-width: 1; }} .label {{ font-size: 13px; }} .small {{ font-size: 11px; }}</style>
<text x="{WIDTH / 2}" y="29" text-anchor="middle" font-size="19" font-weight="700">{html.escape(title)}</text>
{body}
</svg>
"""


def _y_axis(y_label: str) -> list[str]:
    elements = []
    for tick in range(6):
        value = tick / 5
        y = TOP + PLOT_HEIGHT * (1 - value)
        elements.append(
            f'<line class="grid" x1="{LEFT}" y1="{y:.2f}" x2="{LEFT + PLOT_WIDTH}" y2="{y:.2f}"/>'
        )
        elements.append(
            f'<text class="small" x="{LEFT - 12}" y="{y + 4:.2f}" text-anchor="end">{value:.1f}</text>'
        )
    elements.extend(
        [
            f'<line class="axis" x1="{LEFT}" y1="{TOP}" x2="{LEFT}" y2="{TOP + PLOT_HEIGHT}"/>',
            f'<line class="axis" x1="{LEFT}" y1="{TOP + PLOT_HEIGHT}" x2="{LEFT + PLOT_WIDTH}" y2="{TOP + PLOT_HEIGHT}"/>',
            f'<text class="label" x="22" y="{TOP + PLOT_HEIGHT / 2}" text-anchor="middle" transform="rotate(-90 22 {TOP + PLOT_HEIGHT / 2})">{html.escape(y_label)}</text>',
        ]
    )
    return elements


def _bar_figure(title: str, labels: list[str], values: list[float], color: str) -> str:
    body = _y_axis("Balanced accuracy")
    spacing = PLOT_WIDTH / len(values)
    bar_width = min(70, spacing * 0.62)
    for index, (label, value) in enumerate(zip(labels, values, strict=True)):
        x = LEFT + spacing * (index + 0.5)
        y = TOP + (1 - value) * PLOT_HEIGHT
        body.extend(
            [
                f'<rect x="{x - bar_width / 2:.2f}" y="{y:.2f}" width="{bar_width:.2f}" height="{TOP + PLOT_HEIGHT - y:.2f}" fill="{color}" opacity="0.86"/>',
                f'<text class="small" x="{x:.2f}" y="{y - 8:.2f}" text-anchor="middle">{value:.3f}</text>',
                f'<text class="small" x="{x:.2f}" y="{TOP + PLOT_HEIGHT + 24}" text-anchor="middle" transform="rotate(-22 {x:.2f} {TOP + PLOT_HEIGHT + 24})">{html.escape(label)}</text>',
            ]
        )
    return _document(title, "\n".join(body))


def _learning_curve(summary: dict[str, object]) -> str:
    title = "E001 post-hoc group-aware training-size sensitivity"
    body = _y_axis("Mean geographic-fold balanced accuracy")
    fractions = [0.25, 0.5, 0.75, 1.0]
    points = []
    for fraction in fractions:
        value = summary["training_fraction_summaries"][str(fraction)]["mean"]
        x = LEFT + (fraction - 0.25) / 0.75 * PLOT_WIDTH
        y = TOP + (1 - value) * PLOT_HEIGHT
        points.append((x, y, value, fraction))
    rendered = " ".join(f"{x:.2f},{y:.2f}" for x, y, _value, _fraction in points)
    body.append(f'<polyline points="{rendered}" fill="none" stroke="{GREEN}" stroke-width="3"/>')
    for x, y, value, fraction in points:
        body.extend(
            [
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="{GREEN}"/>',
                f'<text class="small" x="{x:.2f}" y="{y - 11:.2f}" text-anchor="middle">{value:.3f}</text>',
                f'<text class="small" x="{x:.2f}" y="{TOP + PLOT_HEIGHT + 24}" text-anchor="middle">{fraction:.0%}</text>',
            ]
        )
    body.append(
        f'<text class="label" x="{LEFT + PLOT_WIDTH / 2}" y="{HEIGHT - 30}" text-anchor="middle">Related-unit training fraction</text>'
    )
    return _document(title, "\n".join(body))


def _score_distribution(summary: dict[str, object]) -> str:
    title = "E001 post-hoc out-of-fold Random Forest score distributions"
    body = _y_axis("Uncalibrated Random Forest score")

    def to_y(value: float) -> float:
        return TOP + (1 - value) * PLOT_HEIGHT

    classes = [
        ("Unlabelled background", "unlabelled_background", BLUE),
        ("Positive bowl barrow", "positive_bowl_barrow", ORANGE),
    ]
    for index, (label, key, color) in enumerate(classes):
        values = summary["score_distributions"][key]
        x = LEFT + PLOT_WIDTH * (0.32 + 0.36 * index)
        body.extend(
            [
                f'<line x1="{x}" y1="{to_y(values["maximum"]):.2f}" x2="{x}" y2="{to_y(values["minimum"]):.2f}" stroke="{color}" stroke-width="2"/>',
                f'<rect x="{x - 48}" y="{to_y(values["q75"]):.2f}" width="96" height="{to_y(values["q25"]) - to_y(values["q75"]):.2f}" fill="{color}" opacity="0.35" stroke="{color}" stroke-width="2"/>',
                f'<line x1="{x - 48}" y1="{to_y(values["median"]):.2f}" x2="{x + 48}" y2="{to_y(values["median"]):.2f}" stroke="{color}" stroke-width="4"/>',
                f'<circle cx="{x}" cy="{to_y(values["mean"]):.2f}" r="5" fill="{color}"/>',
                f'<text class="label" x="{x}" y="{TOP + PLOT_HEIGHT + 28}" text-anchor="middle">{label}</text>',
            ]
        )
    body.append(
        f'<text class="small" x="{WIDTH / 2}" y="{HEIGHT - 28}" text-anchor="middle">Scores are not calibrated probabilities of archaeology.</text>'
    )
    return _document(title, "\n".join(body))


def main() -> int:
    root = find_project_root()
    summary = json.loads(
        (root / "outputs/robustness/e001_robustness_summary.json").read_text(encoding="utf-8")
    )
    if summary.get("posthoc_not_confirmatory") is not True:
        raise ValueError("robustness figures require post-hoc result labelling")
    figures = {
        "e001_geographic_fold_balanced_accuracy.svg": _bar_figure(
            "E001 post-hoc geographic-fold robustness",
            [
                row["fold"].replace("_", " ").title()
                for row in summary["primary_geographic_cv"]["folds"]
            ],
            [row["balanced_accuracy"] for row in summary["primary_geographic_cv"]["folds"]],
            GREEN,
        ),
        "e001_representation_robustness.svg": _bar_figure(
            "E001 post-hoc representation sensitivity",
            ["Elevation", "Slope", "Hillshade", "Local relief", "All four"],
            [
                summary["representation_summaries"][key]["mean"]
                for key in (
                    "normalized_elevation",
                    "slope",
                    "hillshade",
                    "local_relief",
                    "all_four",
                )
            ],
            BLUE,
        ),
        "e001_seed_robustness.svg": _bar_figure(
            "E001 post-hoc Random Forest seed sensitivity",
            list(summary["seed_summaries"]),
            [item["mean"] for item in summary["seed_summaries"].values()],
            ORANGE,
        ),
        "e001_training_size_learning_curve.svg": _learning_curve(summary),
        "e001_score_distributions.svg": _score_distribution(summary),
    }
    figure_root = root / "outputs/robustness/figures"
    figure_root.mkdir(parents=True, exist_ok=True)
    for name, content in figures.items():
        destination = figure_root / name
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite robustness figure: {destination}")
        destination.write_text(content, encoding="utf-8")
    print(f"Rendered {len(figures)} coordinate-safe robustness SVG figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
