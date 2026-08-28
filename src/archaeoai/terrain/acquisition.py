"""Bounded EA WCS acquisition and private NHLE site reconstruction."""

from __future__ import annotations

import csv
import hashlib
import json
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError

from archaeoai.nhle_audit import NHLE_QUERY_URL
from archaeoai.terrain.patches import Bounds
from archaeoai.terrain.privacy import ensure_private_output, verify_git_ignored

EA_DTM_DATASET_ID = "13787b9a-26a4-4775-8523-806d13af58fc"
EA_DTM_WCS_URL = (
    "https://environment.data.gov.uk/spatialdata/lidar-composite-digital-terrain-model-dtm-1m/wcs"
)
EA_DTM_COVERAGE_ID = f"{EA_DTM_DATASET_ID}__Lidar_Composite_Elevation_DTM_1m"
ACQUISITION_VERSION = "e001-wcs-v1"
RETRYABLE_HTTP_CODES = frozenset({429, 500, 502, 503, 504})


class WcsRequestError(RuntimeError):
    """A reason-coded WCS response or transport failure."""

    def __init__(self, reason: str, *, attempts: int, retries: int):
        self.reason = reason
        self.attempts = attempts
        self.retries = retries
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class WcsPayload:
    content: bytes
    sha256: str
    size_bytes: int
    attempts: int
    retries: int


@dataclass(frozen=True, slots=True)
class AcceptedSite:
    list_entry: int
    geographic_group_id: str
    terrain_year: str
    source_resolution_m: str
    survey_program: str


@dataclass(frozen=True, slots=True)
class PrivateSiteLocation:
    list_entry: int
    easting: float
    northing: float
    geographic_group_id: str
    terrain_year: str
    source_resolution_m: str
    survey_program: str


def opaque_sample_id(list_entry: int) -> str:
    digest = hashlib.sha256(f"E001-terrain-v1:{list_entry}".encode()).hexdigest()[:12]
    return f"E001P-{digest}"


def terrain_provenance_id(
    terrain_year: str,
    source_resolution_m: str | float,
    survey_program: str,
) -> str:
    fields = (terrain_year, str(source_resolution_m), survey_program, EA_DTM_DATASET_ID)
    return "EAP-" + hashlib.sha256("|".join(fields).encode()).hexdigest()[:12]


