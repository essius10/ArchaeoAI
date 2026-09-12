"""Phase 5E-C attributable external-review workflow tests."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from archaeoai.review_evidence import (
    DOMAIN_PREFIX,
    OWNER_DECISION_SCHEMA,
    POLICY_SCHEMA,
    REVIEW_SCHEMA,
    RQ1_STATUS,
    ReviewEvidenceError,
    build_review_bundle,
    evaluate_review_gate,
    expected_review_bundle_manifest_sha256,
    review_record_sha256,
    validate_owner_decision,
    validate_review_record,
    verify_review_bundle,
)

ROOT = Path(__file__).resolve().parents[1]


def _review(domain: str = "security", *, finding: bool = False) -> dict[str, object]:
    prefix = DOMAIN_PREFIX[domain]
    review_id = f"P5E-{prefix}-R001"
    findings: list[dict[str, object]] = []
    if finding:
        findings.append(
            {
                "finding_id": f"P5E-{prefix}-F001",
                "originating_review_id": review_id,
                "review_domain": domain,
                "severity": "medium",
                "title": "Document a bounded remediation",
                "description": "The reviewed workflow needs one bounded documentation correction.",
                "evidence_reference": "docs/review/PHASE_5E_REVIEW_PACKAGE.md#track",
                "affected_components": ["docs/review/PHASE_5E_REVIEW_PACKAGE.md"],
                "impact_flags": {
                    "scientific": False,
                    "privacy": False,
                    "security": domain == "security",
                    "licensing": domain == "licensing",
                },
                "recommended_action": "Clarify the bounded workflow before approval.",
            }
        )
    return {
        "schema_version": REVIEW_SCHEMA,
        "record_status": "COMPLETE",
        "review_id": review_id,
        "review_domain": domain,
        "reviewed_repository_commit": "a" * 40,
        "review_bundle_manifest_sha256": "b" * 64,
        "review_date": "2026-09-12",
        "reviewer": {
            "public_attribution": f"Independent {domain} reviewer 01",
            "affiliation": "",
            "expertise": f"Professional expertise relevant to {domain} review.",
            "independence_declaration": "I independently assessed the stated repository scope.",
            "conflict_of_interest_declaration": "I declare no conflict affecting this assessment.",
        },
        "scope_reviewed": ["Public repository evidence and the stated review track."],
        "methodology": "Manual inspection plus the documented deterministic checks.",
        "tools_used": ["Git and Python test tooling"],
        "ai_assistance": "No generative AI was used for this synthetic test record.",
        "limitations": "This synthetic record exists only inside an automated test.",
        "findings": findings,
        "overall_conclusion": "PASS_WITH_CONDITIONS" if finding else "PASS",
        "attestation": "I attest that this record represents the stated review scope and limits.",
        "evidence_references": ["docs/review/PHASE_5E_EXTERNAL_REVIEW_CHECKLIST.md"],
    }


def _policy(bundle_files: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "schema_version": POLICY_SCHEMA,
        "repository": "essius10/ArchaeoAI",
        "required_domains": [
            "security",
            "privacy",
            "archaeological_scientific",
            "licensing",
        ],
        "evidence_directory": "docs/review/evidence",
        "owner_decision_path": "docs/review/evidence/phase5e-owner-decision.json",
        "bundle": {
            "format_version": "archaeoai-phase5e-review-bundle-v1",
            "output_root": "outputs/review",
            "prohibited_prefixes": [".git", "data/private"],
            "prohibited_suffixes": [".pkl", ".tif"],
            "files": bundle_files or [{"path": "README.md", "tracks": ["all"]}],
        },
    }


def _write_test_repository(tmp_path: Path, policy: dict[str, object]) -> str:
    (tmp_path / "docs/review").mkdir(parents=True)
    (tmp_path / "README.md").write_text("# Public-safe review fixture\n", encoding="utf-8")
    (tmp_path / "docs/review/phase5e-review-policy.json").write_text(
        json.dumps(policy), encoding="utf-8"
    )
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "ArchaeoAI test"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=tmp_path, check=True)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_valid_review_metadata_and_finding_structure() -> None:
    record = validate_review_record(_review(finding=True))
    assert record["review_domain"] == "security"
    assert len(record["findings"]) == 1
    assert len(review_record_sha256(record)) == 64


@pytest.mark.parametrize(
    "mutation",
    [
        lambda record: record["reviewer"].update(public_attribution=""),
        lambda record: record.update(reviewed_repository_commit="short"),
        lambda record: record["reviewer"].update(independence_declaration="TODO"),
        lambda record: record["reviewer"].update(expertise="TBD"),
        lambda record: record.update(attestation=""),
    ],
)
def test_required_attribution_version_and_declarations_fail_closed(mutation: object) -> None:
    record = _review()
    mutation(record)  # type: ignore[operator]
    with pytest.raises(ReviewEvidenceError):
        validate_review_record(record)


def test_blank_template_and_placeholder_values_do_not_count() -> None:
    template = json.loads(
        (ROOT / "docs/review/templates/phase5e_review.template.json").read_text(encoding="utf-8")
    )
    with pytest.raises(ReviewEvidenceError, match="templates do not count"):
        validate_review_record(template)
    record = _review()
    record["methodology"] = "REPLACE_WITH_REVIEW_METHOD"
    with pytest.raises(ReviewEvidenceError, match="placeholder"):
        validate_review_record(record)


def test_invalid_domain_severity_and_finding_reference_are_rejected() -> None:
    wrong_domain = _review()
    wrong_domain["review_domain"] = "statistics"
    with pytest.raises(ReviewEvidenceError, match="domain"):
        validate_review_record(wrong_domain)

    wrong_severity = _review(finding=True)
    wrong_severity["findings"][0]["severity"] = "critical"  # type: ignore[index]
    with pytest.raises(ReviewEvidenceError, match="severity"):
        validate_review_record(wrong_severity)

    unsafe_reference = _review(finding=True)
    unsafe_reference["findings"][0]["evidence_reference"] = "C:\\private\\finding.txt"  # type: ignore[index]
    with pytest.raises(ReviewEvidenceError, match="path"):
        validate_review_record(unsafe_reference)


def test_private_contact_or_secret_fields_are_rejected() -> None:
    record = _review()
    record["reviewer"]["email"] = "not-for-the-repository@example.invalid"  # type: ignore[index]
    with pytest.raises(ReviewEvidenceError, match="private field"):
        validate_review_record(record)


def test_current_gate_is_fail_closed_and_lists_every_missing_domain() -> None:
    status = evaluate_review_gate(ROOT)
    assert status["phase5e_status"] == "NOT COMPLETE"
    assert status["phase5f_authorization"] == "NOT AUTHORIZED"
    assert status["rq1_status"] == RQ1_STATUS
    assert status["independent_review_completion"] == "PENDING"
    assert status["owner_decision"] == "PENDING"
    assert {
        domain
        for domain, value in status["review_domains"].items()
        if value["status"] == "NOT_RECEIVED"
    } == {"security", "privacy", "archaeological_scientific", "licensing"}
    assert all("missing/incomplete" in status["blockers"][index] for index in range(4))


def test_owner_decision_binds_distinct_hashed_reviews_and_every_finding() -> None:
    reviews = {
        record["review_id"]: record
        for record in [
            validate_review_record(_review("security", finding=True)),
            validate_review_record(_review("privacy")),
            validate_review_record(_review("archaeological_scientific")),
            validate_review_record(_review("licensing")),
        ]
    }
    accepted = {
        domain: [
            {
                "review_id": record["review_id"],
                "record_sha256": review_record_sha256(record),
            }
        ]
        for domain in (
            "security",
            "privacy",
            "archaeological_scientific",
            "licensing",
        )
        for record in [
            next(value for value in reviews.values() if value["review_domain"] == domain)
        ]
    }
    decision = {
        "schema_version": OWNER_DECISION_SCHEMA,
        "decision_status": "COMPLETE",
        "decision_id": "P5E-OWNER-001",
        "decision_date": "2026-09-12",
        "owner_public_attribution": "ArchaeoAI project owner",
        "accepted_reviews": accepted,
        "finding_dispositions": [
            {
                "finding_id": "P5E-SEC-F001",
                "originating_review_id": "P5E-SEC-R001",
                "owner_disposition": "ACCEPT",
                "disposition_rationale": "The bounded residual risk is explicitly accepted.",
                "code_or_doc_change": "",
                "evidence_references": [],
                "residual_limitation": "The documented limitation remains controlling.",
                "resolution_status": "ACCEPTED_RISK",
                "resolved_by_commit": "",
                "final_verification": "Owner verified the recorded residual limitation.",
            }
        ],
        "phase5e_decision": "COMPLETE",
        "phase5f_authorization": "NOT_AUTHORIZED",
        "residual_limitations": ["All scientific limitations remain controlling."],
        "attestation": "I explicitly close Phase 5E against these exact records and limitations.",
    }
    assert validate_owner_decision(decision, reviews)["phase5e_decision"] == "COMPLETE"

    missing_finding = copy.deepcopy(decision)
    missing_finding["finding_dispositions"] = []
    with pytest.raises(ReviewEvidenceError, match="every accepted finding"):
        validate_owner_decision(missing_finding, reviews)

    reused = copy.deepcopy(decision)
    reused["accepted_reviews"]["privacy"] = copy.deepcopy(accepted["security"])
    with pytest.raises(ReviewEvidenceError, match="multiple review domains|mismatched"):
        validate_owner_decision(reused, reviews)

    extra_reviews = dict(reviews)
    extra_payload = _review("security")
    extra_payload["review_id"] = "P5E-SEC-R002"
    extra = validate_review_record(extra_payload)
    extra_reviews[extra["review_id"]] = extra
    with pytest.raises(ReviewEvidenceError, match="every submitted review"):
        validate_owner_decision(decision, extra_reviews)


def test_gate_accepts_only_four_bound_reviews_plus_explicit_owner_decision(tmp_path: Path) -> None:
    commit = _write_test_repository(tmp_path, _policy())
    bundle_digest = expected_review_bundle_manifest_sha256(tmp_path, revision=commit)
    evidence = tmp_path / "docs/review/evidence"
    evidence.mkdir()
    reviews: dict[str, dict[str, object]] = {}
    for domain in ("security", "privacy", "archaeological_scientific", "licensing"):
        record = _review(domain)
        record["reviewed_repository_commit"] = commit
        record["review_bundle_manifest_sha256"] = bundle_digest
        validated = validate_review_record(record)
        reviews[domain] = validated
        (evidence / f"phase5e-{domain}-review.json").write_text(
            json.dumps(validated), encoding="utf-8"
        )

    received = evaluate_review_gate(tmp_path)
    assert received["phase5e_status"] == "NOT COMPLETE"
    assert {value["status"] for value in received["review_domains"].values()} == {"RECEIVED"}

    decision = {
        "schema_version": OWNER_DECISION_SCHEMA,
        "decision_status": "COMPLETE",
        "decision_id": "P5E-OWNER-001",
        "decision_date": "2026-09-12",
        "owner_public_attribution": "ArchaeoAI project owner",
        "accepted_reviews": {
            domain: [
                {
                    "review_id": record["review_id"],
                    "record_sha256": review_record_sha256(record),
                }
            ]
            for domain, record in reviews.items()
        },
        "finding_dispositions": [],
        "phase5e_decision": "COMPLETE",
        "phase5f_authorization": "NOT_AUTHORIZED",
        "residual_limitations": ["The bounded scientific limitations remain controlling."],
        "attestation": "I explicitly close Phase 5E against these exact records and limitations.",
    }
    (evidence / "phase5e-owner-decision.json").write_text(json.dumps(decision), encoding="utf-8")
    complete = evaluate_review_gate(tmp_path)
    assert complete["phase5e_status"] == "COMPLETE"
    assert complete["independent_review_completion"] == "COMPLETE"
    assert complete["phase5f_authorization"] == "NOT AUTHORIZED"
    assert {value["status"] for value in complete["review_domains"].values()} == {"ACCEPTED"}


def test_bundle_manifest_is_deterministic_and_hashes_git_blobs(tmp_path: Path) -> None:
    commit = _write_test_repository(tmp_path, _policy())
    first = build_review_bundle(tmp_path, tmp_path / "outputs/review/first", revision=commit)
    second = build_review_bundle(tmp_path, tmp_path / "outputs/review/second", revision=commit)
    assert first == second
    assert first["reviewed_repository_commit"] == commit
    assert (tmp_path / "outputs/review/first/manifest.json").read_bytes() == (
        tmp_path / "outputs/review/second/manifest.json"
    ).read_bytes()
    verified = verify_review_bundle(tmp_path / "outputs/review/first")
    expected = hashlib.sha256(b"# Public-safe review fixture\n").hexdigest()
    assert verified["files"][0]["sha256"] == expected


def test_bundle_verification_rejects_tampering_and_unmanifested_files(tmp_path: Path) -> None:
    commit = _write_test_repository(tmp_path, _policy())
    destination = tmp_path / "outputs/review/tampered"
    build_review_bundle(tmp_path, destination, revision=commit)
    (destination / "files/README.md").write_text("changed\n", encoding="utf-8")
    with pytest.raises(ReviewEvidenceError, match="integrity mismatch"):
        verify_review_bundle(destination)

    second = tmp_path / "outputs/review/extra"
    build_review_bundle(tmp_path, second, revision=commit)
    (second / "extra.txt").write_text("unexpected\n", encoding="utf-8")
    with pytest.raises(ReviewEvidenceError, match="unmanifested"):
        verify_review_bundle(second)


def test_bundle_refuses_sensitive_paths_and_output_escape(tmp_path: Path) -> None:
    private = tmp_path / "data/private"
    private.mkdir(parents=True)
    (private / "secret.md").write_text("private\n", encoding="utf-8")
    policy = _policy([{"path": "data/private/secret.md", "tracks": ["security"]}])
    commit = _write_test_repository(tmp_path, policy)
    with pytest.raises(ReviewEvidenceError, match="prohibited path"):
        build_review_bundle(tmp_path, tmp_path / "outputs/review/private", revision=commit)
    with pytest.raises(ReviewEvidenceError, match="configured output root"):
        build_review_bundle(tmp_path, tmp_path / "escaped", revision=commit)


def test_bundle_refuses_git_symlink_entries_without_following_them(tmp_path: Path) -> None:
    _write_test_repository(tmp_path, _policy([{"path": "link.md", "tracks": ["security"]}]))
    blob = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=tmp_path,
        input="README.md\n",
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "update-index", "--add", "--cacheinfo", "120000", blob, "link.md"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(["git", "commit", "-qm", "add symlink entry"], cwd=tmp_path, check=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    with pytest.raises(ReviewEvidenceError, match="regular tracked file"):
        build_review_bundle(tmp_path, tmp_path / "outputs/review/symlink", revision=commit)


def test_review_bundle_output_is_ignored_and_protected_science_unchanged() -> None:
    ignored = subprocess.run(
        ["git", "check-ignore", "outputs/review/example/manifest.json"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0
    protected = {
        "configs": "abe3659c7ed9d93e8895fbc5fb380e3baaef1762",
        "data/manifests": "791cfc4ffc61c2416cd66c13fe6ff9ec932d4eef",
        "docs/manuscript": "a0f79d64c5076cc48d24cfd7920f4c4978f2fc00",
        "outputs": "582697eaebc4b26aa77b2e6f841c1c187ae80dab",
    }
    for path, expected in protected.items():
        actual = subprocess.run(
            ["git", "rev-parse", f"HEAD:{path}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert actual == expected
