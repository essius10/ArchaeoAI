# Research charter

## Scope and claim boundary

The project evaluates computational mapping of **already documented** archaeological earthwork signatures in public terrain data. It does not identify new sites, advise field visits, or expose sensitive locations.

## Primary question

For a single, well-documented earthwork class and public LiDAR-derived digital terrain model (DTM) data in England, how do terrain representation choices and validation splits change performance relative to a simple elevation-only baseline?

## Hypotheses

- **H1:** Multi-scale, topographically justified derivatives improve geographic-holdout F1 and precision–recall AUC over raw elevation alone.
- **H0:** The representation choice produces no material improvement on the geographic holdout.
- **H2 (diagnostic):** Random tile splits overestimate performance relative to spatially grouped holdouts.

## Unit of analysis

Fixed-size terrain patches, centered on a documented feature or a matched negative location. Patches from a single spatial block must remain in exactly one split.

## Minimum evidence standard

- labels with auditable source and license;
- negatives matched by region, terrain, and acquisition characteristics where feasible;
- one held-out geographic area untouched until final evaluation;
- confidence intervals by spatial block, not independently sampled neighboring tiles;
- error review conducted without publishing sensitive coordinates.

## Explicit exclusions

No "site discovery" claim, no random-only validation result, no unlicensed labels, no synthetic-only conclusion, and no location list of possible unknown sites.