def load_accepted_sites(path: str | Path) -> tuple[AcceptedSite, ...]:
    records = []
    with Path(path).open(encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row["review_status"] != "accepted":
                continue
            records.append(
                AcceptedSite(
                    list_entry=int(row["list_entry"]),
                    geographic_group_id=row["geographic_group_id"],
                    terrain_year=row["terrain_year"],
                    source_resolution_m=row["source_resolution_m"],
                    survey_program=row["survey_program"],
                )
            )
    if len(records) != 261 or len({record.list_entry for record in records}) != len(records):
        raise ValueError("accepted site catalogue must contain 261 unique approved records")
    return tuple(records)


def select_diverse_pilot(
    records: tuple[AcceptedSite, ...], *, count: int = 5, seed: str = "E001-Phase-2B-pilot-v1"
) -> tuple[AcceptedSite, ...]:
    if not 1 <= count <= 5:
        raise ValueError("pilot count must be between 1 and 5")
    ranked = sorted(
        records,
        key=lambda record: hashlib.sha256(f"{seed}:{record.list_entry}".encode()).hexdigest(),
    )
    chosen: list[AcceptedSite] = []
    used_groups: set[str] = set()
    used_years: set[str] = set()
    while len(chosen) < count:
        candidates = [record for record in ranked if record not in chosen]
        if not candidates:
            raise ValueError("not enough accepted records for the requested pilot")
        selected = max(
            candidates,
            key=lambda record: (
                record.geographic_group_id not in used_groups,
                record.terrain_year not in used_years,
                record.survey_program == "National LIDAR Programme",
            ),
        )
        chosen.append(selected)
        used_groups.add(selected.geographic_group_id)
        used_years.add(selected.terrain_year)
    return tuple(chosen)


def _request_json(parameters: dict[str, str]) -> dict[str, Any]:
    url = f"{NHLE_QUERY_URL}?{urllib.parse.urlencode(parameters)}"
    request = urllib.request.Request(url, headers={"User-Agent": "ArchaeoAI-terrain/1"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
        payload = json.load(response)
    if "error" in payload:
        raise RuntimeError(f"Historic England service error: {payload['error']}")
    return payload


def reconstruct_private_locations(
    accepted: tuple[AcceptedSite, ...],
) -> tuple[PrivateSiteLocation, ...]:
    by_id = {record.list_entry: record for record in accepted}
    found: dict[int, PrivateSiteLocation] = {}
    ids = sorted(by_id)
    for start in range(0, len(ids), 80):
        batch = ids[start : start + 80]
        payload = _request_json(
            {
                "where": f"ListEntry IN ({','.join(map(str, batch))})",
                "outFields": "ListEntry,Easting,Northing",
                "returnGeometry": "false",
                "outSR": "27700",
                "f": "json",
            }
        )
        for feature in payload.get("features", []):
            attributes = feature["attributes"]
            list_entry = int(attributes["ListEntry"])
            if list_entry in found:
                raise ValueError(f"duplicate official location record: {list_entry}")
            source = by_id[list_entry]
            found[list_entry] = PrivateSiteLocation(
                list_entry=list_entry,
                easting=float(attributes["Easting"]),
                northing=float(attributes["Northing"]),
                geographic_group_id=source.geographic_group_id,
                terrain_year=source.terrain_year,
                source_resolution_m=source.source_resolution_m,
                survey_program=source.survey_program,
            )
    if set(found) != set(by_id):
        missing = sorted(set(by_id) - set(found))
        raise ValueError(f"official locations missing for approved records: {missing}")
    return tuple(found[list_entry] for list_entry in ids)


def write_private_locations(
    locations: tuple[PrivateSiteLocation, ...], *, destination: Path, project_root: Path
) -> Path:
    output = ensure_private_output(project_root, destination)
    verify_git_ignored(project_root, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "e001-private-locations-v1",
        "warning": "CONTROLLED: exact locations; never commit or publish",
        "records": [asdict(location) for location in locations],
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output


def build_wcs_url(bounds: Bounds) -> str:
    parameters = [
        ("service", "WCS"),
        ("version", "2.0.1"),
        ("request", "GetCoverage"),
        ("coverageId", EA_DTM_COVERAGE_ID),
        ("format", "image/tiff"),
        ("subset", f"E({bounds.left:g},{bounds.right:g})"),
        ("subset", f"N({bounds.bottom:g},{bounds.top:g})"),
    ]
    return f"{EA_DTM_WCS_URL}?{urllib.parse.urlencode(parameters)}"


def fetch_wcs_payload(
    bounds: Bounds,
    *,
    maximum_bytes: int = 8 * 1024 * 1024,
    maximum_attempts: int = 4,
    timeout_seconds: int = 90,
    opener: Any = urllib.request.urlopen,
    sleeper: Any = time.sleep,
) -> WcsPayload:
    """Fetch one bounded GeoTIFF with retry accounting and response checks."""
    if maximum_attempts < 1:
        raise ValueError("maximum_attempts must be positive")
    request = urllib.request.Request(
        build_wcs_url(bounds), headers={"User-Agent": f"ArchaeoAI/{ACQUISITION_VERSION}"}
    )
    for attempt_index in range(maximum_attempts):
        attempts = attempt_index + 1
        retries = attempt_index
        try:
            with opener(request, timeout=timeout_seconds) as response:
                content_type = response.headers.get_content_type()
                if content_type not in {"image/tiff", "image/geotiff"}:
                    raise WcsRequestError(
                        "unexpected_content_type", attempts=attempts, retries=retries
                    )
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > maximum_bytes:
                    raise WcsRequestError("response_too_large", attempts=attempts, retries=retries)
                payload = response.read(maximum_bytes + 1)
                if len(payload) > maximum_bytes:
                    raise WcsRequestError("response_too_large", attempts=attempts, retries=retries)
                if content_length and len(payload) != int(content_length):
                    raise WcsRequestError("partial_response", attempts=attempts, retries=retries)
                if not payload.startswith((b"II*\x00", b"MM\x00*")):
                    raise WcsRequestError(
                        "invalid_geotiff_signature", attempts=attempts, retries=retries
                    )
                return WcsPayload(
                    content=payload,
                    sha256=hashlib.sha256(payload).hexdigest(),
                    size_bytes=len(payload),
                    attempts=attempts,
                    retries=retries,
                )
        except WcsRequestError as error:
            if error.reason != "partial_response" or attempts == maximum_attempts:
                if error.reason == "partial_response" and attempts == maximum_attempts:
                    raise WcsRequestError(
                        "retry_exhausted_partial", attempts=attempts, retries=retries
                    ) from error
                raise
        except HTTPError as error:
            if error.code not in RETRYABLE_HTTP_CODES:
                raise WcsRequestError(
                    f"http_{error.code}", attempts=attempts, retries=retries
                ) from error
            if attempts == maximum_attempts:
                raise WcsRequestError(
                    "retry_exhausted_http", attempts=attempts, retries=retries
                ) from error
        except (URLError, TimeoutError) as error:
            if attempts == maximum_attempts:
                raise WcsRequestError(
                    "retry_exhausted_network", attempts=attempts, retries=retries
                ) from error
        sleeper(min(8, 2**attempt_index))
    raise AssertionError("WCS retry loop terminated unexpectedly")


def download_wcs_geotiff(
    bounds: Bounds,
    *,
    destination: Path,
    project_root: Path,
    maximum_bytes: int = 8 * 1024 * 1024,
) -> tuple[Path, str, int]:
    output = ensure_private_output(project_root, destination)
    verify_git_ignored(project_root, output)
    output.parent.mkdir(parents=True, exist_ok=True)
    result = fetch_wcs_payload(bounds, maximum_bytes=maximum_bytes)
    output.write_bytes(result.content)
    return output, result.sha256, result.size_bytes
