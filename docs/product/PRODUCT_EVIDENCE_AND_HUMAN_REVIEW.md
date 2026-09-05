# Product evidence and human review

## Controlling rule

The product must store evidence provenance and level explicitly. A machine may create only Levels
1–2. No score, threshold, rank, label, interface action, or report template may automatically
promote evidence to a human or archaeological level.

## Evidence ladder

| Level | Record | Created by | Minimum evidence | Permitted transition |
| ---:| --- | --- | --- | --- |
| 1 | `AI_OUTPUT` | Approved software runtime | Validated input, verified processing/model identity, raw bounded machine result, and audit event. | Software may propose Level 2 with explicit hypothesis wording; a human may retain, reject, or annotate it. |
| 2 | `AI_HYPOTHESIS` | Approved software under a frozen rule, or an authenticated human reframing Level 1 | Level 1 provenance plus a testable terrain-morphology hypothesis and mandatory limitations. | Requires human examination to reach Level 3; cannot skip levels automatically. |
| 3 | `HUMAN_VETTED_OBSERVATION` | Authenticated human reviewer | Reviewed source material, recorded method/category/rationale, date, identity, and conflicts/limitations. | Requires appropriate archaeological expertise and separate interpretation to reach Level 4. |
| 4 | `ARCHAEOLOGIST_VALIDATED_INTERPRETATION` | Authenticated, suitably qualified archaeological professional | Levels 1–3 provenance where relevant, relevant contextual evidence, professional rationale, attribution, and limitations. | Confirmation at Level 5 requires appropriate independent corroboration; software cannot perform it. |
| 5 | `CONFIRMED_ARCHAEOLOGICAL_EVIDENCE` | Authorized professional/institutional process, not the model | Corroboration appropriate to context, such as verified records, field investigation, or other accepted evidence, with accountable documentation. | Terminal evidence classification for this ladder; it does not imply planning approval or unrestricted publication. |

## Human and expertise transitions

- Level 1 → Level 2 may be deterministic software framing, but the record remains automatic and
  must say `AI_HYPOTHESIS`.
- Level 2 → Level 3 requires an authenticated human review action and a recorded rationale.
- Level 3 → Level 4 requires a suitably qualified archaeological professional acting within the
  project’s authorized scope.
- Level 4 → Level 5 requires appropriate corroboration and accountable professional or
  institutional confirmation; a visual terrain judgement alone is insufficient.
- Rejection, uncertainty, and “insufficient evidence” are first-class review outcomes. The system
  must not pressure reviewers to promote an item.

## Software prohibitions

The software must never automatically:

- create Levels 3–5 or imply that those reviews occurred;
- label a location an archaeological site, discovery, known negative, or safe area;
- interpret a score as archaeological probability or certainty;
- infer reviewer credentials, endorsement, consensus, or independence;
- overwrite machine provenance with a human label or merge distinct evidence records;
- use human annotations, candidate review, or the spent external test for retraining without a new
  scientific protocol and independent evaluation;
- publish candidate locations or promote them into public reports.

## Review record requirements

Every human action should record reviewer identity, role and claimed expertise, timestamp, material
reviewed, whether score/rank was visible, controlled category, notes, evidence level before/after,
supporting evidence references, conflicts/limitations, and supersession history. Corrections append
a new event; they do not erase the original record.

Review assignment and access must follow project permissions. A report may summarize the review
state only from attributed records and must identify unreviewed or disputed items explicitly.

## Product terminology

Preferred terms are **archaeological terrain screening**, **terrain-pattern similarity**,
**candidate terrain morphology**, **review prioritization**, **AI-generated hypothesis**, and
**human review required**. Model output is not an archaeological probability, discovery, planning
decision, construction clearance, or finding that no archaeology is present.

## Current research boundary

The existing Phase 2F packet remains privately prepared but unreviewed; it is not a product review
queue or evidence of Levels 3–5. E001 remains limited to documented bowl-barrow terrain versus
matched `unlabelled_background` under the evaluated geographic design. This product ladder does
not change any scientific result or the status
`RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW`.
