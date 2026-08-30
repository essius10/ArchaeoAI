# ArchaeoAI current research status

ArchaeoAI E001 is a student-led, coordinate-controlled study of terrain-pattern classification for
documented bowl barrows. The frozen dataset contains **522 observations**: 261 curated
`positive_bowl_barrow` patches and 261 matched `unlabelled_background` patches.

## Verified evidence

| Evidence | Current result |
|---|---:|
| Preferred E001 model | Random Forest |
| Frozen geographic final balanced accuracy | **87.1%** |
| Five-fold geographic mean balanced accuracy | **82.3%** |
| Independent external evaluation | **84.17%**; 95% CI **77.5–90.0%**; n = 120 |
| External result classification | `EXTERNAL_GENERALIZATION_SUPPORTED` |

Phase 4A post-hoc external error analysis is complete. It is explicitly exploratory and does not
alter the confirmatory Phase 3C result. The independent external test is **spent**: it cannot be
reused for model selection, threshold changes, recalibration, or improvement of the currently
reported model.

Phase 4C classifies the coordinate-safe manuscript package as `READY_FOR_EXTERNAL_REVIEW`. This is a
draft suitable for serious independent feedback, not a publication or release. Citation identities
and claim fit have been checked, and public evidence has been clean-clone tested. Systematic
literature review, independent scientific/privacy review, full private-data reproduction, and
repository licensing remain unresolved before any release decision.

## Claim boundary

These results concern terrain classification within the frozen E001 and external-validation
designs. They are not archaeological probabilities, England-wide performance estimates, or
evidence of archaeological discovery. ArchaeoAI makes **no archaeological discovery claim**.
