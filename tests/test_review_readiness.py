import re
from pathlib import Path

from archaeoai.external_error_analysis import validate_external_error_analysis
from archaeoai.external_evaluation import validate_external_evaluation_result
from archaeoai.manuscript import EXPECTED_MANUSCRIPT_EVIDENCE_SHA256, validate_manuscript_evidence

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs/review"
MANUSCRIPT = ROOT / "docs/manuscript/archaeoai-e001-manuscript.md"
CITATION_AUDIT = ROOT / "docs/citation-audit.md"


def test_review_readiness_preserves_frozen_scientific_boundaries() -> None:
    phase3c = validate_external_evaluation_result(
        ROOT / "outputs/external_validation/e001_phase3c_external_evaluation.json"
    )
    phase4a = validate_external_error_analysis(
        ROOT / "outputs/external_validation/e001_phase4a_error_analysis.json"
    )
    evidence = validate_manuscript_evidence(
        ROOT / "outputs/manuscript/e001_manuscript_evidence.json", root=ROOT
    )
    assert phase3c["external_test_spent"] is True
    assert phase3c["primary"]["metrics"]["balanced_accuracy"] == 0.8416666666666667
    assert phase4a["analysis_label"] == "POST-HOC / EXPLORATORY"
    assert evidence["evidence_manifest_sha256"] == EXPECTED_MANUSCRIPT_EVIDENCE_SHA256


def test_citation_audit_and_manuscript_use_verified_references_consistently() -> None:
    manuscript = MANUSCRIPT.read_text(encoding="utf-8")
    audit = CITATION_AUDIT.read_text(encoding="utf-8")
    dois = {
        "10.1109/ICPR.2010.764",
        "10.1016/j.jas.2024.106022",
        "10.3758/s13428-019-01252-y",
        "10.5334/jcaa.64",
        "10.1111/ecog.02881",
        "10.5334/jcaa.32",
        "10.1002/arp.1931",
    }
    for doi in dois:
        assert doi in manuscript
        assert doi in audit
    assert "every manuscript reference" in audit
    assert "CITATION_REVIEW_REQUIRED" in audit


def test_reviewer_packet_has_required_disciplines_and_questions() -> None:
    guide = (REVIEW / "REVIEWER_GUIDE.md").read_text(encoding="utf-8")
    checklist = (REVIEW / "REVIEW_CHECKLIST.md").read_text(encoding="utf-8")
    assert len(re.findall(r"^\d+\. ", guide, flags=re.MULTILINE)) == 10
    for heading in (
        "## Archaeology",
        "## Remote sensing and GIS",
        "## Machine learning",
        "## Statistics",
        "## Privacy and responsible archaeology",
        "## Reproducibility",
        "## Citations and licensing",
    ):
        assert heading in checklist


def test_reviewer_packet_is_coordinate_safe_and_claim_bounded() -> None:
    public_text = "\n".join(path.read_text(encoding="utf-8") for path in REVIEW.glob("*.md"))
    assert "84.2% balanced accuracy" in public_text
    assert "77.5–90.0%" in public_text
    assert "n = 120" in public_text
    assert "five pre-specified" in public_text
    assert not re.search(
        r'(?i)["\']?(?:easting|northing|latitude|longitude|heritage_id|sample_id|pair_id)'
        r'["\']?\s*[:=]\s*[-+]?\d',
        public_text,
    )
    assert re.search(
        r"does not imply that any institution or\s+academic has endorsed, supervised, or agreed",
        public_text.lower(),
    )
    prohibited = (
        "this peer-reviewed manuscript",
        "endorsed by a university",
        "84% archaeological discovery accuracy",
        "backgrounds are archaeology-free",
    )
    assert not any(phrase in public_text.lower() for phrase in prohibited)


def test_readiness_and_reproduction_classifications_are_exact() -> None:
    readiness = (REVIEW / "READINESS_AUDIT.md").read_text(encoding="utf-8")
    reproduction = (REVIEW / "CLEAN_ENVIRONMENT_REPRODUCTION.md").read_text(encoding="utf-8")
    assert "**READY_FOR_EXTERNAL_REVIEW**" in readiness
    assert "REVIEW_BLOCKED" not in readiness
    assert (
        "**Classification: PARTIALLY REPRODUCIBLE — PRIVATE DATA REQUIRED FOR SPECIFIC STEPS**"
        in reproduction
    )


def test_licensing_ambiguity_remains_an_explicit_release_blocker() -> None:
    text = (ROOT / "docs/licensing-and-attribution.md").read_text(encoding="utf-8")
    assert "does **not** currently have a repository-wide licence" in text
    assert "## Release blockers" in text
    assert not (ROOT / "LICENSE").exists()
    assert not (ROOT / "LICENSE.md").exists()


def test_python_source_has_cross_platform_ruff_line_endings() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "*.py text eol=lf" in attributes.splitlines()
