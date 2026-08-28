"""Typed validation for dataset provenance manifests."""

import re
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal, cast
from urllib.parse import urlparse

from archaeoai.paths import ensure_within_project, find_project_root, resolve_project_path

DatasetStatus = Literal["template", "planned", "acquired", "verified"]
SensitivityClassification = Literal["public", "restricted", "sensitive"]

_ALLOWED_STATUSES = frozenset({"template", "planned", "acquired", "verified"})
_ALLOWED_SENSITIVITY = frozenset({"public", "restricted", "sensitive"})
_DATASET_ID = re.compile(r"^[A-Z][A-Z0-9_-]{2,63}$")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


class ManifestError(ValueError):
    """Raised when a dataset manifest is malformed or incomplete."""


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    provider: str
    url: str
    license: str
    attribution: str | None
    edition: str | None
    service_url: str | None
    access_date: date | None


@dataclass(frozen=True, slots=True)
class SpatialMetadata:
    crs: str
    vertical_datum: str | None
    resolution_m: float
    geographic_area: str
    acquisition_date: date | None


@dataclass(frozen=True, slots=True)
class FileMetadata:
    expected_local_path: Path
    sha256: str | None
    checksum_scope: str | None


@dataclass(frozen=True, slots=True)
class DatasetManifest:
    dataset_id: str
    name: str
    description: str
    status: DatasetStatus
    sensitivity: SensitivityClassification
    source: SourceMetadata
    spatial: SpatialMetadata
    file: FileMetadata
    source_path: Path


def _table(document: dict[str, Any], name: str) -> dict[str, Any]:
    value = document.get(name)
    if not isinstance(value, dict):
        raise ManifestError(f"Missing or invalid [{name}] table")
    return value


def _reject_unknown(table: dict[str, Any], allowed: set[str], *, table_name: str) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise ManifestError(f"Unknown keys in [{table_name}]: {', '.join(unknown)}")


def _string(table: dict[str, Any], key: str, *, table_name: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"[{table_name}].{key} must be a non-empty string")
    return value.strip()


def _number(table: dict[str, Any], key: str, *, table_name: str) -> float:
    value = table.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ManifestError(f"[{table_name}].{key} must be numeric")
    return float(value)


def _optional_date(table: dict[str, Any], key: str, *, table_name: str) -> date | None:
    value = table.get(key)
    if value is None:
        return None
    if not isinstance(value, date):
        raise ManifestError(f"[{table_name}].{key} must be an unquoted TOML date")
    return value


def _optional_checksum(table: dict[str, Any]) -> str | None:
    value = table.get("sha256")
    if value is None:
        return None
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ManifestError("[file].sha256 must contain exactly 64 hexadecimal characters")
    return value.lower()


def _optional_string(table: dict[str, Any], key: str, *, table_name: str) -> str | None:
    value = table.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ManifestError(f"[{table_name}].{key} must be a non-empty string when supplied")
    return value.strip()


def _optional_https_url(table: dict[str, Any], key: str, *, table_name: str) -> str | None:
    value = _optional_string(table, key, table_name=table_name)
    if value is None:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ManifestError(f"[{table_name}].{key} must be a complete HTTPS URL")
    return value


def load_dataset_manifest(
    manifest_path: str | Path,
    *,
    project_root: Path | None = None,
) -> DatasetManifest:
    """Load dataset metadata without opening or claiming the associated data file."""
    source_path = Path(manifest_path).resolve()
    root = (project_root or find_project_root(source_path)).resolve()
    ensure_within_project(root, source_path, field_name="manifest_path")

    try:
        with source_path.open("rb") as manifest_file:
            document = tomllib.load(manifest_file)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ManifestError(f"Could not load dataset manifest {source_path}: {exc}") from exc

    _reject_unknown(document, {"dataset", "source", "spatial", "file"}, table_name="root")

    dataset = _table(document, "dataset")
    _reject_unknown(
        dataset,
        {"id", "name", "description", "status", "sensitivity"},
        table_name="dataset",
    )
    dataset_id = _string(dataset, "id", table_name="dataset")
    if not _DATASET_ID.fullmatch(dataset_id):
        raise ManifestError("[dataset].id must be 3-64 uppercase letters, digits, '-' or '_'")
    status_raw = _string(dataset, "status", table_name="dataset")
    if status_raw not in _ALLOWED_STATUSES:
        raise ManifestError(f"Unsupported dataset status: {status_raw}")
    sensitivity_raw = _string(dataset, "sensitivity", table_name="dataset")
    if sensitivity_raw not in _ALLOWED_SENSITIVITY:
        raise ManifestError(f"Unsupported sensitivity classification: {sensitivity_raw}")

    source = _table(document, "source")
    _reject_unknown(
        source,
        {"provider", "url", "license", "attribution", "edition", "service_url", "access_date"},
        table_name="source",
    )
    source_url = _string(source, "url", table_name="source")
    parsed_url = urlparse(source_url)
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise ManifestError("[source].url must be a complete HTTPS URL")
    access_date = _optional_date(source, "access_date", table_name="source")

    spatial = _table(document, "spatial")
    _reject_unknown(
        spatial,
        {"crs", "vertical_datum", "resolution_m", "geographic_area", "acquisition_date"},
        table_name="spatial",
    )
    resolution_m = _number(spatial, "resolution_m", table_name="spatial")
    if resolution_m <= 0:
        raise ManifestError("[spatial].resolution_m must be positive")

    file_table = _table(document, "file")
    _reject_unknown(
        file_table,
        {"expected_local_path", "sha256", "checksum_scope"},
        table_name="file",
    )
    checksum = _optional_checksum(file_table)

    if status_raw == "template" and (access_date is not None or checksum is not None):
        raise ManifestError("Template manifests must not imply data access or file verification")
    if status_raw in {"acquired", "verified"} and (access_date is None or checksum is None):
        raise ManifestError("Acquired or verified datasets require access_date and sha256")

    return DatasetManifest(
        dataset_id=dataset_id,
        name=_string(dataset, "name", table_name="dataset"),
        description=_string(dataset, "description", table_name="dataset"),
        status=cast(DatasetStatus, status_raw),
        sensitivity=cast(SensitivityClassification, sensitivity_raw),
        source=SourceMetadata(
            provider=_string(source, "provider", table_name="source"),
            url=source_url,
            license=_string(source, "license", table_name="source"),
            attribution=_optional_string(source, "attribution", table_name="source"),
            edition=_optional_string(source, "edition", table_name="source"),
            service_url=_optional_https_url(source, "service_url", table_name="source"),
            access_date=access_date,
        ),
        spatial=SpatialMetadata(
            crs=_string(spatial, "crs", table_name="spatial"),
            vertical_datum=_optional_string(spatial, "vertical_datum", table_name="spatial"),
            resolution_m=resolution_m,
            geographic_area=_string(spatial, "geographic_area", table_name="spatial"),
            acquisition_date=_optional_date(
                spatial,
                "acquisition_date",
                table_name="spatial",
            ),
        ),
        file=FileMetadata(
            expected_local_path=resolve_project_path(
                root,
                _string(file_table, "expected_local_path", table_name="file"),
                field_name="file.expected_local_path",
            ),
            sha256=checksum,
            checksum_scope=_optional_string(file_table, "checksum_scope", table_name="file"),
        ),
        source_path=source_path,
    )
