"""Phase 5E-B internal-readiness and anti-overclaiming regression tests."""

from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "docs" / "review"
RQ1 = "RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW"

REQUIRED_REVIEW_FILES = (
    "AI_ASSISTANCE_AND_AUTHORSHIP_DISCLOSURE.md",
    "PHASE_5E_COMPLETION_GATE.md",
    "PHASE_5E_LICENSING_QUESTIONS.md",
    "PHASE_5E_OWNER_DISPOSITION.md",
    "PHASE_5E_REVIEWER_HANDOFF.md",
)

PROTECTED_GIT_OBJECTS = {
    "configs": "abe3659c7ed9d93e8895fbc5fb380e3baaef1762",
    "data/manifests": "791cfc4ffc61c2416cd66c13fe6ff9ec932d4eef",
    "docs/claims-register.md": "f50ef6cc2c2cffa01fe0c4472205f39abd1a2362",
    "docs/decision-log.md": "31d05ce5015f88a605477ed79ca7355952f5f63c",
    "docs/manuscript": "a0f79d64c5076cc48d24cfd7920f4c4978f2fc00",
    "experiments": "7ff387d2f2e6740673bc5fd49b4d9220a502c585",
    "outputs": "582697eaebc4b26aa77b2e6f841c1c187ae80dab",
    "research-log": "ff141d6d28e90300b13f03b6de37425566271d38",
    "website": "afd015db3ba480d2cd26192fb7d18a7f964f0550",
}


def _read(name: str) -> str:
    return (REVIEW / name).read_text(encoding="utf-8")


def test_completion_gate_records_truthful_current_state() -> None:
    gate = _read("PHASE_5E_COMPLETION_GATE.md")
    for token in (
        "INTERNAL_PHASE_5E_READINESS = READY",
        "INDEPENDENT_REVIEW_COMPLETION = PENDING",
        "PHASE_5E_OVERALL_STATUS = NOT COMPLETE",
        "PHASE_5F_AUTHORIZATION = NOT AUTHORIZED",
        RQ1,
    ):
        assert token in gate
    assert not re.search(r"(?m)^INDEPENDENT_REVIEW_COMPLETION = COMPLETE$", gate)
    assert not re.search(r"(?m)^PHASE_5F_AUTHORIZATION = AUTHORIZED$", gate)


def test_review_consolidation_files_exist_and_are_linked() -> None:
    index = _read("README.md")
    handoff = _read("PHASE_5E_REVIEWER_HANDOFF.md")
    for name in REQUIRED_REVIEW_FILES:
        assert (REVIEW / name).is_file()
        assert name in index or name in handoff


def test_ai_disclosure_is_candid_and_not_independent_review() -> None:
    disclosure = _read("AI_ASSISTANCE_AND_AUTHORSHIP_DISCLOSURE.md")
    collapsed = " ".join(disclosure.replace("**", "").split())
    for phrase in (
        "materially generative-AI-assisted",
        "OpenAI Codex",
        "It would be inaccurate to claim that the owner manually wrote every line",
        "AI assistance is not an independent external review",
        "does not support saying that the owner independently hand-authored all software",
        "The Phase 2A.5 record",
        "no complete model/version chronology is claimed",
    ):
        assert phrase in collapsed
    assert "Professor James Conolly" in disclosure
    assert "owner-relayed paraphrase" in disclosure
    assert "not a quotation, endorsement" in disclosure


def test_feedback_and_disposition_do_not_fabricate_review() -> None:
    feedback = _read("FEEDBACK_REGISTER.md")
    disposition = _read("PHASE_5E_OWNER_DISPOSITION.md")
    for source_class in (
        "INFORMAL_EXPERT_ADVICE",
        "EXTERNAL_REVIEW",
        "LEGAL_OR_LICENSING_REVIEW",
        "REVIEWER_PENDING",
        "NO_REVIEW_OBTAINED",
        "AI_INTERNAL_WORK",
    ):
        assert source_class in feedback
    assert "No findings are recorded at this snapshot." in disposition
    collapsed = " ".join(disposition.split()).casefold()
    assert "a blank register is not a pass." in collapsed
    assert "no detailed feedback, approval, or review completion is inferred" in collapsed


def test_review_language_preserves_claim_and_authorization_boundaries() -> None:
    paths = [ROOT / "README.md", ROOT / "docs" / "CURRENT_STATUS.md"] + [
        REVIEW / name
        for name in REQUIRED_REVIEW_FILES
        + (
            "FEEDBACK_REGISTER.md",
            "PHASE_5E_EXTERNAL_REVIEW_CHECKLIST.md",
            "PHASE_5E_REVIEW_PACKAGE.md",
            "README.md",
            "REVIEWER_GUIDE.md",
        )
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert RQ1 in text
    assert "Phase 5E" in text and "NOT COMPLETED" in text
    assert "Phase 5F" in text and "NOT AUTHORIZED" in text
    assert re.search(r"not archaeological probabilit(?:y|ies)", text.casefold())
    assert "does not claim archaeological discovery" in text.casefold()
    for false_claim in (
        "Professor James Conolly endorsed ArchaeoAI",
        "independent reviewers approved ArchaeoAI",
        "ArchaeoAI is peer reviewed",
        "ArchaeoAI is a peer-reviewed publication",
        "AI assistance constitutes independent review",
        "candidate locations are published",
        "safe to build according to ArchaeoAI",
    ):
        assert false_claim.casefold() not in text.casefold()


def test_licensing_status_remains_unresolved() -> None:
    licensing = (ROOT / "docs" / "licensing-and-attribution.md").read_text(encoding="utf-8")
    questions = _read("PHASE_5E_LICENSING_QUESTIONS.md")
    assert "does **not** currently have a repository-wide licence" in licensing
    assert "FORMAL public software release remains blocked".casefold() in questions.casefold()
    assert not (ROOT / "LICENSE").exists()
    assert not (ROOT / "LICENSE.md").exists()


def test_protected_scientific_and_frozen_git_objects_are_unchanged() -> None:
    for path, expected in PROTECTED_GIT_OBJECTS.items():
        actual = subprocess.run(
            ["git", "rev-parse", f"HEAD:{path}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert actual == expected, path

    entries = subprocess.run(
        ["git", "ls-tree", "-r", "HEAD", "--", "docs"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    e001_entries = "\n".join(line for line in entries if "\tdocs/e001-" in line) + "\n"
    assert hashlib.sha256(e001_entries.encode()).hexdigest() == (
        "ac18e43ac65583062ca6cf5d2243c280baaf5acc7acafd89f9b53503791cfb56"
    )


def test_no_sensitive_artifact_type_is_tracked() -> None:
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.splitlines()
    forbidden = (
        ".tif",
        ".tiff",
        ".npz",
        ".pkl",
        ".pickle",
        ".joblib",
        ".onnx",
        ".pt",
        ".pth",
        ".ckpt",
        ".geojson",
        ".gpkg",
        ".shp",
    )
    assert not [path for path in tracked if path.casefold().endswith(forbidden)]
