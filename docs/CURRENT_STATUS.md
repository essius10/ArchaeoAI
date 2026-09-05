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

Phase 4D has audited RQ001 against the frozen evidence and classifies it
`RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW`. Within E001, representation choice affected the small
geographic-development comparison, while the selected Random Forest's random final balanced
accuracy (82.3%) did not overstate its geographic final balanced accuracy (87.1%). The unchanged
model's 84.2% independent external result supports only the bounded transfer claim stated above.
The classification remains provisional pending systematic literature work, independent
scientific/privacy and label-reliability review, and authorized private-data reproduction. See the
[Phase 4D RQ1 audit](review/PHASE_4D_RQ1_AUDIT.md) and
[feedback register](review/FEEDBACK_REGISTER.md).

Phase 5A has completed a contract-only inference architecture audit. The repository is classified
`INFERENCE_CODE_READY_MODEL_ARTIFACT_UNAVAILABLE`: tested research inference code exists, and the
approved artifact is available only in authorized private storage, not in the public Git history.
The new contracts fail closed on invalid terrain metadata or a missing/changed model and prevent an
automatic result from claiming human review or archaeological confirmation. No model was loaded or
executed, no terrain was scored, and no CLI, API, website feature, deployment, or release was
created. See the [Phase 5 architecture](architecture/PHASE_5_INFERENCE_ARCHITECTURE.md).

## Claim boundary

These results concern terrain classification within the frozen E001 and external-validation
designs. They are not archaeological probabilities, England-wide performance estimates, or
evidence of archaeological discovery. ArchaeoAI makes **no archaeological discovery claim**.
