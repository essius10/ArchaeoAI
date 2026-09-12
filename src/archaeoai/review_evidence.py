"""Fail-closed Phase 5E external-review evidence and bundle support."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from collections.abc import Mapping
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlsplit

REVIEW_SCHEMA = "archaeoai-phase5e-review-v1"
OWNER_DECISION_SCHEMA = "archaeoai-phase5e-owner-decision-v1"
POLICY_SCHEMA = "archaeoai-phase5e-review-policy-v1"
GATE_SCHEMA = "archaeoai-phase5e-gate-status-v1"
RQ1_STATUS = "RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW"

REQUIRED_DOMAINS = (
    "security",
    "privacy",
    "archaeological_scientific",
    "licensing",
)
DOMAIN_PREFIX = {
    "security": "SEC",
    "privacy": "PRIV",
    "archaeological_scientific": "SCI",
    "licensing": "LIC",
}
SEVERITIES = frozenset({"blocker", "high", "medium", "low", "informational"})
CONCLUSIONS = frozenset({"PASS", "PASS_WITH_CONDITIONS", "CHANGES_REQUIRED", "NO_GO"})
DISPOSITIONS = frozenset({"ACCEPT", "REMEDIATE", "DEFER", "REJECT_WITH_RATIONALE"})
RESOLUTION_STATES = frozenset({"ACCEPTED_RISK", "RESOLVED", "DEFERRED", "REJECTED_WITH_RATIONALE"})

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
_REVIEW_ID = re.compile(r"^P5E-(SEC|PRIV|SCI|LIC)-R[0-9]{3}$")
_FINDING_ID = re.compile(r"^P5E-(SEC|PRIV|SCI|LIC)-F[0-9]{3}$")
_PLACEHOLDER = re.compile(
    r"(?:^|\b)(?:todo|tbd|tbc|fixme|changeme|placeholder|your name|reviewer name|"
    r"example reviewer|fill (?:this|me) in|insert here|replace[_ -]with)(?:\b|$)",
    re.IGNORECASE,
)
_SECRET_MARKERS = (
    b"-----BEGIN " + b"PRIVATE KEY-----",
    b"-----BEGIN OPENSSH " + b"PRIVATE KEY-----",
    b"github" + b"_pat_",
    b"gh" + b"p_",
)
_HARD_PROHIBITED_PREFIXES = frozenset(
    {
        ".git",
        ".venv",
        ".aws",
        ".gcloud",
        "secrets",
        "data/private",
        "data/raw",
        "data/interim",
        "data/processed",
        "outputs/review",
        "outputs/deep_learning/checkpoints",
        "outputs/deep_learning/training_runs",
    }
)
_HARD_PROHIBITED_SUFFIXES = frozenset(
    {
        ".env",
        ".tif",
        ".tiff",
        ".las",
        ".laz",
        ".gpkg",
        ".shp",
        ".npy",
        ".npz",
        ".pkl",
        ".pickle",
        ".joblib",
        ".onnx",
        ".pt",
        ".pth",
        ".ckpt",
        ".pem",
        ".p12",
        ".pfx",
    }
)
_FORBIDDEN_REVIEW_KEYS = frozenset(
    {
        "address",
        "email",
        "phone",
        "telephone",
        "credential",
        "credentials",
        "password",
        "secret",
        "token",
        "coordinates",
        "bounds",
        "transform",
        "easting",
        "northing",
        "latitude",
        "longitude",
        "geometry",
        "ngr",
        "sample_id",
        "pair_id",
        "heritage_id",
        "terrain_path",
        "model_path",
        "private_path",
    }
)


class ReviewEvidenceError(ValueError):
    """Raised when review evidence, policy, or bundle content is unsafe or invalid."""


def canonical_json_bytes(payload: Any) -> bytes:
    """Return the stable JSON representation used for evidence hashes."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def sha256_bytes(content: bytes) -> str:
    """Return a lowercase SHA-256 digest."""
    return hashlib.sha256(content).hexdigest()


def review_record_sha256(record: Mapping[str, Any]) -> str:
    """Hash a validated review record without asserting reviewer identity."""
    return sha256_bytes(canonical_json_bytes(record))


