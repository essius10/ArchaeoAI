"""Geometry and EA metadata helpers for the coordinate-safe E001 gate.

Exact coordinates and polygons are inputs only.  Returned summaries contain
status, broad provenance, and reason codes but no machine-ready locations.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError

EA_FEATURES_ROOT = (
    "https://environment.data.gov.uk/geoservices/datasets/"
    "9f0fa3fc-a860-4729-adc9-47fe53f658d0/ogc/features/v1/collections"
)
COMPOSITE_COLLECTION = "LIDAR_Composite_1m_DTM_2022_extents"
NLP_COLLECTION = "National_LIDAR_Programme_Index_Catalogue"
TIMESTAMPED_COLLECTION = "LIDAR_DTM_Time_Stamped_Extents"
BNG_CRS = "http://www.opengis.net/def/crs/EPSG/0/27700"


@dataclass(frozen=True, slots=True)
class GeometryQa:
    status: str
    reason: str | None
    area_ha: float | None
    part_count: int


@dataclass(frozen=True, slots=True)
class TerrainQa:
    coverage_status: str
    provenance_status: str
    reason: str | None
    year: str
    resolution_m: str
    programme: str
    acquisition_dates: str


def signed_ring_area(ring: list[list[float]]) -> float:
    return (
        sum(
            ring[index][0] * ring[(index + 1) % len(ring)][1]
            - ring[(index + 1) % len(ring)][0] * ring[index][1]
            for index in range(len(ring))
        )
        / 2
    )


def point_in_ring(point: tuple[float, float], ring: list[list[float]]) -> bool:
    x, y = point
    inside = False
    previous = ring[-1]
    for current in ring:
        x1, y1 = previous
        x2, y2 = current
        intersects = (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1
        if intersects:
            inside = not inside
        previous = current
    return inside


def esri_geometry_qa(
    geometry: dict[str, Any], *, centroid: tuple[float, float], area_ha: float | None
) -> GeometryQa:
    rings = geometry.get("rings") or []
    if not rings:
        return GeometryQa("needs_review", "geometry_missing", area_ha, 0)
    outer_rings = [ring for ring in rings if signed_ring_area(ring) < 0]
    if not outer_rings:  # tolerate services with opposite winding
        outer_rings = [max(rings, key=lambda ring: abs(signed_ring_area(ring)))]
    if len(outer_rings) != 1:
        return GeometryQa("fail", "geometry_compound", area_ha, len(outer_rings))
    if not point_in_ring(centroid, outer_rings[0]):
        return GeometryQa("fail", "geometry_off_centre", area_ha, 1)
    xs = [point[0] for point in outer_rings[0]]
    ys = [point[1] for point in outer_rings[0]]
    if area_ha is None or area_ha > 0.5 or max(xs) - min(xs) > 200 or max(ys) - min(ys) > 200:
        return GeometryQa("needs_review", "geometry_too_large", area_ha, 1)
    return GeometryQa("pass", None, area_ha, 1)


def patch_sample_points(
    centre: tuple[float, float], *, patch_size_m: float = 128
) -> list[tuple[float, float]]:
    half = patch_size_m / 2
    x, y = centre
    return [
        (x, y),
        (x - half, y - half),
        (x, y - half),
        (x + half, y - half),
        (x - half, y),
        (x + half, y),
        (x - half, y + half),
        (x, y + half),
        (x + half, y + half),
    ]


def _geometry_contains(geometry: dict[str, Any], point: tuple[float, float]) -> bool:
    coordinates = geometry.get("coordinates", [])
    polygons = coordinates if geometry.get("type") == "MultiPolygon" else [coordinates]
    return any(polygon and point_in_ring(point, polygon[0]) for polygon in polygons)


def assess_terrain_features(
    *,
    composite_features: list[dict[str, Any]],
    programme_features: list[dict[str, Any]],
    timestamped_features: list[dict[str, Any]],
    sample_points: list[tuple[float, float]],
) -> TerrainQa:
    relevant = [
        feature
        for feature in composite_features
        if any(_geometry_contains(feature.get("geometry", {}), point) for point in sample_points)
    ]
    if not relevant:
        return TerrainQa("fail", "not_reviewed", "terrain_no_1m_coverage", "", "", "", "")
    all_points_covered = all(
        any(_geometry_contains(feature.get("geometry", {}), point) for feature in relevant)
        for point in sample_points
    )
    if not all_points_covered:
        return TerrainQa("fail", "not_reviewed", "terrain_patch_incomplete", "", "", "", "")

    properties = [feature.get("properties", {}) for feature in relevant]
    signatures = {
        (
            str(prop.get("polygon_id") or ""),
            str(prop.get("year") or ""),
            str(prop.get("resolution") or ""),
            str(prop.get("sd_flown") or ""),
            str(prop.get("ed_flown") or ""),
        )
        for prop in properties
    }
    if len(signatures) != 1:
        return TerrainQa("pass", "needs_review", "terrain_provenance_confounded", "", "", "", "")
    polygon_id, year, resolution, start, end = next(iter(signatures))
    try:
        numeric_resolution = float(resolution)
    except ValueError:
        numeric_resolution = 999
    if numeric_resolution > 1:
        return TerrainQa("fail", "fail", "terrain_no_1m_coverage", year, resolution, "", "")

    nlp_ids = {str(f.get("properties", {}).get("polygon_id") or "") for f in programme_features}
    timestamped_ids = {
        str(f.get("properties", {}).get("polygonid") or "") for f in timestamped_features
    }
    source_dtm = str(properties[0].get("od_dtm_fn") or properties[0].get("filename") or "")
    if polygon_id in nlp_ids or source_dtm.casefold().startswith("np "):
        programme = "National LIDAR Programme"
    elif polygon_id in timestamped_ids:
        programme = "Time-stamped EA survey"
    elif source_dtm:
        programme = "EA Composite source survey"
    else:
        programme = "UNKNOWN"
    required = (polygon_id, year, resolution, start, end)
    if not all(required) or programme == "UNKNOWN":
        return TerrainQa(
            "pass",
            "needs_review",
            "terrain_provenance_missing",
            year or "UNAVAILABLE",
            resolution or "UNAVAILABLE",
            programme,
            f"{start or 'UNAVAILABLE'}--{end or 'UNAVAILABLE'}",
        )
    return TerrainQa("pass", "pass", None, year, resolution, programme, f"{start}--{end}")


def fetch_collection_bbox(
    collection: str, *, centre: tuple[float, float], patch_size_m: float = 128
) -> list[dict[str, Any]]:
    half = patch_size_m / 2
    x, y = centre
    params = {
        "bbox": f"{x - half},{y - half},{x + half},{y + half}",
        "bbox-crs": BNG_CRS,
        "crs": BNG_CRS,
        "limit": "100",
        "f": "json",
    }
    url = f"{EA_FEATURES_ROOT}/{collection}/items?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "ArchaeoAI-metadata-gate/1"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
                payload = json.load(response)
            break
        except HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 4:
                raise
            time.sleep(min(8, 2**attempt))
    return list(payload.get("features", []))


def fetch_terrain_qa(centre: tuple[float, float], *, patch_size_m: float = 128) -> TerrainQa:
    sample_points = patch_sample_points(centre, patch_size_m=patch_size_m)
    return assess_terrain_features(
        composite_features=fetch_collection_bbox(
            COMPOSITE_COLLECTION, centre=centre, patch_size_m=patch_size_m
        ),
        # The Composite index's ``od_dtm_fn`` identifies National Programme
        # versus other EA source surveys without two additional per-site calls.
        programme_features=[],
        timestamped_features=[],
        sample_points=sample_points,
    )
