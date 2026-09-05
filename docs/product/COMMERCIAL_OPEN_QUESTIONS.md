# ArchaeoAI commercial open questions

## Status

This is a prioritized register of unresolved questions, not a set of assumed answers. `BLOCKER`
means the issue must be resolved for the relevant pilot or deployment; `IMPORTANT` means it should
shape design and approval; `LATER` means it is intentionally deferred beyond the first bounded
pilot.

| Category | Severity | Question | Why it matters | Owner/reviewer type needed |
| --- | --- | --- | --- | --- |
| Scientific | BLOCKER | What claims and use cases remain defensible when E001 covers one narrow class and bounded geographies? | Product wording and safe decisions cannot exceed evidence. | Research lead, statistician, archaeologist. |
| Scientific | IMPORTANT | What independent evidence would be required before evaluating another class, terrain source, or geography? | Prevents product pressure from becoming unregistered model expansion. | Research methodologist and archaeologist. |
| Archaeological | BLOCKER | Which screening decisions may the tool support, and which must remain solely professional? | Defines safe workflow, liability, and evidence transitions. | Qualified archaeological professional and legal adviser. |
| Archaeological | BLOCKER | What reviewer qualifications and corroboration are required for Levels 3–5? | Prevents software or unqualified review from implying validation. | Professional archaeology body/practitioner. |
| Archaeological | IMPORTANT | How should sensitive candidate locations be handled across clients, reports, regulators, and archives? | Disclosure may create heritage harm or breach obligations. | Archaeologist, data protection/privacy lead, client. |
| Product | BLOCKER | Which single professional job is valuable enough for a bounded pilot without implying automated determination? | A credible MVP needs a narrow user outcome. | Product researcher and prospective professional users. |
| Product | IMPORTANT | What evidence and interface context do reviewers need without anchoring them improperly to scores? | Review design affects bias, burden, and usefulness. | UX researcher, archaeologist, research methodologist. |
| Product | IMPORTANT | What pilot success criteria measure workflow value, safety, and auditability without reusing scientific tests? | Prevents metrics from overstating product or model performance. | Product owner, research lead, pilot partner. |
| Security | BLOCKER | Can untrusted raster processing be isolated and resource-bounded under the chosen deployment? | File parsing is a primary attack surface. | Security engineer and platform engineer. |
| Security | BLOCKER | Can the approved model be loaded without accepting arbitrary pickle risk or exposing the artifact? | Unsafe deserialization can compromise the host and model IP. | ML security engineer and model owner. |
| Security | IMPORTANT | What identity, authorization, support-access, and incident controls are proportionate for a private pilot? | Sensitive projects require accountable access. | Security architect and deployment operator. |
| Privacy | BLOCKER | What exact retention/deletion schedule applies to every sensitive data class, backups, and reports? | “Minimum retention” must become enforceable behavior. | Privacy/legal adviser, archaeologist, client records owner. |
| Privacy | BLOCKER | What lawful basis, notices, contracts, and jurisdiction apply to client terrain and location data? | Processing cannot begin without clear authority and obligations. | Data protection/legal adviser and client. |
| Privacy | IMPORTANT | Are any aggregated telemetry fields safe and genuinely necessary? | Operational visibility can accidentally disclose location or activity. | Privacy engineer and security reviewer. |
| Licensing | BLOCKER | Do all source terms permit the intended commercial processing, hosting, derived outputs, and client reporting? | Research permissions do not automatically establish commercial rights. | Licensing/legal specialist and data providers. |
| Licensing | IMPORTANT | What attribution and redistribution language must appear in reports and exports? | Deliverables must preserve source obligations. | Licensing specialist and report owner. |
| Model/IP | BLOCKER | Who owns the trained artifact and has authority to use, distribute, host, modify, and support it commercially? | The current private artifact cannot be assumed deployable. | Repository/model owner and IP counsel. |
| Model/IP | BLOCKER | Is a safer portable model format technically equivalent and legally acceptable? | Hash-bound pickle has code-execution risk; conversion could change outputs. | ML engineer, security engineer, research lead. |
| Infrastructure | BLOCKER | What local/private packaging and update mechanism preserves reproducibility, signatures, and rollback? | First deployment must be supportable without silent drift. | Platform engineer and security/reproducibility reviewer. |
| Infrastructure | IMPORTANT | How are append-only audit records and verified deletion implemented, including backups? | Accountability and privacy require both history and controlled erasure. | Platform engineer, security/privacy leads. |
| Infrastructure | LATER | What tenancy, regional hosting, availability, and disaster-recovery design would SaaS require? | These matter only after a separate public/SaaS decision. | Cloud architect, security/privacy/legal leads. |
| Business | BLOCKER | Will professional organizations participate in a bounded, paid or unpaid discovery/pilot process? | Technical readiness does not demonstrate demand. | Founder/product researcher and prospective users. |
| Business | IMPORTANT | Which delivery hypothesis—pilot, per-project, annual licence, private deployment, or enterprise contract—best fits procurement and risk? | Determines operations and product constraints; no price is assumed. | Business lead, procurement stakeholders, legal adviser. |
| Business | LATER | What pricing, support, insurance, and service-level model is viable? | These require real discovery and cost evidence. | Business/finance/legal leads. |
| Customer validation | BLOCKER | Do independent professionals understand and accept the terminology, evidence ladder, limitations, and required human work? | Misunderstanding would create unsafe reliance. | External archaeologists and consultancy users. |
| Customer validation | BLOCKER | Does the workflow improve prioritization or auditability in a real authorized project without displacing required review? | Core value remains unvalidated. | Pilot partner, independent evaluator, product researcher. |
| Customer validation | IMPORTANT | What objections, integration needs, and adoption barriers recur across different organization types? | Prevents designing from untested assumptions. | Product researcher and diverse prospective users. |

## Highest-priority blockers

The first five questions to resolve are:

1. the defensible professional use and claim boundary for narrow E001 evidence;
2. commercial source-data and derived-output rights;
3. model ownership, runtime authority, and safe artifact format;
4. enforceable security isolation and privacy retention/deletion for authorized inputs;
5. external professional acceptance of the human-review workflow and evidence ladder.

No blocker is resolved by repository documentation alone. Answers require attributable evidence and
must be carried into the corresponding commercial decision-gate record.
