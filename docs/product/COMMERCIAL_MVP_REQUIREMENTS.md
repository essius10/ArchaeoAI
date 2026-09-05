# ArchaeoAI commercial MVP requirements

## Status

This document specifies a possible future MVP. It does not authorize implementation, model
execution, real-data ingestion, a pilot, Phase 5F, or public access.

## Bounded user journey

1. An authorized user creates a project with a defined purpose and accountable organization.
2. The user accepts applicable data, privacy, retention, and acceptable-use terms.
3. The user supplies terrain and project inputs they are authorized to process.
4. The system validates identity, permission, format, CRS, dimensions, resolution, size, and
   content before admission.
5. The system creates an auditable processing contract and accepts or divides terrain only through
   an explicitly approved tiling workflow.
6. The existing frozen terrain pipeline prepares the four representations and 4,096 features.
7. An approved model runtime may score patches only in an authorized deployment after artifact
   identity, configuration, and state checks succeed.
8. The system records bounded `AI_OUTPUT` or `AI_HYPOTHESIS` results using controlled terminology.
9. Hypotheses enter a permissioned review queue without becoming archaeological determinations.
10. A qualified human examines selected terrain and supporting evidence.
11. Human observations and archaeological interpretations remain separately attributed from AI
    output.
12. The system produces an auditable report containing scope, provenance, review state, and limits.
13. Sensitive inputs and derived data follow the project’s approved retention/deletion schedule.

## Capability classification

| Capability | Classification | Minimum requirement or reason |
| --- | --- | --- |
| Authentication | MVP REQUIRED | Strong individual identity; no anonymous processing. |
| Organization and project permissions | MVP REQUIRED | Least privilege with explicit project membership and reviewer roles. |
| Project workspace | MVP REQUIRED | Stable project purpose, owner, scope, status, and data-policy record. |
| Terms and authorization attestation | MVP REQUIRED | Record authority to process supplied data and accept handling conditions. |
| Authorized terrain ingestion | MVP REQUIRED | Controlled local import or private upload; strict type and size allowlist. |
| Raster validation | MVP REQUIRED | Preserve the Phase 5 canonical contract or use a separately approved preprocessing stage. |
| Bounded processing | MVP REQUIRED | Explicit quotas, isolation, deterministic job identity, and fail-closed admission. |
| Job status | MVP REQUIRED | Controlled states and error codes without paths, coordinates, or content leakage. |
| Approved model runtime | MVP REQUIRED for scored pilot | Disabled unless the private artifact, licence, deployment, and review gates pass. |
| Review queue | MVP REQUIRED | Permissioned, private, and clearly labelled as machine-generated hypotheses. |
| Human annotations | MVP REQUIRED | Authenticated author, timestamp, evidence level, rationale, and immutable history. |
| Evidence-level enforcement | MVP REQUIRED | Machines limited to Levels 1–2; higher transitions require appropriate humans. |
| Controlled output terminology | MVP REQUIRED | No discovery, probability, clearance, approval, or known-negative claims. |
| Report generation | MVP REQUIRED | Bounded report with provenance, AI/human separation, limitations, and audit references. |
| Audit history | MVP REQUIRED | Append-only security and decision events with sensitive-field minimization. |
| Retention and deletion | MVP REQUIRED | Project policy, expiry, verified deletion, legal-hold exception, and deletion evidence. |
| Export controls | MVP REQUIRED | Permissioned, reviewed exports; no public candidate-location export. |
| Multi-tenant managed SaaS | LATER | Requires a separate cross-tenant and public-service approval gate. |
| Automated reprojection/mosaicking | LATER | Must be an explicit, versioned preprocessing product with equivalence tests. |
| Integrations with HER/GIS/planning systems | LATER | Require source terms, authorization, field mapping, and leakage review. |
| Billing and payment | LATER | Commercial operations follow—not establish—workflow safety and demand. |
| Mobile field application | LATER | Requires location, offline-storage, and field-safety review. |
| Public API or public upload form | OUT OF SCOPE | Phase 5F is not authorized; anonymous location processing is unsafe. |
| Public candidate map or feed | OUT OF SCOPE | Conflicts with archaeological sensitivity and evidence boundaries. |
| Automatic archaeological decision or clearance | OUT OF SCOPE | Software must never make the final archaeological determination. |
| Automatic retraining or model substitution | OUT OF SCOPE | Would violate the frozen model and evidence boundary. |

## Core screen concepts

- **Projects:** only projects the authenticated user is permitted to access, with purpose, owner,
  retention state, and review status.
- **New screening project:** controlled scope and authorization capture followed by bounded terrain
  ingestion; no public map submission.
- **Processing:** safe job state, admitted/rejected counts, processing-contract identity, and fixed
  errors without private paths or coordinates.
- **Screening results:** private terrain-pattern-similarity hypotheses and aggregate summaries;
  never automatic “archaeological site” labels.
- **Review queue:** assigned human review with blinded or score-aware modes defined by protocol,
  controlled categories, and explicit evidence level.
- **Evidence record:** immutable separation of machine output, human observation, qualified
  archaeological interpretation, supporting sources, and any later confirmation.
- **Report:** permissioned preview/export of bounded findings, provenance, review status, and
  limitations.
- **Project settings:** membership, roles, retention/deletion, export permissions, and audit access.

These are information-architecture concepts, not frontend designs or implementation authorization.

## Professional report concept

A report should contain:

1. project identifier, accountable organization, purpose, and authorized scope;
2. input description, rights attestation, CRS/resolution, and data provenance;
3. processing contract, software version, model/config identity, and integrity checks;
4. terrain and representation QA with admitted/rejected aggregate counts;
5. screening summary using terrain-pattern-similarity terminology;
6. AI-generated hypotheses with their evidence level and controlled limitations;
7. human-review state, reviewer identity/role, method, and separately attributed observations;
8. archaeological interpretation only when supplied and signed by a qualified reviewer;
9. unresolved limitations, excluded uses, and recommended next professional step;
10. retention/deletion status and an audit-record reference.

The report must never translate a score into archaeological certainty, certify absence, grant
approval or clearance, or obscure whether qualified human review occurred.

## Acceptance boundary

An MVP is not credible merely because screens exist. Before use it must pass the Phase 6A decision
gates, threat/privacy testing, licensing review, model/IP decision, professional workflow review,
and a separately authorized bounded pilot. Phase 5E completion alone would not authorize it.
