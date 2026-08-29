from __future__ import annotations

import hashlib
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "website"


class _SiteParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: list[str] = []
        self.local_assets: list[str] = []
        self.remote_scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if element_id := attributes.get("id"):
            self.ids.append(element_id)
        source = attributes.get("src")
        if source:
            if tag == "script" and source.startswith(("http://", "https://", "//")):
                self.remote_scripts.append(source)
            elif not source.startswith(("http://", "https://", "//", "data:")):
                self.local_assets.append(source)
        href = attributes.get("href")
        if tag == "link" and href and not href.startswith(("http://", "https://", "//")):
            self.local_assets.append(href)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_public_demo_has_complete_coordinate_safe_narrative() -> None:
    html = (SITE / "index.html").read_text(encoding="utf-8")
    required_claims = (
        "87.1",
        "82.3%",
        "70.1%",
        "522",
        "261",
        "5,929",
        "No human morphology review has been completed",
        "No heritage cross-check has occurred",
        "Predictions are not discoveries",
    )
    assert all(claim in html for claim in required_claims)
    assert "discovered archaeological" not in html.casefold()


def test_public_demo_has_no_coordinate_or_candidate_level_payload() -> None:
    tracked_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in SITE.rglob("*")
        if path.is_file()
        and path.suffix.casefold() in {".html", ".css", ".js", ".json", ".xml", ".txt", ".md"}
    )
    forbidden_fields = re.compile(
        r'(?i)["\'](?:easting|northing|latitude|longitude|geometry|polygon|bbox|bounds|private_token|sample_id)["\']\s*:'
    )
    assert forbidden_fields.search(tracked_text) is None
    assert re.search(r"BNG_100KM_E\d+_N\d+", tracked_text) is None
    assert not any(
        path.suffix.casefold()
        in {
            ".tif",
            ".tiff",
            ".las",
            ".laz",
            ".gpkg",
            ".shp",
            ".npy",
            ".npz",
            ".pt",
            ".pth",
            ".ckpt",
            ".geojson",
        }
        for path in SITE.rglob("*")
        if path.is_file()
    )


def test_public_demo_is_self_contained_and_accessible() -> None:
    parser = _SiteParser()
    parser.feed((SITE / "index.html").read_text(encoding="utf-8"))
    assert len(parser.ids) == len(set(parser.ids))
    assert parser.remote_scripts == []
    assert all((SITE / asset).is_file() for asset in parser.local_assets)
    assert {"main", "question", "results", "responsibility", "status"}.issubset(parser.ids)


def test_public_demo_aggregate_figures_match_frozen_sources() -> None:
    copies = {
        "assets/balanced-accuracy-comparison.svg": (
            "outputs/modelling/figures/e001_balanced_accuracy_comparison.svg"
        ),
        "assets/cnn-vs-rf-by-fold.svg": (
            "outputs/deep_learning/figures/e001_cnn_vs_rf_by_fold.svg"
        ),
        "assets/private-inference-score-distribution.svg": (
            "outputs/inference/figures/e001_phase2f_b_score_distribution.svg"
        ),
    }
    assert all(_sha256(SITE / copy) == _sha256(ROOT / source) for copy, source in copies.items())
