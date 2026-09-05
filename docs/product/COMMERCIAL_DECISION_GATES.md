# ArchaeoAI commercial decision gates

## Rule

Every gate starts **NOT COMPLETED**. Evidence and an accountable decision must be recorded; absence
of a concern is not approval. A gate may be `GO`, `GO WITH CONDITIONS`, or `NO-GO`. A later gate
cannot override an unresolved blocker in an earlier gate.

## Gate A — Scientific integrity

Confirm claims remain limited to E001’s documented bowl-barrow terrain versus matched
`unlabelled_background`, evaluated geographies, and stated uncertainty. Scores remain terrain-
pattern similarity, not archaeological probability. No discovery, absence, clearance, universal
generalization, or automatic professional determination is implied.

**Minimum evidence:** claims-register audit, frozen-artifact diff, terminology review, and
documented confirmation that the spent external test was not reused.

## Gate B — Phase 5E review

Appropriate external reviewers examine security, privacy, archaeological/scientific workflow, and
licensing/data/model issues using the Phase 5E checklist. Substantive findings receive documented
resolution or an explicitly accepted residual risk appropriate to the intended deployment.

**Current state:** **NOT COMPLETED.** Phase 6A does not complete it or authorize Phase 5F.

## Gate C — Data licensing

Verify commercial-use, hosting, transformation, derived-output, attribution, redistribution, and
deletion rights for every proposed data source and customer-supplied input. Resolve jurisdiction,
contract, and source-version differences.

**Stop if:** a required right or attribution obligation is unclear or incompatible.

## Gate D — Model/IP

Establish ownership, authority to use commercially, distribution restrictions, approved runtime
location, artifact format, provenance, integrity/state verification, and protection/support policy.

**Stop if:** ownership or redistribution/runtime authority is unclear, or safe loading cannot be
demonstrated.

## Gate E — Real-input authorization

For any pilot, record project purpose, data provider, rights/consent, geographic scope, responsible
organization, privacy/retention terms, and ethical authority before admission.

**Stop if:** authorization is missing, overly broad, unverifiable, or conflicts with archaeological
sensitivity.

## Gate F — Professional workflow review

At least one appropriate external domain professional reviews the intended user journey,
terminology, evidence ladder, review burden, report, and escalation process. Their role, scope,
conflicts, limitations, findings, and dispositions must be recorded without implying endorsement.

**Current state:** no completion is claimed by this design.

## Gate G — Pilot authorization

Only after Gates A–F are sufficiently resolved may the owner separately authorize a bounded pilot.
The decision must name the deployment, organization, users, inputs, model, limits, monitoring,
retention, support, stop conditions, and success criteria. A pilot is not general release.

## Gate H — Public/SaaS decision

A local/private pilot does not authorize public SaaS. Internet access, uploads, multitenancy,
central storage, telemetry, public interfaces, scaling, incident response, and abuse controls need
a separate architecture, threat/privacy review, professional review, and explicit owner approval.

## Decision record template

- Gate and date:
- Decision: `GO` / `GO WITH CONDITIONS` / `NO-GO`
- Accountable owner:
- Reviewers and scope (no endorsement implied):
- Evidence reviewed:
- Findings and unresolved risks:
- Required actions, owners, and deadlines:
- Deployment or activity explicitly authorized:
- Activities explicitly not authorized:
- Re-review trigger:

## Current authorization boundary

Phase 6A authorizes documentation and architecture discussion only. It authorizes no model loading,
real terrain processing, customer-data storage, pilot, Phase 5F work, public interface, deployment,
commercial claim, or candidate publication.
