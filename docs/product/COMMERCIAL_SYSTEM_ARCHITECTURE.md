# ArchaeoAI commercial system architecture

## Status and recommendation

This is a hypothetical Phase 6A architecture, not implementation or deployment authorization.
The recommended first deployment model is a **controlled local/private professional deployment**
inside an owner-approved environment. A managed cloud SaaS should remain a separate later decision
because sensitive locations, model protection, tenancy, uploads, and retention substantially
increase risk.

## Architectural rule: one inference path

The future product must orchestrate—not replace—the Phase 5 contracts:

```text
authorized input
→ Phase 5 input validation
→ frozen preprocessing and 4,096-feature contract
→ approved hash-bound model boundary (only when separately authorized)
→ safe result contract
→ evidence ladder
→ bounded batch primitives
→ authenticated human review and report
```

No “commercial” preprocessing, scoring, serializer, or evidence shortcut may run in parallel with
this path. Any new tiling, reprojection, model-loading, or persistence layer must sit outside the
canonical core, produce an auditable versioned input, and pass equivalence and privacy review.

## Logical components

| Component | Responsibility | Trust boundary |
| --- | --- | --- |
| Professional client | Project, authorization, upload/import, review, report, deletion controls. | Shows only projects and data permitted to the authenticated user. |
| Authenticated API or local service | Validates identity, role, project state, request schema, quotas, and idempotency. | No anonymous or cross-project access; no public inference endpoint. |
| Project metadata service | Stores purpose, organization, permissions, data-policy state, and workflow status. | Excludes terrain values and precise locations from ordinary metadata/logs. |
| Secure object storage | Holds authorized terrain and approved derived private material. | Project-scoped encryption, short-lived access, no public ACL, lifecycle deletion. |
| Job queue | Carries opaque project/job references and controlled states. | No paths, coordinates, feature vectors, scores, or raster bytes in messages. |
| Isolated terrain worker | Performs explicit preprocessing then calls the exact Phase 5 validation/feature path. | Sandboxed, resource-limited, minimal filesystem, no outbound network by default. |
| Isolated model runtime | Verifies approved artifact/config/state and scores canonical feature matrices. | Separate authorization; no pickle from users, retraining, fallback model, or internet download. |
| Results database | Stores private machine evidence, controlled status, and links to project-scoped geometry. | Row/project authorization; sensitive columns never exposed by generic queries. |
| Human-review application | Records assignments, blinded state, annotations, expertise, and evidence transitions. | Machine output cannot impersonate or promote a reviewer. |
| Report generator | Produces bounded, permissioned reports from verified records and templates. | No automatic certainty, clearance, discovery, or public candidate publication. |
| Append-only audit log | Records security and decision events with actor, time, object, action, and version. | Sensitive values minimized or tokenized; access itself is audited. |
| Retention/deletion service | Applies expiry, deletion, legal holds, and deletion evidence across stores/backups. | Failures alert owners; deletion is verified rather than assumed. |

In a local/private deployment these may be packaged into fewer processes, but the trust boundaries,
separate evidence records, least privilege, and audit requirements remain.

## Option A — Local/private professional deployment

| Dimension | Assessment |
| --- | --- |
| Security | Smaller exposed surface and easier network isolation; endpoint hardening and update discipline remain necessary. |
| Privacy/sensitive archaeology | Terrain and candidate locations can remain within the professional organization’s controlled environment. |
| Deployment complexity | Installation, hardware compatibility, upgrades, backups, and support must be standardized. |
| Maintenance | More version fragmentation; signed packages, supported versions, and upgrade evidence are required. |
| Model protection | Artifact can be delivered through a controlled channel and kept local, though a customer administrator may access it. |
| Customer usability | Lower upload burden and compatible with private workflows; setup may be less convenient than SaaS. |
| Auditability | Local append-only records and exportable signed reports are feasible; centralized visibility is limited. |
| Cost | Avoids permanent hosted infrastructure but creates installation and support cost; no cost claim is validated. |
| Scalability | Suitable for bounded professional pilots; constrained by local hardware and operational maturity. |

## Option B — Managed cloud SaaS

| Dimension | Assessment |
| --- | --- |
| Security | Adds internet exposure, authentication, tenant isolation, object storage, API abuse, secrets, and incident-response obligations. |
| Privacy/sensitive archaeology | Uploads and centralized candidate locations increase breach and jurisdiction risk. |
| Deployment complexity | Easier client access but materially harder secure platform engineering and compliance. |
| Maintenance | Centralized updates and observability are simpler, subject to safe telemetry and change control. |
| Model protection | Server-side runtime can limit artifact distribution, but infrastructure compromise could expose it. |
| Customer usability | Browser workflow may be easier if upload size, bandwidth, GIS interoperability, and trust are solved. |
| Auditability | Central policy enforcement is possible, but cross-tenant logs and support access require strong controls. |
| Cost | Ongoing compute, storage, egress, security, and support costs; no commercial estimate is established. |
| Scalability | Potentially greater, but only after quotas, isolation, scheduling, and operational controls are validated. |

## First-deployment conclusion

Begin, if later gates authorize it, with a single-organization local/private pilot: bounded projects,
named users, private storage, no public endpoint, no anonymous upload, and explicit deletion. This
reduces—not eliminates—risk and provides a setting for professional workflow evaluation. Success
would not authorize public SaaS; Option B requires a separate Gate H decision.

## Control and data flows

1. A project owner establishes purpose, access, data rights, retention, and reviewer roles.
2. Admission validates authorization before file parsing and applies byte/item quotas.
3. Untrusted raster parsing occurs in an isolated, resource-limited worker.
4. Accepted canonical patches use the exact Phase 5 transformation; derived features remain
   private and ephemeral unless a separately approved need is documented.
5. The model runtime remains disabled until the artifact/IP and deployment gates pass. When
   enabled, it accepts only canonical feature matrices and emits bounded Level 1 results.
6. Private results enter a project-scoped review queue. Human records are appended separately.
7. Reports are rendered from allowlisted fields, carry limitations, and are access-controlled.
8. Retention expiry removes inputs and derived sensitive data across stores and records evidence.

## Existing website reuse assessment

The static `website/` can later inform visual language, research explanations, geographic-
validation education, aggregate figures, and responsible-archaeology wording. It is a research-only
communication artifact today. Its private-run section reports only coordinate-safe aggregate
evidence and must not become a candidate browser, upload form, authentication shell, score viewer,
commercial promise, or model-backed inference interface without separate approval. Phase 6A makes
no website change and authorizes no deployment.

## Unresolved implementation decisions

Identity provider, authorization model, storage technology, worker sandbox, deployment packaging,
artifact format, audit immutability, backup deletion, report signing, and operational ownership are
intentionally undecided. They follow the decision gates and external review; they are not selected
by this architecture sketch.
