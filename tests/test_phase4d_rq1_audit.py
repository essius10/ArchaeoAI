import re
from pathlib import Path

from archaeoai.external_error_analysis import validate_external_error_analysis
from archaeoai.external_evaluation import validate_external_evaluation_result

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "docs/review/PHASE_4D_RQ1_AUDIT.md"
FEEDBACK = ROOT / "docs/review/FEEDBACK_REGISTER.md"
RQ = ROOT / "docs/research-questions.md"

RQ1 = (
    "For one documented English earthwork class, how do terrain representations and random "
    "versus geographic splits change apparent baseline performance?"
)
STATUS = "RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW"


def test_phase4d_uses_the_tracked_rq1_without_redefinition() -> None:
    rq_text = RQ.read_text(encoding="utf-8")
    audit = AUDIT.read_text(encoding="utf-8")
    assert RQ1 in rq_text
    assert RQ1 in " ".join(audit.replace("> ", "").split())
    assert STATUS in audit


def test_phase4d_preserves_frozen_external_result_and_spent_test() -> None:
    result = validate_external_evaluation_result(
        ROOT / "outputs/external_validation/e001_phase3c_external_evaluation.json"
    )
    phase4a = validate_external_error_analysis(
        ROOT / "outputs/external_validation/e001_phase4a_error_analysis.json"
    )
    audit = AUDIT.read_text(encoding="utf-8")
    assert result["external_test_spent"] is True
    assert result["primary"]["metrics"]["balanced_accuracy"] == 0.8416666666666667
    assert result["primary"]["confidence_interval"]["lower_95"] == 0.775
    assert result["primary"]["confidence_interval"]["upper_95"] == 0.9
    assert phase4a["analysis_label"] == "POST-HOC / EXPLORATORY"
    assert "84.2%, 95% matched-pair bootstrap CI 77.5–90.0%, n=120" in audit
    assert "The external test is spent" in audit


def test_phase4d_answer_reports_split_result_without_overstatement() -> None:
    audit = AUDIT.read_text(encoding="utf-8")
    assert "Random final balanced accuracy 0.822581" in audit
    assert "geographic final 0.870968" in audit
    assert "random-minus-geographic −0.048387" in audit
    assert "the random split did not overstate performance" in audit
    assert "does not establish England-wide performance" in audit
    assert "no new evidence or discovery is claimed" in audit.lower()


def test_phase4d_separates_evidence_statuses() -> None:
    audit = AUDIT.read_text(encoding="utf-8")
    guide = (ROOT / "docs/review/REVIEWER_GUIDE.md").read_text(encoding="utf-8")
    for phrase in (
        "AI/model output",
        "Hypothesis or candidate interpretation",
        "Human-vetted observation",
        "Archaeologist-validated interpretation",
        "Confirmed archaeological evidence",
    ):
        assert phrase.lower() in audit.lower()
        assert phrase.lower() in guide.lower()


def test_feedback_register_does_not_invent_or_overstate_review() -> None:
    feedback = FEEDBACK.read_text(encoding="utf-8")
    assert "name not supplied or authorized" in feedback
    assert "Careful paraphrase" in feedback
    assert "not a verified quotation" in feedback
    assert "no endorsement or completed review is claimed" in feedback
    assert "Accepted" in feedback


def test_phase4d_blockers_have_explicit_owners() -> None:
    audit = AUDIT.read_text(encoding="utf-8")
    required_statuses = {
        "Advanced but still open",
        "Blocked by external human work",
        "Blocked by private data",
        "Requires owner decision",
    }
    assert all(status.lower() in audit.lower() for status in required_statuses)


def test_phase4d_public_documents_are_coordinate_safe() -> None:
    paths = (
        AUDIT,
        FEEDBACK,
        ROOT / "research-log/2026-09-05-phase-4d-rq1-audit.md",
    )
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert not re.search(
        r'(?i)["\']?(?:easting|northing|latitude|longitude|heritage_id|sample_id|pair_id)'
        r'["\']?\s*[:=]\s*[-+]?\d',
        text,
    )
    assert not re.search(r"(?i)[a-z]:\\users\\|data/private|\.npz|\.tiff?|\.pt(?:h)?", text)
