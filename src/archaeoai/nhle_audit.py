"""Coordinate-safe metadata audit helpers for NHLE bowl-barrow feasibility.

This module deliberately operates on designation metadata only. It does not
download terrain, create raster patches, or claim that title triage produces
research-quality archaeological labels.
"""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from statistics import median
from typing import Any

NHLE_ITEM_ID = "767f279327a24845bf47dfe5eae9862b"
NHLE_LAYER_ID = 6
NHLE_ITEM_URL = (
    "https://opendata-historicengland.hub.arcgis.com/datasets/"
    "historicengland::national-heritage-list-for-england-nhle/explore?layer=6"
)
NHLE_SERVICE_URL = (
    "https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/"
    "National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer"
)
NHLE_LAYER_URL = f"{NHLE_SERVICE_URL}/{NHLE_LAYER_ID}"
NHLE_QUERY_URL = f"{NHLE_LAYER_URL}/query"
CLASSIFIER_VERSION = "title-triage-v1"
DEFAULT_SAMPLE_SEED = "E001-Phase-2A-2026-08-27"

_BOWL_BARROW = re.compile(r"\bbowl\s+barrow\b", re.IGNORECASE)
_NON_TARGET = re.compile(
    r"\b(?:long|bell|disc|saucer|platform|pond|oval|bank)\s+barrows?\b"
    r"|\bcairns?\b|\bring\s+ditches?\b|\bcropmarks?\b",
    re.IGNORECASE,
)
_MULTIPLE = re.compile(
    r"\b(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
    r"pair\s+of|group\s+of)\b.{0,80}\bbarrows?\b"
    r"|\b(?:bowl|round|long|bell|disc|saucer|platform|pond|oval|bank)\s+barrows\b"
    r"|\bbarrow\s+(?:cemetery|cemeteries|group|field)\b",
    re.IGNORECASE,
)
_SURVIVAL_PROBLEM = re.compile(
    r"\b(?:destroyed|levelled|flattened|ploughed|cropmark(?:s)?(?:\s+only)?|"
    r"reconstructed|restored)\b",
    re.IGNORECASE,
)
_COMPOUND_OR_CONTEXTUAL = re.compile(
    r"\b(?:and|including|containing|with|within|part\s+of|forming\s+part\s+of)\b",
    re.IGNORECASE,
)


class TriageCategory(StrEnum):
    """Conservative title-only categories, not final archaeological labels."""

    PROBABLE_BOWL = "probable_bowl_candidate"
    CLEAR_EXCLUSION = "clear_title_exclusion"
    MANUAL_REVIEW = "manual_review_required"


@dataclass(frozen=True, slots=True)
class TitleTriage:
    category: TriageCategory
    reason: str


@dataclass(frozen=True, slots=True)
class NhleRecord:
    """The small attribute subset used transiently during the audit."""

    list_entry: int
    name: str
    easting: float | None
    northing: float | None
    capture_scale: str | None = None
    area_ha: float | None = None


def triage_title(title: str) -> TitleTriage:
    """Classify an NHLE title conservatively for subsequent manual review.

    A probable result means only that the statutory title explicitly names one
    bowl barrow and contains no obvious title-level warning. Survival, geometry,
    and single-feature status still require inspection of the full list entry.
    """
    normalized = " ".join(title.split())
    if "barrow" not in normalized.casefold():
        raise ValueError("title triage requires a title containing 'barrow'")

    has_bowl_barrow = _BOWL_BARROW.search(normalized) is not None
    non_target = _NON_TARGET.search(normalized) is not None
    multiple = _MULTIPLE.search(normalized) is not None
    survival_problem = _SURVIVAL_PROBLEM.search(normalized) is not None

    if has_bowl_barrow:
        if multiple:
            return TitleTriage(TriageCategory.MANUAL_REVIEW, "possible multiple monument")
        if non_target:
            return TitleTriage(TriageCategory.MANUAL_REVIEW, "mixed monument types")
        if survival_problem:
            return TitleTriage(TriageCategory.MANUAL_REVIEW, "survival warning")
        if _COMPOUND_OR_CONTEXTUAL.search(normalized):
            return TitleTriage(TriageCategory.MANUAL_REVIEW, "compound or contextual title")
        return TitleTriage(TriageCategory.PROBABLE_BOWL, "explicit singular bowl-barrow title")

    if non_target:
        return TitleTriage(TriageCategory.CLEAR_EXCLUSION, "explicit non-target barrow type")
    if multiple:
        return TitleTriage(TriageCategory.CLEAR_EXCLUSION, "explicit multiple monuments")
    if survival_problem:
        return TitleTriage(TriageCategory.CLEAR_EXCLUSION, "explicit survival warning")
    return TitleTriage(TriageCategory.MANUAL_REVIEW, "generic or ambiguous barrow title")