def _mapping(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReviewEvidenceError(f"{field} must be an object")
    return value


def _list(value: Any, field: str, *, allow_empty: bool = False) -> list[Any]:
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "a list" if allow_empty else "a non-empty list"
        raise ReviewEvidenceError(f"{field} must be {qualifier}")
    return value


def _text(value: Any, field: str, *, min_length: int = 3) -> str:
    if not isinstance(value, str):
        raise ReviewEvidenceError(f"{field} must be text")
    cleaned = value.strip()
    if len(cleaned) < min_length:
        raise ReviewEvidenceError(f"{field} is blank or too short")
    if (
        _PLACEHOLDER.search(cleaned)
        or "replace_with" in cleaned.casefold()
        or "{{" in cleaned
        or "}}" in cleaned
    ):
        raise ReviewEvidenceError(f"{field} contains placeholder text")
    return cleaned


def _optional_text(value: Any, field: str) -> str:
    if value in (None, ""):
        return ""
    return _text(value, field)


def _texts(value: Any, field: str, *, allow_empty: bool = False) -> list[str]:
    return [
        _text(item, f"{field}[{index}]")
        for index, item in enumerate(_list(value, field, allow_empty=allow_empty))
    ]


def _exact_keys(value: Mapping[str, Any], expected: set[str], field: str) -> None:
    missing = sorted(expected - set(value))
    unknown = sorted(set(value) - expected)
    if missing or unknown:
        details = []
        if missing:
            details.append(f"missing: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown: {', '.join(unknown)}")
        raise ReviewEvidenceError(f"{field} fields invalid ({'; '.join(details)})")


def _reject_private_fields(value: Any, field: str = "review") -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).casefold() in _FORBIDDEN_REVIEW_KEYS:
                raise ReviewEvidenceError(f"{field} contains prohibited private field: {key}")
            _reject_private_fields(item, f"{field}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_private_fields(item, f"{field}[{index}]")


def _reject_sensitive_content(value: Mapping[str, Any], field: str) -> None:
    serialized = canonical_json_bytes(value)
    if any(marker in serialized for marker in _SECRET_MARKERS):
        raise ReviewEvidenceError(f"{field} contains a prohibited secret marker")
    text = serialized.decode("utf-8")
    if re.search(
        r"(?i)\b(?:easting|northing|latitude|longitude|NGR)\s*[:=]\s*[-+]?\d",
        text,
    ):
        raise ReviewEvidenceError(f"{field} contains coordinate-like sensitive content")
    if re.search(r"(?i)(?:[A-Z]:\\(?:Users|Documents)\\|/(?:home|Users)/|data/private/)", text):
        raise ReviewEvidenceError(f"{field} contains a private local path")


def _safe_repository_reference(value: str, field: str) -> str:
    text = _text(value, field)
    if "\\" in text or re.match(r"^[A-Za-z]:", text) or text.startswith(("/", "~")):
        raise ReviewEvidenceError(f"{field} must not expose an absolute or local path")
    if text.startswith(("http://", "https://")):
        parsed = urlsplit(text)
        if (
            parsed.scheme != "https"
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or parsed.query
        ):
            raise ReviewEvidenceError(f"{field} must be a query-free public HTTPS reference")
        return text
    path = PurePosixPath(text.split("#", 1)[0])
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ReviewEvidenceError(f"{field} must be a safe repository-relative reference")
    return text


def _validate_date(value: Any, field: str) -> str:
    text = _text(value, field, min_length=10)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as exc:
        raise ReviewEvidenceError(f"{field} must use YYYY-MM-DD") from exc
    if parsed > date.today():
        raise ReviewEvidenceError(f"{field} must not be in the future")
    return text


def validate_review_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a completed external-review record; templates never pass."""
    payload = dict(record)
    _reject_private_fields(payload)
    _reject_sensitive_content(payload, "review")
    _exact_keys(
        payload,
        {
            "schema_version",
            "record_status",
            "review_id",
            "review_domain",
            "reviewed_repository_commit",
            "review_bundle_manifest_sha256",
            "review_date",
            "reviewer",
            "scope_reviewed",
            "methodology",
            "tools_used",
            "ai_assistance",
            "limitations",
            "findings",
            "overall_conclusion",
            "attestation",
            "evidence_references",
        },
        "review",
    )
    if payload["schema_version"] != REVIEW_SCHEMA:
        raise ReviewEvidenceError("review.schema_version is unsupported")
    if payload["record_status"] != "COMPLETE":
        raise ReviewEvidenceError("review.record_status must be COMPLETE; templates do not count")

    domain = payload["review_domain"]
    if domain not in REQUIRED_DOMAINS:
        raise ReviewEvidenceError("review.review_domain is unsupported")
    review_id = _text(payload["review_id"], "review.review_id")
    if not _REVIEW_ID.fullmatch(review_id) or DOMAIN_PREFIX[domain] not in review_id:
        raise ReviewEvidenceError("review.review_id does not match its domain")
    commit = _text(payload["reviewed_repository_commit"], "review.reviewed_repository_commit")
    if not _COMMIT_SHA.fullmatch(commit):
        raise ReviewEvidenceError(
            "review.reviewed_repository_commit must be 40 lowercase hex digits"
        )
    bundle_digest = _text(
        payload["review_bundle_manifest_sha256"], "review.review_bundle_manifest_sha256"
    )
    if not _SHA256.fullmatch(bundle_digest):
        raise ReviewEvidenceError(
            "review.review_bundle_manifest_sha256 must be 64 lowercase hex digits"
        )
    _validate_date(payload["review_date"], "review.review_date")

    reviewer = _mapping(payload["reviewer"], "review.reviewer")
    _exact_keys(
        reviewer,
        {
            "public_attribution",
            "affiliation",
            "expertise",
            "independence_declaration",
            "conflict_of_interest_declaration",
        },
        "review.reviewer",
    )
    attribution = _text(reviewer["public_attribution"], "review.reviewer.public_attribution")
    if attribution.casefold() in {"anonymous", "reviewer", "independent reviewer"}:
        raise ReviewEvidenceError("reviewer attribution must be stable and owner-verifiable")
    _optional_text(reviewer["affiliation"], "review.reviewer.affiliation")
    _text(reviewer["expertise"], "review.reviewer.expertise", min_length=12)
    _text(
        reviewer["independence_declaration"],
        "review.reviewer.independence_declaration",
        min_length=12,
    )
    _text(
        reviewer["conflict_of_interest_declaration"],
        "review.reviewer.conflict_of_interest_declaration",
        min_length=12,
    )
    _texts(payload["scope_reviewed"], "review.scope_reviewed")
    _text(payload["methodology"], "review.methodology", min_length=12)
    _texts(payload["tools_used"], "review.tools_used", allow_empty=True)
    _text(payload["ai_assistance"], "review.ai_assistance", min_length=8)
    _text(payload["limitations"], "review.limitations", min_length=8)

    findings = _list(payload["findings"], "review.findings", allow_empty=True)
    seen_findings: set[str] = set()
    for index, raw_finding in enumerate(findings):
        finding = _mapping(raw_finding, f"review.findings[{index}]")
        _validate_finding(finding, review_id=review_id, domain=domain, index=index)
        finding_id = str(finding["finding_id"])
        if finding_id in seen_findings:
            raise ReviewEvidenceError(f"duplicate finding ID: {finding_id}")
        seen_findings.add(finding_id)

    conclusion = payload["overall_conclusion"]
    if conclusion not in CONCLUSIONS:
        raise ReviewEvidenceError("review.overall_conclusion is unsupported")
    if conclusion != "PASS" and not findings:
        raise ReviewEvidenceError("a non-PASS conclusion must include at least one finding")
    if conclusion == "PASS" and any(
        finding["severity"] in {"blocker", "high"} for finding in findings
    ):
        raise ReviewEvidenceError("PASS cannot contain blocker or high findings")
    _text(payload["attestation"], "review.attestation", min_length=20)
    references = _texts(payload["evidence_references"], "review.evidence_references")
    for index, reference in enumerate(references):
        _safe_repository_reference(reference, f"review.evidence_references[{index}]")
    return payload


def _validate_finding(
    finding: Mapping[str, Any], *, review_id: str, domain: str, index: int
) -> None:
    field = f"review.findings[{index}]"
    _exact_keys(
        finding,
        {
            "finding_id",
            "originating_review_id",
            "review_domain",
            "severity",
            "title",
            "description",
            "evidence_reference",
            "affected_components",
            "impact_flags",
            "recommended_action",
        },
        field,
    )
    finding_id = _text(finding["finding_id"], f"{field}.finding_id")
    if not _FINDING_ID.fullmatch(finding_id) or DOMAIN_PREFIX[domain] not in finding_id:
        raise ReviewEvidenceError(f"{field}.finding_id does not match its domain")
    if finding["originating_review_id"] != review_id:
        raise ReviewEvidenceError(f"{field}.originating_review_id does not match the review")
    if finding["review_domain"] != domain:
        raise ReviewEvidenceError(f"{field}.review_domain does not match the review")
    if finding["severity"] not in SEVERITIES:
        raise ReviewEvidenceError(f"{field}.severity is unsupported")
    _text(finding["title"], f"{field}.title")
    _text(finding["description"], f"{field}.description", min_length=12)
    _safe_repository_reference(finding["evidence_reference"], f"{field}.evidence_reference")
    components = _texts(finding["affected_components"], f"{field}.affected_components")
    for component_index, component in enumerate(components):
        _safe_repository_reference(component, f"{field}.affected_components[{component_index}]")
    impacts = _mapping(finding["impact_flags"], f"{field}.impact_flags")
    _exact_keys(
        impacts, {"scientific", "privacy", "security", "licensing"}, f"{field}.impact_flags"
    )
    if any(not isinstance(value, bool) for value in impacts.values()):
        raise ReviewEvidenceError(f"{field}.impact_flags values must be booleans")
    _text(finding["recommended_action"], f"{field}.recommended_action", min_length=8)


def load_review_record(path: str | Path) -> dict[str, Any]:
    """Load and validate one completed external-review record."""
    source = Path(path)
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewEvidenceError(f"could not read review evidence: {source.name}") from exc
    return validate_review_record(_mapping(payload, "review"))


def load_review_policy(root: str | Path, policy_path: str | Path | None = None) -> dict[str, Any]:
    """Load the strict Phase 5E review policy."""
    base = Path(root).resolve()
    source = Path(policy_path or base / "docs/review/phase5e-review-policy.json").resolve()
    try:
        policy = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ReviewEvidenceError("could not read Phase 5E review policy") from exc
    payload = _mapping(policy, "policy")
    _exact_keys(
        payload,
        {
            "schema_version",
            "repository",
            "required_domains",
            "evidence_directory",
            "owner_decision_path",
            "bundle",
        },
        "policy",
    )
    if payload["schema_version"] != POLICY_SCHEMA:
        raise ReviewEvidenceError("policy.schema_version is unsupported")
    if payload["repository"] != "essius10/ArchaeoAI":
        raise ReviewEvidenceError("policy.repository is unexpected")
    if tuple(payload["required_domains"]) != REQUIRED_DOMAINS:
        raise ReviewEvidenceError("policy.required_domains must contain the four canonical tracks")
    if payload["evidence_directory"] != "docs/review/evidence":
        raise ReviewEvidenceError("policy.evidence_directory is unexpected")
    if payload["owner_decision_path"] != "docs/review/evidence/phase5e-owner-decision.json":
        raise ReviewEvidenceError("policy.owner_decision_path is unexpected")
    bundle = _mapping(payload["bundle"], "policy.bundle")
    _exact_keys(
        bundle,
        {
            "format_version",
            "output_root",
            "files",
            "prohibited_prefixes",
            "prohibited_suffixes",
        },
        "policy.bundle",
    )
    if bundle["format_version"] != "archaeoai-phase5e-review-bundle-v1":
        raise ReviewEvidenceError("policy.bundle.format_version is unsupported")
    if bundle["output_root"] != "outputs/review":
        raise ReviewEvidenceError("policy.bundle.output_root is unexpected")
    files = _list(bundle["files"], "policy.bundle.files")
    seen: set[str] = set()
    for index, raw_entry in enumerate(files):
        entry = _mapping(raw_entry, f"policy.bundle.files[{index}]")
        _exact_keys(entry, {"path", "tracks"}, f"policy.bundle.files[{index}]")
        path = _safe_relative_path(entry["path"], f"policy.bundle.files[{index}].path")
        if path in seen:
            raise ReviewEvidenceError(f"duplicate bundle file: {path}")
        seen.add(path)
        tracks = _texts(entry["tracks"], f"policy.bundle.files[{index}].tracks")
        if any(track not in {*REQUIRED_DOMAINS, "all"} for track in tracks):
            raise ReviewEvidenceError(f"unsupported review track for bundle file: {path}")
    for field in ("prohibited_prefixes", "prohibited_suffixes"):
        _texts(bundle[field], f"policy.bundle.{field}")
    return payload


def _safe_relative_path(value: Any, field: str) -> str:
    text = _text(value, field)
    if "\\" in text or re.match(r"^[A-Za-z]:", text):
        raise ReviewEvidenceError(f"{field} must use repository-relative POSIX syntax")
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts or "." in path.parts or not path.parts:
        raise ReviewEvidenceError(f"{field} must be a safe repository-relative path")
    return path.as_posix()


def _git(root: Path, *arguments: str, binary: bool = False) -> bytes | str:
    process = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=not binary,
    )
    if process.returncode != 0:
        raise ReviewEvidenceError(
            f"Git could not resolve review bundle input: {' '.join(arguments)}"
        )
    return process.stdout


def _resolve_commit(root: Path, revision: str) -> str:
    resolved = str(_git(root, "rev-parse", "--verify", f"{revision}^{{commit}}")).strip()
    if not _COMMIT_SHA.fullmatch(resolved):
        raise ReviewEvidenceError("review bundle commit could not be resolved")
    return resolved


def assert_review_commit_available(root: str | Path, commit: str) -> None:
    """Require an evidence record to name an exact commit available in this repository."""
    if not _COMMIT_SHA.fullmatch(commit):
        raise ReviewEvidenceError("reviewed repository commit is malformed")
    if _resolve_commit(Path(root).resolve(), commit) != commit:
        raise ReviewEvidenceError("reviewed repository commit is unavailable")


def _git_blob(root: Path, commit: str, relative: str) -> bytes:
    entry = str(_git(root, "ls-tree", commit, "--", relative)).strip()
    if not entry or "\t" not in entry:
        raise ReviewEvidenceError(f"bundle input is not tracked at reviewed commit: {relative}")
    metadata, tracked_path = entry.split("\t", 1)
    mode, object_type, _object_id = metadata.split()
    if tracked_path != relative or object_type != "blob" or mode == "120000":
        raise ReviewEvidenceError(f"bundle input is not a regular tracked file: {relative}")
    return bytes(_git(root, "show", f"{commit}:{relative}", binary=True))


def _assert_bundle_path_allowed(relative: str, policy: Mapping[str, Any]) -> None:
    bundle = policy["bundle"]
    casefolded = relative.casefold()
    for prefix in {*bundle["prohibited_prefixes"], *_HARD_PROHIBITED_PREFIXES}:
        prefix_text = str(prefix).casefold().rstrip("/")
        if casefolded == prefix_text or casefolded.startswith(prefix_text + "/"):
            raise ReviewEvidenceError(f"bundle input uses a prohibited path: {relative}")
    suffixes = {*bundle["prohibited_suffixes"], *_HARD_PROHIBITED_SUFFIXES}
    if any(casefolded.endswith(str(suffix).casefold()) for suffix in suffixes):
        raise ReviewEvidenceError(f"bundle input uses a prohibited file type: {relative}")


def _prepare_review_bundle(
    root: Path, commit: str, policy: Mapping[str, Any]
) -> tuple[dict[str, Any], list[tuple[str, bytes]], bytes, str]:
    entries: list[dict[str, Any]] = []
    blobs: list[tuple[str, bytes]] = []
    for item in sorted(policy["bundle"]["files"], key=lambda entry: entry["path"]):
        relative = _safe_relative_path(item["path"], "bundle file")
        _assert_bundle_path_allowed(relative, policy)
        content = _git_blob(root, commit, relative)
        if any(marker in content for marker in _SECRET_MARKERS):
            raise ReviewEvidenceError(
                f"bundle input contains a prohibited secret marker: {relative}"
            )
        blobs.append((relative, content))
        entries.append(
            {
                "path": relative,
                "review_tracks": sorted(item["tracks"]),
                "sha256": sha256_bytes(content),
                "size_bytes": len(content),
            }
        )
    manifest = {
        "schema_version": policy["bundle"]["format_version"],
        "repository": policy["repository"],
        "reviewed_repository_commit": commit,
        "deterministic": True,
        "identity_claim": False,
        "files": entries,
    }
    manifest_bytes = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False).encode() + b"\n"
    )
    return manifest, blobs, manifest_bytes, sha256_bytes(manifest_bytes)


def expected_review_bundle_manifest_sha256(
    root: str | Path,
    *,
    revision: str = "HEAD",
    policy_path: str | Path | None = None,
) -> str:
    """Recompute the canonical review-bundle manifest digest without writing a bundle."""
    base = Path(root).resolve()
    policy = load_review_policy(base, policy_path)
    commit = _resolve_commit(base, revision)
    _manifest, _blobs, _manifest_bytes, digest = _prepare_review_bundle(base, commit, policy)
    return digest


def build_review_bundle(
    root: str | Path,
    destination: str | Path,
    *,
    revision: str = "HEAD",
    policy_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build a deterministic, Git-version-bound public-safe review directory."""
    base = Path(root).resolve()
    policy = load_review_policy(base, policy_path)
    commit = _resolve_commit(base, revision)
    output_root = (base / policy["bundle"]["output_root"]).resolve()
    target = Path(destination).resolve()
    try:
        target.relative_to(output_root)
    except ValueError as exc:
        raise ReviewEvidenceError(
            "review bundle output must remain under the configured output root"
        ) from exc
    if target == output_root:
        raise ReviewEvidenceError(
            "review bundle output must be a child of the configured output root"
        )
    if target.exists():
        raise ReviewEvidenceError("review bundle destination already exists")
    output_root.mkdir(parents=True, exist_ok=True)

    manifest, blobs, manifest_bytes, manifest_digest = _prepare_review_bundle(base, commit, policy)

    temporary = Path(tempfile.mkdtemp(prefix=".phase5e-building-", dir=output_root)).resolve()
    try:
        files_root = temporary / "files"
        for relative, content in blobs:
            destination_path = files_root / PurePosixPath(relative)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.write_bytes(content)
        (temporary / "manifest.json").write_bytes(manifest_bytes)
        (temporary / "manifest.sha256").write_text(
            f"{manifest_digest}  manifest.json\n", encoding="ascii", newline="\n"
        )
        temporary.rename(target)
    except Exception:
        if temporary.exists() and temporary.parent == output_root:
            shutil.rmtree(temporary)
        raise
    return manifest


def verify_review_bundle(path: str | Path) -> dict[str, Any]:
    """Verify a generated bundle manifest, file set, and SHA-256 bindings."""
    supplied = Path(path)
    if supplied.is_symlink():
        raise ReviewEvidenceError("review bundle must be a non-symlink directory")
    root = supplied.resolve()
    if not root.is_dir():
        raise ReviewEvidenceError("review bundle must be a non-symlink directory")
    if (root / "manifest.json").is_symlink() or (root / "manifest.sha256").is_symlink():
        raise ReviewEvidenceError("review bundle manifest files must not be symlinks")
    try:
        manifest_bytes = (root / "manifest.json").read_bytes()
        digest_line = (root / "manifest.sha256").read_text(encoding="ascii").strip()
        manifest = json.loads(manifest_bytes)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReviewEvidenceError("review bundle manifest is missing or malformed") from exc
    expected_digest = sha256_bytes(manifest_bytes)
    if digest_line != f"{expected_digest}  manifest.json":
        raise ReviewEvidenceError("review bundle manifest SHA-256 mismatch")
    payload = _mapping(manifest, "bundle manifest")
    _exact_keys(
        payload,
        {
            "schema_version",
            "repository",
            "reviewed_repository_commit",
            "deterministic",
            "identity_claim",
            "files",
        },
        "bundle manifest",
    )
    if payload["schema_version"] != "archaeoai-phase5e-review-bundle-v1":
        raise ReviewEvidenceError("review bundle schema is unsupported")
    if payload["repository"] != "essius10/ArchaeoAI":
        raise ReviewEvidenceError("review bundle repository is unexpected")
    if not _COMMIT_SHA.fullmatch(str(payload["reviewed_repository_commit"])):
        raise ReviewEvidenceError("review bundle commit is malformed")
    if payload["deterministic"] is not True or payload["identity_claim"] is not False:
        raise ReviewEvidenceError("review bundle integrity boundary is malformed")
    files = _list(payload.get("files"), "bundle manifest.files")
    expected_files = {"manifest.json", "manifest.sha256"}
    seen: set[str] = set()
    manifest_paths: list[str] = []
    for index, raw_entry in enumerate(files):
        entry = _mapping(raw_entry, f"bundle manifest.files[{index}]")
        _exact_keys(
            entry,
            {"path", "review_tracks", "sha256", "size_bytes"},
            f"bundle manifest.files[{index}]",
        )
        relative = _safe_relative_path(entry["path"], f"bundle manifest.files[{index}].path")
        if relative in seen:
            raise ReviewEvidenceError(f"duplicate bundle manifest path: {relative}")
        seen.add(relative)
        manifest_paths.append(relative)
        tracks = _texts(entry["review_tracks"], f"bundle manifest.files[{index}].review_tracks")
        if tracks != sorted(tracks) or any(
            track not in {*REQUIRED_DOMAINS, "all"} for track in tracks
        ):
            raise ReviewEvidenceError(f"bundle manifest review tracks are invalid: {relative}")
        if not _SHA256.fullmatch(str(entry["sha256"])):
            raise ReviewEvidenceError(f"bundle manifest SHA-256 is malformed: {relative}")
        if isinstance(entry["size_bytes"], bool) or not isinstance(entry["size_bytes"], int):
            raise ReviewEvidenceError(f"bundle manifest size is malformed: {relative}")
        bundled = root / "files" / PurePosixPath(relative)
        cursor = bundled
        while cursor != root:
            if cursor.is_symlink():
                raise ReviewEvidenceError(f"bundled file uses a symlink: {relative}")
            cursor = cursor.parent
        if not bundled.is_file():
            raise ReviewEvidenceError(f"bundled file is missing or unsafe: {relative}")
        content = bundled.read_bytes()
        if entry["sha256"] != sha256_bytes(content) or entry["size_bytes"] != len(content):
            raise ReviewEvidenceError(f"bundled file integrity mismatch: {relative}")
        expected_files.add(f"files/{relative}")
    if manifest_paths != sorted(manifest_paths):
        raise ReviewEvidenceError("review bundle manifest file order is not deterministic")
    actual_files = {
        item.relative_to(root).as_posix()
        for item in root.rglob("*")
        if item.is_file() or item.is_symlink()
    }
    if actual_files != expected_files:
        raise ReviewEvidenceError("review bundle contains an unmanifested or missing file")
    return payload


def validate_owner_decision(
    decision: Mapping[str, Any], reviews: Mapping[str, Mapping[str, Any]]
) -> dict[str, Any]:
    """Validate a final owner decision against immutable external-review records."""
    payload = dict(decision)
    _reject_private_fields(payload, "owner_decision")
    _reject_sensitive_content(payload, "owner_decision")
    _exact_keys(
        payload,
        {
            "schema_version",
            "decision_status",
            "decision_id",
            "decision_date",
            "owner_public_attribution",
            "accepted_reviews",
            "historical_reviews",
            "finding_dispositions",
            "phase5e_decision",
            "phase5f_authorization",
            "residual_limitations",
            "attestation",
        },
        "owner_decision",
    )
    if payload["schema_version"] != OWNER_DECISION_SCHEMA:
        raise ReviewEvidenceError("owner_decision.schema_version is unsupported")
    if payload["decision_status"] != "COMPLETE" or payload["phase5e_decision"] != "COMPLETE":
        raise ReviewEvidenceError("owner decision must explicitly complete Phase 5E")
    if payload["phase5f_authorization"] != "NOT_AUTHORIZED":
        raise ReviewEvidenceError("Phase 5E decision cannot authorize Phase 5F")
    _text(payload["decision_id"], "owner_decision.decision_id")
    _validate_date(payload["decision_date"], "owner_decision.decision_date")
    _text(payload["owner_public_attribution"], "owner_decision.owner_public_attribution")
    _text(payload["attestation"], "owner_decision.attestation", min_length=20)
    _texts(payload["residual_limitations"], "owner_decision.residual_limitations")

    accepted = _mapping(payload["accepted_reviews"], "owner_decision.accepted_reviews")
    _exact_keys(accepted, set(REQUIRED_DOMAINS), "owner_decision.accepted_reviews")
    accepted_ids: set[str] = set()
    for domain in REQUIRED_DOMAINS:
        bindings = _list(accepted[domain], f"owner_decision.accepted_reviews.{domain}")
        for index, raw_binding in enumerate(bindings):
            binding = _mapping(raw_binding, f"accepted review {domain}[{index}]")
            _exact_keys(
                binding, {"review_id", "record_sha256"}, f"accepted review {domain}[{index}]"
            )
            review_id = _text(binding["review_id"], f"accepted review {domain}.review_id")
            if review_id in accepted_ids:
                raise ReviewEvidenceError(
                    "one review record cannot satisfy multiple review domains"
                )
            accepted_ids.add(review_id)
            review = reviews.get(review_id)
            if review is None or review["review_domain"] != domain:
                raise ReviewEvidenceError(f"accepted {domain} review is missing or mismatched")
            if review["overall_conclusion"] == "NO_GO":
                raise ReviewEvidenceError(f"accepted {domain} review has a NO_GO conclusion")
            if binding["record_sha256"] != review_record_sha256(review):
                raise ReviewEvidenceError(f"accepted {domain} review hash mismatch")

    historical = _list(
        payload["historical_reviews"], "owner_decision.historical_reviews", allow_empty=True
    )
    historical_ids: set[str] = set()
    for index, raw_binding in enumerate(historical):
        field = f"owner_decision.historical_reviews[{index}]"
        binding = _mapping(raw_binding, field)
        _exact_keys(
            binding,
            {"review_id", "record_sha256", "superseded_by_review_id"},
            field,
        )
        review_id = _text(binding["review_id"], f"{field}.review_id")
        superseding_id = _text(
            binding["superseded_by_review_id"], f"{field}.superseded_by_review_id"
        )
        if review_id in accepted_ids or review_id in historical_ids:
            raise ReviewEvidenceError("review records must have exactly one closeout role")
        review = reviews.get(review_id)
        superseding_review = reviews.get(superseding_id)
        if review is None:
            raise ReviewEvidenceError(f"historical review is missing: {review_id}")
        if superseding_id not in accepted_ids or superseding_review is None:
            raise ReviewEvidenceError(
                f"historical review must name an accepted superseding review: {review_id}"
            )
        if superseding_review["review_domain"] != review["review_domain"]:
            raise ReviewEvidenceError(f"historical review superseding domain mismatch: {review_id}")
        if binding["record_sha256"] != review_record_sha256(review):
            raise ReviewEvidenceError(f"historical review hash mismatch: {review_id}")
        historical_ids.add(review_id)
    if accepted_ids | historical_ids != set(reviews):
        raise ReviewEvidenceError(
            "owner decision must bind every submitted review as accepted or historical"
        )

    dispositions = _list(
        payload["finding_dispositions"], "owner_decision.finding_dispositions", allow_empty=True
    )
    by_finding: dict[str, Mapping[str, Any]] = {}
    for index, raw_disposition in enumerate(dispositions):
        disposition = _mapping(raw_disposition, f"owner_decision.finding_dispositions[{index}]")
        _validate_disposition(disposition, index=index)
        finding_id = str(disposition["finding_id"])
        if finding_id in by_finding:
            raise ReviewEvidenceError(f"duplicate owner disposition: {finding_id}")
        by_finding[finding_id] = disposition

    all_findings: dict[str, Mapping[str, Any]] = {}
    for review in reviews.values():
        for finding in review["findings"]:
            finding_id = finding["finding_id"]
            if finding_id in all_findings:
                raise ReviewEvidenceError(f"duplicate finding ID across reviews: {finding_id}")
            all_findings[finding_id] = finding
    if set(by_finding) != set(all_findings):
        raise ReviewEvidenceError(
            "every finding in accepted and historical reviews requires exactly one "
            "owner disposition"
        )
    for finding_id, finding in all_findings.items():
        disposition = by_finding[finding_id]
        if disposition["originating_review_id"] != finding["originating_review_id"]:
            raise ReviewEvidenceError(f"disposition origin mismatch: {finding_id}")
        if finding["severity"] in {"blocker", "high"} and not (
            disposition["owner_disposition"] == "REMEDIATE"
            and disposition["resolution_status"] == "RESOLVED"
        ):
            raise ReviewEvidenceError(f"blocker/high finding must be remediated: {finding_id}")
    return payload


def _validate_disposition(disposition: Mapping[str, Any], *, index: int) -> None:
    field = f"owner_decision.finding_dispositions[{index}]"
    _exact_keys(
        disposition,
        {
            "finding_id",
            "originating_review_id",
            "owner_disposition",
            "disposition_rationale",
            "code_or_doc_change",
            "evidence_references",
            "residual_limitation",
            "resolution_status",
            "resolved_by_commit",
            "final_verification",
        },
        field,
    )
    if not _FINDING_ID.fullmatch(_text(disposition["finding_id"], f"{field}.finding_id")):
        raise ReviewEvidenceError(f"{field}.finding_id is malformed")
    if not _REVIEW_ID.fullmatch(
        _text(disposition["originating_review_id"], f"{field}.originating_review_id")
    ):
        raise ReviewEvidenceError(f"{field}.originating_review_id is malformed")
    owner_disposition = disposition["owner_disposition"]
    resolution_status = disposition["resolution_status"]
    if owner_disposition not in DISPOSITIONS or resolution_status not in RESOLUTION_STATES:
        raise ReviewEvidenceError(f"{field} uses an unsupported disposition or status")
    expected_status = {
        "ACCEPT": "ACCEPTED_RISK",
        "REMEDIATE": "RESOLVED",
        "DEFER": "DEFERRED",
        "REJECT_WITH_RATIONALE": "REJECTED_WITH_RATIONALE",
    }[owner_disposition]
    if resolution_status != expected_status:
        raise ReviewEvidenceError(f"{field} disposition and resolution status are inconsistent")
    _text(disposition["disposition_rationale"], f"{field}.disposition_rationale", min_length=12)
    _optional_text(disposition["code_or_doc_change"], f"{field}.code_or_doc_change")
    references = _texts(
        disposition["evidence_references"], f"{field}.evidence_references", allow_empty=True
    )
    for reference_index, reference in enumerate(references):
        _safe_repository_reference(reference, f"{field}.evidence_references[{reference_index}]")
    residual = _optional_text(disposition["residual_limitation"], f"{field}.residual_limitation")
    resolved_by = _optional_text(disposition["resolved_by_commit"], f"{field}.resolved_by_commit")
    _text(disposition["final_verification"], f"{field}.final_verification", min_length=8)
    if owner_disposition == "REMEDIATE":
        if not references or not _COMMIT_SHA.fullmatch(resolved_by):
            raise ReviewEvidenceError(f"{field} remediation requires evidence and a commit SHA")
    elif owner_disposition in {"ACCEPT", "DEFER"} and not residual:
        raise ReviewEvidenceError(f"{field} requires an explicit residual limitation")


def evaluate_review_gate(root: str | Path, policy_path: str | Path | None = None) -> dict[str, Any]:
    """Derive the fail-closed Phase 5E status from attributable evidence files."""
    base = Path(root).resolve()
    policy = load_review_policy(base, policy_path)
    evidence_directory = base / policy["evidence_directory"]
    decision_path = base / policy["owner_decision_path"]
    reviews: dict[str, dict[str, Any]] = {}
    by_domain: dict[str, list[dict[str, Any]]] = {domain: [] for domain in REQUIRED_DOMAINS}
    manifest_hashes: dict[str, str] = {}
    if evidence_directory.exists():
        for path in sorted(evidence_directory.glob("*.json")):
            if path.resolve() == decision_path.resolve():
                continue
            review = load_review_record(path)
            reviewed_commit = review["reviewed_repository_commit"]
            assert_review_commit_available(base, reviewed_commit)
            if reviewed_commit not in manifest_hashes:
                manifest_hashes[reviewed_commit] = expected_review_bundle_manifest_sha256(
                    base, revision=reviewed_commit
                )
            expected_manifest = manifest_hashes[reviewed_commit]
            if review["review_bundle_manifest_sha256"] != expected_manifest:
                raise ReviewEvidenceError(
                    f"review bundle manifest hash mismatch: {review['review_id']}"
                )
            review_id = review["review_id"]
            if review_id in reviews:
                raise ReviewEvidenceError(f"duplicate review ID across evidence files: {review_id}")
            reviews[review_id] = review
            by_domain[review["review_domain"]].append(review)

    blockers: list[str] = []
    domain_status: dict[str, dict[str, Any]] = {}
    for domain in REQUIRED_DOMAINS:
        records = by_domain[domain]
        if not records:
            status = "NOT_RECEIVED"
            blockers.append(f"{domain} review missing/incomplete")
        elif any(
            record["overall_conclusion"] == "NO_GO"
            or any(item["severity"] == "blocker" for item in record["findings"])
            for record in records
        ):
            status = "BLOCKED"
            blockers.append(f"{domain} review contains a blocker or NO_GO conclusion")
        else:
            status = "RECEIVED"
            blockers.append(f"{domain} review received but owner acceptance is pending")
        domain_status[domain] = {
            "status": status,
            "review_ids": [record["review_id"] for record in records],
            "reviewed_repository_commits": sorted(
                {record["reviewed_repository_commit"] for record in records}
            ),
        }

    owner_status = "PENDING"
    unresolved_blocker_findings = sorted(
        finding["finding_id"]
        for review in reviews.values()
        for finding in review["findings"]
        if finding["severity"] in {"blocker", "high"}
    )
    if decision_path.exists():
        try:
            decision_payload = json.loads(decision_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ReviewEvidenceError("owner decision is unreadable or malformed") from exc
        decision = validate_owner_decision(_mapping(decision_payload, "owner_decision"), reviews)
        owner_status = "COMPLETE"
        accepted = decision["accepted_reviews"]
        domain_status = {
            domain: {
                "status": "ACCEPTED",
                "review_ids": [binding["review_id"] for binding in accepted[domain]],
                "historical_review_ids": [
                    binding["review_id"]
                    for binding in decision["historical_reviews"]
                    if reviews[binding["review_id"]]["review_domain"] == domain
                ],
                "reviewed_repository_commits": sorted(
                    {
                        reviews[binding["review_id"]]["reviewed_repository_commit"]
                        for binding in accepted[domain]
                    }
                ),
            }
            for domain in REQUIRED_DOMAINS
        }
        blockers = []
        unresolved_blocker_findings = []

    phase5e_complete = owner_status == "COMPLETE" and all(
        value["status"] == "ACCEPTED" for value in domain_status.values()
    )
    if not phase5e_complete:
        blockers.append("explicit owner Phase 5E completion decision absent")
    blockers.append("separate explicit owner Phase 5F authorization absent")
    return {
        "schema_version": GATE_SCHEMA,
        "review_domains": domain_status,
        "unresolved_blocker_findings": unresolved_blocker_findings,
        "owner_decision": owner_status,
        "internal_phase5e_readiness": "READY",
        "independent_review_completion": "COMPLETE" if phase5e_complete else "PENDING",
        "phase5e_status": "COMPLETE" if phase5e_complete else "NOT COMPLETE",
        "phase5f_authorization": "NOT AUTHORIZED",
        "rq1_status": RQ1_STATUS,
        "reviewed_repository_shas": sorted(
            {review["reviewed_repository_commit"] for review in reviews.values()}
        ),
        "blockers": blockers,
    }
