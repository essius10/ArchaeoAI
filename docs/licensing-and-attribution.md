# Licensing and attribution audit

## Current status

ArchaeoAI does **not** currently have a repository-wide licence. Under default copyright, public
visibility on GitHub does not by itself grant permission to reproduce, distribute, or modify the
original work. This is intentional while ownership and third-party attribution boundaries are made
explicit.

This document is a project recommendation, not legal advice.

## Material classes in this repository

| Material | Examples | Current treatment |
|---|---|---|
| Original software | `src/`, `scripts/`, `tests/` | No licence declared; default copyright |
| Original research prose | README, `docs/`, experiment protocol, research log | No licence declared; default copyright |
| Fictional templates | Example TOML configuration and manifest | Original project material; no licence declared |
| OGL-derived metadata summaries | Coordinate-free feasibility CSV/JSON outputs | Source terms and attribution continue to apply |
| External maps, polygons, terrain, and full datasets | Not tracked | Must remain outside Git unless a later review explicitly permits distribution |

No supplied Historic England map, raw NHLE polygon export, Environment Agency raster, or exact
archaeological coordinate table is committed.

## Third-party source obligations

The tracked feasibility artifacts contain filtered or aggregated information derived from Historic
England and Environment Agency sources offered under the
[Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
The OGL permits reuse but requires source acknowledgement, any provider-specified attribution, and
non-endorsement. It does not cover third-party rights that the provider is not authorised to license.

### Historic England

The [Historic England Open Data Hub terms](https://historicengland.org.uk/terms/website-terms-conditions/open-data-hub/)
specify:

- `© Historic England [year]`; and
- for spatial data, `Contains Ordnance Survey data © Crown copyright and database right [year].`

They also recommend stating data currency and prohibit implying Historic England endorsement. For
the current snapshot, use 2026 and state that the data was obtained on 27 August 2026. The source
ArcGIS item's displayed copyright wording differs from the terms page; preserve the provider notices
and seek clarification before distributing a derived dataset beyond these limited audit summaries.

### Environment Agency

The official 2022 LIDAR Composite DTM record identifies the Open Government Licence and the
attribution `© Environment Agency copyright and/or database right 2022. All rights reserved.` Keep
that provider statement, the OGL link, dataset identity, and access date with derived artifacts.

## Recommended licensing strategy

Do not add a single MIT-style licence over the whole repository yet. Instead, after confirming the
copyright holder name and contribution ownership:

1. License original Python and scripts under **Apache License 2.0**. Its explicit patent grant and
   notice mechanism are a good fit for reusable research software.
2. License original prose documentation under **Creative Commons Attribution 4.0**.
3. Keep OGL-derived tables and metadata under their source terms with exact Historic England,
   Ordnance Survey, and Environment Agency attribution; do not imply that Apache-2.0 covers them.
4. Add `LICENSES/` texts, a concise root `LICENSE` or `LICENSE.md` explaining the split, and SPDX
   identifiers or a file-scope table.
5. Require contributors to confirm that they have the right to submit their work. Consider a
   lightweight Developer Certificate of Origin only if outside contributions become substantial.

Before finalizing, confirm whether the repository owner wants personal-name or project ownership in
the notices and resolve the Historic England wording discrepancy recorded above. Until then, the
README must continue to say that no repository-wide licence has been applied.

## Attribution block for current audit outputs

Use this near any redistribution of the tracked feasibility results:

> Contains information derived from Historic England data obtained 27 August 2026. © Historic
> England 2026. Contains Ordnance Survey data © Crown copyright and database right 2026. Contains
> Environment Agency information © Environment Agency copyright and/or database right 2022. Source
> information is licensed under the Open Government Licence v3.0. Neither provider endorses this
> project or its interpretation.
