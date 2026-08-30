import copy
import json
import re
from pathlib import Path

import pytest

from archaeoai.manuscript import (
    EXPECTED_FIGURE_PATHS,
    EXPECTED_PHASE3C_RESULT_SHA256,
    MANUSCRIPT_PATH,
    canonical_sha256,
    manuscript_figure_paths,
    validate_manuscript_evidence,
)

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_PATH = ROOT / "outputs/manuscript/e001_manuscript_evidence.json"
MANUSCRIPT = ROOT / MANUSCRIPT_PATH


def test_manuscript_evidence_validates() -> None:
    payload = validate_manuscript_evidence(EVIDENCE_PATH, root=ROOT)
    assert payload["frozen_evidence"]["phase3c_result_sha256"] == (EXPECTED_PHASE3C_RESULT_SHA256)
    assert 4_000 <= payload["manuscript"]["word_count"] <= 7_000


def test_manuscript_metrics_match_frozen_phase3c_result() -> None:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    frozen = json.loads(
        (ROOT / "outputs/external_validation/e001_phase3c_external_evaluation.json").read_text(
            encoding="utf-8"
        )
    )
    metrics = frozen["primary"]["metrics"]
    assert metrics["balanced_accuracy"] == 0.8416666666666667
    assert frozen["primary"]["confidence_interval"]["lower_95"] == 0.775
    assert frozen["primary"]["confidence_interval"]["upper_95"] == 0.9
    assert metrics["confusion_matrix"] == {"tn": 52, "fp": 8, "fn": 11, "tp": 49}
    for required in ("84.2%", "77.5–90.0%", "120 observations", "TN = 52", "FP = 8"):
        assert required in text
    for required in ("FN = 11", "TP = 49", "0.927778", "0.942058"):
        assert required in text


def test_scientific_boundaries_are_explicit() -> None:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    assert "external test is spent" in text.lower()
    assert "POST-HOC / EXPLORATORY" in text
    assert "not archaeological-discovery accuracy" in text.lower()
    assert "no field verification" in text.lower()
    assert "remains unreviewed" in text.lower()


def test_manuscript_uses_only_frozen_coordinate_safe_figures() -> None:
    text = MANUSCRIPT.read_text(encoding="utf-8")
    assert manuscript_figure_paths(text) == EXPECTED_FIGURE_PATHS
    for path in EXPECTED_FIGURE_PATHS:
        svg = (ROOT / path).read_text(encoding="utf-8")
        assert not re.search(
            r'(?i)["\'](?:easting|northing|latitude|longitude|sample_id|pair_id)["\']\s*:',
            svg,
        )


def test_no_prohibited_affirmative_claims() -> None:
    paths = [
        MANUSCRIPT,
        ROOT / "docs/reproducibility.md",
        ROOT / "docs/release-checklist.md",
        ROOT / "docs/release-plan.md",
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths).lower()
    prohibited = (
        "ai discovered archaeological sites",
        "84% archaeological discovery accuracy",
        "84% accurate across england",
        "rf score is probability of archaeology",
        "backgrounds are archaeology-free",
        "professor endorsement",
        "university endorsement",
    )
    assert not any(phrase in text for phrase in prohibited)


def test_freeze_script_cannot_train_or_score() -> None:
    source = (ROOT / "scripts/freeze_e001_manuscript_evidence.py").read_text(encoding="utf-8")
    prohibited = (".fit(", ".predict(", ".predict_proba(", "RandomForestClassifier", "torch")
    assert not any(token in source for token in prohibited)


def test_evidence_mutation_is_detected(tmp_path: Path) -> None:
    payload = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    mutated = copy.deepcopy(payload)
    mutated["scientific_boundary"]["phase3c_external_test_spent"] = False
    mutated["evidence_manifest_sha256"] = canonical_sha256(mutated, omit="evidence_manifest_sha256")
    path = tmp_path / "mutated.json"
    path.write_text(json.dumps(mutated), encoding="utf-8")
    with pytest.raises(ValueError, match="evidence SHA-256"):
        validate_manuscript_evidence(path, root=ROOT)