def broad_grid_id(easting: float | None, northing: float | None, *, size_km: int = 100) -> str:
    """Return a coarse British National Grid cell without exposing coordinates."""
    if size_km <= 0:
        raise ValueError("size_km must be positive")
    if easting is None or northing is None:
        return "UNAVAILABLE"
    cell_size = size_km * 1000
    return f"BNG_{size_km}KM_E{int(easting // cell_size)}_N{int(northing // cell_size)}"


def stable_sample_ids(
    records: Iterable[NhleRecord],
    *,
    sample_size: int,
    seed: str = DEFAULT_SAMPLE_SEED,
) -> list[int]:
    """Select record IDs reproducibly without using coordinates or global RNG state."""
    if sample_size < 0:
        raise ValueError("sample_size must not be negative")
    ranked = sorted(
        records,
        key=lambda record: hashlib.sha256(f"{seed}:{record.list_entry}".encode()).hexdigest(),
    )
    return [record.list_entry for record in ranked[:sample_size]]


def _request_json(url: str, parameters: dict[str, str] | None = None) -> dict[str, Any]:
    if parameters:
        url = f"{url}?{urllib.parse.urlencode(parameters)}"
    request = urllib.request.Request(url, headers={"User-Agent": "ArchaeoAI-metadata-audit/1"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(f"ArcGIS service error: {payload['error']}")
    return payload


def fetch_source_metadata() -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch live service and Scheduled Monuments layer metadata."""
    return _request_json(NHLE_SERVICE_URL, {"f": "json"}), _request_json(
        NHLE_LAYER_URL, {"f": "json"}
    )


def fetch_total_record_count() -> int:
    payload = _request_json(
        NHLE_QUERY_URL,
        {"where": "1=1", "returnCountOnly": "true", "f": "json"},
    )
    return int(payload["count"])


def fetch_all_list_entry_ids(*, page_size: int = 2000) -> list[int]:
    """Fetch stable IDs only, allowing feature and designation counts to be compared."""
    if not 1 <= page_size <= 2000:
        raise ValueError("page_size must be between 1 and 2000")

    list_entries: list[int] = []
    offset = 0
    while True:
        payload = _request_json(
            NHLE_QUERY_URL,
            {
                "where": "1=1",
                "outFields": "ListEntry",
                "returnGeometry": "false",
                "orderByFields": "OBJECTID ASC",
                "resultOffset": str(offset),
                "resultRecordCount": str(page_size),
                "f": "json",
            },
        )
        features = payload.get("features", [])
        list_entries.extend(int(feature["attributes"]["ListEntry"]) for feature in features)
        if len(features) < page_size:
            break
        offset += len(features)
    return list_entries


def fetch_barrow_records(*, page_size: int = 2000) -> list[NhleRecord]:
    """Fetch only small title/ID/centroid metadata for titles containing 'barrow'."""
    if not 1 <= page_size <= 2000:
        raise ValueError("page_size must be between 1 and 2000")

    records: list[NhleRecord] = []
    offset = 0
    while True:
        payload = _request_json(
            NHLE_QUERY_URL,
            {
                "where": "UPPER(Name) LIKE '%BARROW%'",
                "outFields": "ListEntry,Name,Easting,Northing,CaptureScale,area_ha",
                "returnGeometry": "false",
                "orderByFields": "ListEntry ASC",
                "resultOffset": str(offset),
                "resultRecordCount": str(page_size),
                "f": "json",
            },
        )
        features = payload.get("features", [])
        for feature in features:
            attributes = feature["attributes"]
            records.append(
                NhleRecord(
                    list_entry=int(attributes["ListEntry"]),
                    name=str(attributes["Name"]),
                    easting=_optional_float(attributes.get("Easting")),
                    northing=_optional_float(attributes.get("Northing")),
                    capture_scale=_optional_string(attributes.get("CaptureScale")),
                    area_ha=_optional_float(attributes.get("area_ha")),
                )
            )
        if len(features) < page_size:
            break
        offset += len(features)
    return records


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


def _optional_string(value: object) -> str | None:
    return None if value is None else str(value)


def build_audit_summary(
    *,
    total_features: int,
    distinct_list_entries: int,
    barrow_records: list[NhleRecord],
    service_metadata: dict[str, Any],
    layer_metadata: dict[str, Any],
    accessed_at: datetime,
    sample_size: int = 30,
) -> tuple[dict[str, Any], list[dict[str, int | str]]]:
    """Build coordinate-free summary JSON content and coarse aggregate rows."""
    if accessed_at.tzinfo is None:
        raise ValueError("accessed_at must be timezone-aware")
    if distinct_list_entries > total_features:
        raise ValueError("distinct_list_entries cannot exceed total_features")
    broad_list_entries = [record.list_entry for record in barrow_records]
    if len(set(broad_list_entries)) != len(broad_list_entries):
        raise ValueError("broad candidate records must have unique List Entry Numbers")

    classified = [(record, triage_title(record.name)) for record in barrow_records]
    counts = Counter(triage.category for _, triage in classified)
    if sum(counts.values()) != len(barrow_records):
        raise AssertionError("triage categories must partition broad candidates")

    by_grid: dict[str, Counter[TriageCategory]] = defaultdict(Counter)
    for record, triage in classified:
        by_grid[broad_grid_id(record.easting, record.northing)][triage.category] += 1

    rows: list[dict[str, int | str]] = []
    for group_id, group_counts in sorted(by_grid.items()):
        rows.append(
            {
                "broad_group": group_id,
                "broad_barrow_candidates": sum(group_counts.values()),
                "probable_bowl_candidates": group_counts[TriageCategory.PROBABLE_BOWL],
                "clear_title_exclusions": group_counts[TriageCategory.CLEAR_EXCLUSION],
                "manual_review_required": group_counts[TriageCategory.MANUAL_REVIEW],
            }
        )

    probable_records = [
        record for record, triage in classified if triage.category is TriageCategory.PROBABLE_BOWL
    ]
    probable_capture_scales = Counter(
        record.capture_scale or "UNAVAILABLE" for record in probable_records
    )
    probable_areas = sorted(
        record.area_ha for record in probable_records if record.area_ha is not None
    )
    fields = [
        {
            "name": field.get("name"),
            "alias": field.get("alias"),
            "type": field.get("type"),
        }
        for field in layer_metadata.get("fields", [])
    ]
    last_edit_ms = layer_metadata.get("editingInfo", {}).get("lastEditDate")
    last_edit = (
        datetime.fromtimestamp(last_edit_ms / 1000, tz=UTC).isoformat()
        if last_edit_ms is not None
        else None
    )

    summary: dict[str, Any] = {
        "audit": {
            "purpose": "metadata-only E001 bowl-barrow feasibility audit",
            "accessed_at": accessed_at.astimezone(UTC).isoformat(),
            "classifier_version": CLASSIFIER_VERSION,
            "class_definition": (
                "a single bowl barrow in England, recorded as a Scheduled Monument, "
                "surviving as a discrete upstanding earthwork mound"
            ),
            "warning": (
                "Title triage is not a final label set; every probable candidate requires "
                "full-record and geometry review."
            ),
        },
        "source": {
            "official_item_url": NHLE_ITEM_URL,
            "arcgis_item_id": NHLE_ITEM_ID,
            "feature_service_url": NHLE_SERVICE_URL,
            "layer_id": NHLE_LAYER_ID,
            "layer_name": layer_metadata.get("name"),
            "geometry_type": layer_metadata.get("geometryType"),
            "spatial_reference": layer_metadata.get("extent", {}).get("spatialReference"),
            "last_edit_at": last_edit,
            "query_formats": _split_formats(layer_metadata.get("supportedQueryFormats", "")),
            "export_formats": _split_formats(service_metadata.get("supportedExportFormats", "")),
            "fields": fields,
        },
        "counts": {
            "total_scheduled_monument_records_examined": distinct_list_entries,
            "scheduled_monument_polygon_features": total_features,
            "duplicate_list_entry_features": total_features - distinct_list_entries,
            "broad_barrow_candidates": len(barrow_records),
            "probable_bowl_candidates": counts[TriageCategory.PROBABLE_BOWL],
            "clear_title_exclusions": counts[TriageCategory.CLEAR_EXCLUSION],
            "manual_review_required": counts[TriageCategory.MANUAL_REVIEW],
        },
        "geographic_distribution": {
            "aggregation": "100 km British National Grid cells; no coordinates retained",
            "groups_with_any_broad_candidate": len(by_grid),
            "groups_with_probable_bowl_candidates": sum(
                row["probable_bowl_candidates"] > 0 for row in rows
            ),
            "groups_with_at_least_25_probable_bowl_candidates": sum(
                row["probable_bowl_candidates"] >= 25 for row in rows
            ),
            "records_without_centroid_metadata": sum(
                record.easting is None or record.northing is None for record in barrow_records
            ),
        },
        "geometry_metadata": {
            "warning": (
                "Designation polygons indicate the protected area, not a mound segmentation "
                "mask; every selected patch centre requires visual review."
            ),
            "probable_candidate_capture_scales": dict(sorted(probable_capture_scales.items())),
            "probable_candidate_area_ha": {
                "available": len(probable_areas),
                "minimum": probable_areas[0] if probable_areas else None,
                "median": median(probable_areas) if probable_areas else None,
                "maximum": probable_areas[-1] if probable_areas else None,
            },
        },
        "manual_sample": {
            "method": "lowest SHA-256 ranks of seed and stable List Entry Number",
            "seed": DEFAULT_SAMPLE_SEED,
            "requested_size": sample_size,
            "record_ids": stable_sample_ids(
                probable_records,
                sample_size=min(sample_size, len(probable_records)),
            ),
        },
        "privacy": {
            "stored_coordinates": False,
            "stored_geometry": False,
            "tracked_aggregation_only": True,
        },
    }
    return summary, rows


def _split_formats(raw: str) -> list[str]:
    return [item.strip() for item in raw.split(",") if item.strip()]
