# Phase 4D — external-feedback integration and RQ1 completion audit

Status: `RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW`

Audit date: 5 September 2026
Evidence cut-off: commit `3b978cd4a4805c27ea977a84894f1d40f2b5a24e`

## Scope and decision rule

This is an evidence-synthesis and review-readiness audit. It does not train, tune, score, relabel,
or rerun a model; reopen the spent external test; or change a frozen scientific artifact. The audit
uses only already recorded coordinate-safe evidence.

The authoritative RQ001 wording is in [research-questions.md](../research-questions.md):

> For one documented English earthwork class, how do terrain representations and random versus
> geographic splits change apparent baseline performance?

The [research charter](../research-charter.md) and
[E001 plan](../../experiments/E001_geographic_baseline.md) are compatible operational refinements:
they specify scheduled single bowl barrows, Environment Agency 1 m DTM terrain, an elevation-only
comparison, and the risk that a random split might overstate performance. They do not define a
different RQ1.

The audit assigns:

- `RQ1_ANSWERED_WITHIN_BOUNDED_SCOPE` only when the question's components are supported and the
  required independent scientific, privacy, reliability, and reproduction reviews are complete;
- `RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW` when the existing evidence supports a bounded answer
  but those external checks remain open; or
- `RQ1_REMAINS_OPEN` when essential empirical evidence is absent or incompatible with the question.

## Evidence-status vocabulary

These terms must not be collapsed:

| Status | Meaning | Current ArchaeoAI use |
|---|---|---|
| AI/model output | A model score, prediction, ranking, or AI-assisted draft; not archaeological evidence by itself | Phase 2F candidate-ranking outputs remain private and unreviewed |
| Hypothesis or candidate interpretation | A testable idea suggested by output or exploratory analysis | Phase 4A hypotheses are post-hoc and require new prospective tests |
| Human-vetted observation | A person has reviewed material under a stated procedure; this does not itself confer archaeological expertise or confirmation | No Phase 2F morphology review has occurred |
| Archaeologist-validated interpretation | A suitably qualified archaeologist has assessed the evidence; still not necessarily a confirmed site | None is claimed for new model-ranked candidates |
| Confirmed archaeological evidence | Corroborated evidence under an appropriate archaeological process, potentially including field investigation | No new evidence or discovery is claimed |

The E001 positive class consists of curated records for already documented monuments. Their
inventory status is not a project discovery, and the project's label-reliability review is still
pending.

## RQ1 evidence matrix

| RQ1 component | Design and frozen protocol | Evidence | Interpretation and limitation | Supporting artifacts |
|---|---|---|---|---|
| Archaeological and dataset scope | One class: curated scheduled, surviving single bowl barrows; 261 positives and 261 matched `unlabelled_background` observations | 522 E001 observations from England using 1 m DTM-derived terrain | Backgrounds are not confirmed negatives; labels and 40-record reliability sample await independent review | [dataset decision record](../dataset-decision-record.md), [Phase 2C report](../e001-phase-2c-background-and-splits.md) |
| Terrain representations | Five frozen inputs after deterministic 4×4 pooling: normalized elevation, slope, hillshade, local relief, and all four concatenated | On the 28-observation geographic development set, Random Forest balanced accuracy was 0.750000 for elevation and 0.821429 for all four; the latter was selected under the frozen rule | The 0.071429 difference is selection-stage evidence from 14 observations per class, without a confirmatory interval; it is not proof that all-four input is universally superior | [development protocol](../../configs/e001-phase-2d-a-preregistered.json), [development results](../../outputs/modelling/e001_phase_2d_a_development_results.json), [selected configuration](../../outputs/modelling/e001_primary_baseline_config.json) |
| Model selection and metric | Geographic-development balanced accuracy was primary; differences below 0.02 were ties; balanced accuracy handles the binary task symmetrically | All-four Random Forest scored 0.821429; runners-up hillshade and local relief scored 0.785714 | The choice was made before final-test access. No new selection occurs in Phase 4D | [Phase 2D methods](../e001-phase-2d-baseline-modelling.md), [claims register C009](../claims-register.md) |
| Random versus geographic split | Frozen group-aware random and complete-block geographic final partitions, evaluated once after selection | Random final balanced accuracy 0.822581; geographic final 0.870968; random-minus-geographic −0.048387 | In E001, the random split did **not** overstate the selected baseline; geographic was 0.048387 higher. This descriptive comparison is not evidence that geographic splits generally improve performance | [Phase 2D final protocol](../../configs/e001-phase-2d-b-final-protocol.json), [final results](../../outputs/modelling/e001_random_vs_geographic.json) |
| Uncertainty | Whole-group bootstrap for E001 final results; matched-pair bootstrap for the independent external evaluation | Geographic final 95% CI 0.774194–0.951613; random final 0.718750–0.916667. External balanced accuracy 0.841667, 95% CI 0.775–0.900, n=120 | Intervals describe the frozen samples and resampling units, not all English barrows or unknown terrain | [Phase 2D report](../e001-phase-2d-baseline-modelling.md), [Phase 3C result](../../outputs/external_validation/e001_phase3c_external_evaluation.json) |
| Confirmatory geographic evidence | One-way E001 geographic final test followed by a separately frozen external design and one-time evaluation of the unchanged model | Geographic final balanced accuracy 0.870968 (n=62); independent external balanced accuracy 0.841667 (n=120 across five pre-specified cells), classified `EXTERNAL_GENERALIZATION_SUPPORTED` | Supports transfer within the defined class, terrain source, sampling policy, regions, and model. It is not England-wide accuracy, calibrated archaeological probability, or discovery evidence. The external test is spent | [Phase 3A protocol](../../configs/e001-phase-3a-external-validation.json), [Phase 3C report](../e001-phase-3c-external-evaluation.md) |
| Robustness | Frozen score-independent five-fold post-hoc geographic assignments | Random Forest mean balanced accuracy 0.823406, range 0.790000–0.861111 | Post-hoc robustness contextualizes but does not replace the confirmatory result | [robustness protocol](../../configs/e001-phase-2e-a-robustness-protocol.json), [Phase 2E-A report](../e001-phase-2e-robustness.md) |
| Exploratory representation evidence | Representation sensitivity reused the fixed folds after the confirmatory evaluation | Local relief alone averaged 0.853577 versus 0.823406 for all four | Exploratory evidence cautions against a blanket all-four superiority claim; it cannot reselect the model | [robustness summary](../../outputs/robustness/e001_phase_2e_a_summary.json), [claims register C011](../claims-register.md) |
| Stronger-model check | One frozen compact CNN, same geographic folds, three seeds | CNN mean 0.700866 versus Random Forest 0.823406 | Post-hoc comparison only; it supports retaining the RF but does not generalize to all neural networks or model families | [CNN protocol](../../outputs/deep_learning/e001_cnn_protocol.json), [Phase 2E-B report](../e001-phase-2eb-compact-cnn.md) |
| Privacy | Exact coordinates, identifiers, terrain, row-level scores, candidates, and models remain private/ignored | Public artifacts contain aggregates, coarse groups, protocols, and hashes | Public verification cannot substitute for authorized private-data review | [privacy policy](../privacy-ethics.md), [reproducibility guide](../reproducibility.md) |
| Reproducibility | Frozen hashes and exact-value tests protect public evidence; Linux CPython 3.12 CI and Windows checks cover the public package | Coordinate-safe clean-clone checks pass; model-phase versions are recorded | Full private-data reproduction by an independent person has not occurred | [clean-environment audit](CLEAN_ENVIRONMENT_REPRODUCTION.md), [reproducibility guide](../reproducibility.md) |
| External review | Phase 4C prepared a reviewer packet and found it ready to request review | Citation identity and claim-fit audit completed; no independent review response is recorded | Ready for review is not peer reviewed, endorsed, or publication-ready | [readiness audit](READINESS_AUDIT.md), [reviewer guide](REVIEWER_GUIDE.md) |

