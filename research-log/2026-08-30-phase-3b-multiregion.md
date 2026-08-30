# 2026-08-30 — Phase 3B multi-region external dataset construction

## Scope

Resume Phase 3B after the frozen R1 amendment, curate the 33 supplementary probable-title
records under the unchanged evidence rules, and construct the external dataset without model
access.

## Curation

Official Historic England full entries were reviewed before terrain construction. The
supplementary decisions were 29 accepted, two rejected, zero uncertain, and two requiring terrain
review. Combined with the 47 locked first-region acceptances, the eligible pool contained 76
records. The frozen Phase 3A SHA-256 selection selected exactly 60; no record was chosen from model
output or terrain resemblance.

## Dataset construction

One deterministic `unlabelled_background` was matched to every selected positive using the frozen
annulus, cell, provenance, known Scheduled Monument, positive-buffer, and background-spacing rules.
All final observations received bounded 128 m × 128 m Environment Agency 1 m DTM windows and the
four unchanged terrain representations. Technical QA alone governed acquisition; no morphology
review was performed.

The private audit checked all 522 E001 centres, the Phase 2F private domain, sample and centre
collisions, terrain-window overlap, exact patch content, matched-pair structure, and the 15 km
exclusions. Coordinates, record-level labels, GeoTIFFs, NPZ archives, and the private manifest are
ignored by Git. The tracked receipt contains coordinate-safe aggregates and binds the private
manifest and canonical dataset digest.

The audit recorded five internal positive-to-positive window overlaps. These do not violate the
frozen protocol. The Phase 3A disjoint-window rule is part of the 15 km prior-study boundary and is
implemented as no E001-patch or Phase 2F-domain overlap; its background rules separately require
500 m positive-to-background and 256 m background-to-background spacing, with no positive-to-positive
exclusion. The five pairs have distinct centres, IDs, and content checksums and were retained under
the performance-blind selection rule.

## Decision

Final status: `READY_UNSCORED` with 60 positive observations, 60 matched
`unlabelled_background` observations, and 120 observations total.

The Random Forest was not loaded. Neither `predict()` nor `predict_proba()` was called. No external
performance metric was calculated. Phase 3C remains the only phase authorized to score this
dataset.
