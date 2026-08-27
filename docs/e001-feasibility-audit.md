# E001 Phase 2A — bowl-barrow feasibility audit

## Decision

**CONDITIONAL GO.** Official metadata provides strong evidence that scheduled, single bowl
barrows can support a student-scale E001 experiment. The title-derived pool is much larger than
the planning target and is widely distributed. This is not yet a final label set: full-entry
review, geometry QA, and terrain-provenance checks remain mandatory before Phase 2B.

This audit was performed on 27 August 2026. It downloaded no LiDAR, retained no raw NHLE export,
and wrote no exact coordinates or geometry to tracked output.

## 1. Official NHLE source

Historic England's [listing-data download page](https://historicengland.org.uk/listing/the-list/data-downloads)
links to the official [National Heritage List for England Open Data Hub item](https://opendata-historicengland.hub.arcgis.com/datasets/historicengland::national-heritage-list-for-england-nhle/explore?layer=6).
The audit queried layer 6, `Scheduled Monuments`, from the official hosted
[ArcGIS Feature Service](https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer/6).

Verified service properties at access time:

| Property | Finding |
|---|---|
| ArcGIS item ID | `767f279327a24845bf47dfe5eae9862b` |
| Layer | 6, `Scheduled Monuments` |
| Geometry | ArcGIS polygon, EPSG:27700 |
| Update information | Parent item says data is updated daily; live layer last-edit timestamp was 27 August 2026 05:59 UTC |
| API query formats | JSON, GeoJSON, PBF |
| Service export formats | CSV, Shapefile, SQLite, GeoPackage, File Geodatabase, feature collection, GeoJSON, KML, Excel |
| Public access | No authentication was required for metadata queries |

The live layer contained **20,002 feature records and 20,002 unique List Entry Numbers**. No
duplicate designation IDs were found. Historic England's separate public search interface showed
19,998 scheduling results in its indexed response, four fewer than the live layer. The likely
cause is update timing, but that was not verified. This audit therefore binds its counts to the
named service and access timestamp and requires a rerun before label curation. The total is not a
timeless count and not a count of bowl barrows.

### Scheduled Monuments schema

| Field | Meaning | Type |
|---|---|---|
| `OBJECTID` | Service feature identifier | OID |
| `ListEntry` | Stable NHLE List Entry Number | Integer |
| `Name` | Statutory registered monument title | String |
| `SchedDate` | Date first scheduled | Date |
| `AmendDate` | Most recent amendment date | Date |
| `CaptureScale` | Scale used for spatial capture | String |
| `hyperlink` | Official NHLE list-entry link | String |
| `area_ha` | Designation polygon area in hectares | Double |
| `NGR` | Centroid National Grid Reference | String |
| `Easting` | Centroid easting | Double |
| `Northing` | Centroid northing | Double |

The layer has **no monument-type, survival-condition, description, county, or archaeological-period
field**. `Name` is the only bulk text useful for class identification. The linked official list
entry normally contains `Reasons for Designation` and `Details`, but those descriptions are not
part of the downloadable layer schema. Consequently, strict inclusion cannot be automated from
the feature layer.

## 2. Reproducible title triage

The data-free audit logic lives in `src/archaeoai/nhle_audit.py`; the networked runner is
`scripts/audit_nhle_bowl_barrows.py`.

The runner:

1. asks the service for the total Scheduled Monument record count;
2. fetches only records where the statutory title contains `barrow`;
3. uses `ListEntry`, `Name`, `CaptureScale`, polygon area, and centroid metadata transiently;
4. conservatively partitions titles into probable, clearly excluded, and manual-review queues;
5. aggregates geography to 100 km British National Grid cells; and
6. discards all exact coordinates and source records after writing the aggregate result.

A `probable_bowl_candidate` must contain the exact singular phrase `bowl barrow` and no obvious
title warning for multiple monuments, another barrow type, a cropmark/survival problem, or a
compound designation. `clear_title_exclusion` is limited to titles without an exact singular bowl
barrow that explicitly identify multiple monuments or a non-target class such as a long, bell,
disc, saucer, platform, pond, oval, or bank barrow, cairn, cropmark, or ring ditch. Everything else,
including generic `round barrow` titles, enters `manual_review_required`.

These are triage categories, not archaeological labels. A probable candidate still requires the
full official entry to confirm one monument, bowl-barrow identity, upstanding survival, and usable
geometry.

## 3. Verified counts

| Audit stage | Count |
|---|---:|
| Total distinct Scheduled Monument records examined by the service query | 20,002 |
| Broad titles containing `barrow` | 5,487 |
| Probable singular bowl-barrow title candidates | 1,908 |
| Clear title exclusions | 1,826 |
| Title-level manual review required | 1,753 |

The last three rows partition the 5,487 broad candidates. The count of 1,908 is a **review queue**,
not a final usable-positive count. No claim is made that all, or any fixed proportion, will pass
terrain coverage and archaeological QA.

Coordinate-free results are in
`outputs/feasibility/bowl_barrow_summary.json` and
`outputs/feasibility/bowl_barrow_counts.csv`.

## 4. Manual sample audit

Thirty probable-title records were selected by sorting SHA-256 hashes of a fixed seed and stable
List Entry Number. The seed is `E001-Phase-2A-2026-08-27`. Each linked official list entry was read;
precise locations were not copied into the review artifact.

| Review outcome | Count | Meaning |
|---|---:|---|
| Clear include | 25 | One bowl barrow with an explicitly surviving mound or visible rise |
| Clear exclude | 3 | One levelled cropmark, one mound no longer visible, and one feature described as a cairn |
| Uncertain | 2 | Surface relief was unspecified or described as only just visible |

This is an 83% clear-include result within a small sample drawn only from the most promising title
queue. It must not be treated as a population estimate. It does show that the title rule finds many
genuine examples while also demonstrating that full-text review changes labels.

All 30 sample designations used 1:10,000 capture scale and compact polygons approximately
0.019–0.181 ha. The descriptions generally provide mound dimensions and the entries say their map
extract includes a small boundary around the archaeological feature. This makes the geometry
provisionally useful for locating the monument, but not a segmentation mask or automatically valid
patch centre. The coordinate-free review decisions are recorded in
`outputs/feasibility/bowl_barrow_manual_sample.csv`.

## 5. Geographic viability

Probable title candidates occurred in **23 coarse 100 km grid cells**; **20 cells** contained at
least 25 probable candidates. The 30-record manual sample covered 20 distinct county or unitary-
authority labels in the official entries.

This comfortably exceeds the preliminary request for evidence of eight groups and three distinct
landscape settings. It does not define the E001 split. The 100 km cells are privacy-safe feasibility
aggregates, not final spatial blocks, and adjacent cells are not automatically independent.

The 1,908-title review queue would need a final yield of only about 13% to produce 250 positives.
That arithmetic, together with the manual sample and broad distribution, supports feasibility but
does not verify that 250 usable positives exist. Terrain coverage, survey confounding, duplicate
complexes, and manual review can still reduce the set.

## 6. Geometry findings

All 5,487 broad candidates had centroid metadata in the live layer; coordinates were used only in
memory to calculate coarse aggregate cells. Among the 1,908 probable-title candidates:

- 1,883 polygons were captured at 1:10,000;
- 17 at 1:2,500;
- 5 at 1:1,250; and
- 3 at 1:5,000.

Probable polygon areas ranged from about 0.008 ha to 2.115 ha, with a median of about 0.063 ha. The
large upper outlier is another reason to review geometry rather than infer that a title describes a
compact, single mound.

Historic England's [Open Data Hub terms](https://historicengland.org.uk/terms/website-terms-conditions/open-data-hub/)
state that spatial data is provided solely to indicate the location of the area and is licensed
as-is. E001 must visually verify the feature centre and reject compound, off-centre, or unusually
large geometries before any terrain extraction.

## 7. Environment Agency terrain metadata

The official candidate is the Environment Agency
[LIDAR Composite Digital Terrain Model (DTM) — 1 m](https://www.data.gov.uk/dataset/01b3ee39-da3f-47b6-83da-dc98e73a461f/lidar-composite-digital-terrain-model-dtm-1m).

Verified properties:

| Property | Finding |
|---|---|
| Publisher | Environment Agency |
| Licence | Open Government Licence |
| Nominal product resolution | 1 m |
| Coverage | Approximately 99% of England |
| CRS | EPSG:27700 |
| Vertical reference | Metres relative to Ordnance Datum Newlyn, using OSTN15 |
| Raster format | GeoTIFF in 5 km OS National Grid tiles |
| Source period | Surveys from 6 June 2000 to 2 April 2022 |
| Processing warning | Composite chooses newer/better-resolution surveys and includes bilinear resampling |
| Access mechanisms | Survey download plus WMS, WMTS, and WCS services |

Survey provenance is practically queryable without downloading national terrain. The official
[Defra OGC Features collection](https://environment.data.gov.uk/geoservices/datasets/9f0fa3fc-a860-4729-adc9-47fe53f658d0/ogc/features/v1/collections/LIDAR_Composite_1m_DTM_2022_extents)
uses EPSG:27700 and exposes `filename`, `tilename`, `polygon_id`, `resolution`, `year`, source DTM
filename, survey start date, survey end date, and polygon geometry. A later private audit can query
this index by candidate point or small bounding box to determine coverage and survey provenance.
The WCS can later request bounded terrain subsets, while the 5 km tile downloader remains an
alternative. Neither was used in Phase 2A.

## 8. Licensing and privacy

Historic England licenses Open Data Hub datasets under OGL v3 for commercial and non-commercial
use. Its terms require:

> © Historic England [year]

and, for spatial data:

> Contains Ordnance Survey data © Crown copyright and database right [year].

Reuse must state data currency, must not imply Historic England endorsement, and must comply with
laws protecting archaeological sites. The terms permit derived and filtered metadata under OGL,
subject to attribution and equivalent attribution in sublicensing. Official list-entry text also
states that its text is OGL unless noted otherwise; supplied maps carry separate Ordnance Survey
rights and were not copied.

The ArcGIS item itself currently displays `© Crown Copyright 2026` rather than the terms page's
`© Historic England [year]`. That wording discrepancy should be clarified with Historic England or
both notices preserved before releasing a derived label table.

The Environment Agency catalogue identifies the terrain dataset as OGL and provides the notice
`© Environment Agency copyright and/or database right 2022. All rights reserved.` E001 should
retain that notice together with the OGL reference and access date. The apparent coexistence of
`All rights reserved` and OGL should not be reinterpreted without publisher guidance.

Repository privacy controls for this audit:

- no NHLE coordinates, NGRs, geometries, or raw exports are tracked;
- the script uses centroid values transiently only for 100 km aggregate counts;
- tracked sample notes use stable public record IDs without copying coordinates or maps;
- no unrecorded-site prediction or candidate-location map exists; and
- later exact labels must remain in `data/private/`, outside Git.

## 9. Conditional-GO conditions

Phase 2B remains blocked until all of the following are complete:

1. Freeze a full-entry inclusion rubric and a reviewer decision schema.
2. Manually review a geographically stratified pool sufficient to obtain at least 250 high-quality
   records, without assuming the current sample yield will hold.
3. Independently double-review a subset and resolve disagreements.
4. Privately validate each polygon/centroid against the official map and reject compound or
   off-centre geometry.
5. Query the EA survey index for every retained candidate and verify 1 m DTM coverage, source
   resolution, dates, and acquisition group.
6. Demonstrate at least eight viable independent geographic groups after label and terrain QA.
7. Check that label class and proposed holdouts are not confounded with survey year, resolution,
   capture scale, preservation context, or one dominant landscape.
8. Select at least two nonadjacent final test groups, without finalizing block size until patch
   footprint and spatial autocorrelation can be assessed.
9. Finalize Historic England and Environment Agency attribution wording and the controlled-data
   publication policy.
10. Change D001 from conditional to approved only when the audited private label manifest records
    these checks.

No raster pipeline, terrain download, negative sampling, or model work should begin before these
conditions are met.

## Reproduction

From the installed Phase 1 environment:

```powershell
.\.venv\Scripts\python.exe .\scripts\audit_nhle_bowl_barrows.py
```

The command requires network access to the official ArcGIS service. It overwrites only the two
coordinate-free generated summaries. Tests do not require network access.