## Bounded answer to RQ1

Within E001, representation choice changed development-stage apparent performance: for the same
Random Forest, the frozen all-four representation scored 0.821429 balanced accuracy versus
0.750000 for normalized elevation on the small geographic development partition. This supported
the pre-final selection but does not establish universal representation superiority; the later
post-hoc five-fold analysis in fact found local relief alone above all four, so that observation is
exploratory rather than a reason to revise the frozen model.

For the selected all-four Random Forest, the random final split scored 0.822581 and the geographic
final split 0.870968 (95% whole-group bootstrap CI 0.774194–0.951613). Thus, contrary to the initial
risk hypothesis, the random split did not overstate performance in this dataset; its balanced
accuracy was 0.048387 lower. The unchanged model then achieved 0.841667 balanced accuracy—reported
as **84.2%, 95% matched-pair bootstrap CI 77.5–90.0%, n=120**—on the one-time independent external
evaluation across five pre-specified geographic cells. That frozen result supports bounded
geographic transfer for documented bowl-barrow terrain versus matched unlabelled background under
this data and model design. The external test is spent.

This answer does not establish England-wide performance, archaeological detection in unknown
terrain, calibrated archaeological probabilities, superiority across model families, field
validation, or discovery.

## Completion decision

**`RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW`**

All empirical parts of the bounded question now have recorded evidence, including a negative
answer to the anticipated random-split overstatement and an independent external check. The answer
remains provisional because systematic literature completeness, independent scientific/privacy
review, the 40-record label-reliability review, and owner-independent private-data reproduction are
not complete. Representation comparisons beyond development are exploratory, not a new
confirmatory ablation.

## Remaining blockers

| Blocker | Phase 4D status | Advancement made | What closes it |
|---|---|---|---|
| Systematic literature-search completeness | Advanced but still open | A reproducible search-and-screening plan is now recorded in the citation audit | Execute and document searches, deduplication, eligibility decisions, and specialist gap review |
| Independent scientific and privacy review | Blocked by external human work | Reviewer guide now uses an explicit evidence-status vocabulary and links this audit | Receive and log qualified, conflict-declared review responses |
| 40-record reliability review | Blocked by external human work and private data | Its role in RQ1 uncertainty is explicitly recorded | Authorized independent review of the frozen 40-record sample with an auditable agreement summary |
| Private-data reproduction | Blocked by private data and external human work | Public/private reproduction boundaries and handoff requirements are explicit | Authorized owner-independent rerun without exposing restricted material |
| Archival dependency specification | Advanced but still open | Reproducibility guide now separates recorded scientific environments from a future archival lock | Create and independently test an archival environment specification without changing results |
| Licensing and derived-data redistribution | Requires owner decision and external/legal review | No licence or redistribution permission was inferred; existing audit remains controlling | Owner chooses a release path after provider-term and qualified legal/licensing review |
| External-review tracking | Advanced but still open | Structured feedback register created with source, response, evidence, and status fields | Log actual reviewer responses and dispositions without implying endorsement |

## Owner summary

RQ1 has a defensible, concise answer for the experiment that was actually run, but it should not
yet be labelled finally complete. Request independent review using the existing packet, complete
the 40-record reliability check and systematic search, and arrange an authorized private-data
reproduction before reconsidering the classification. No release, preprint, licence selection, or
new experiment is authorized by this audit.
