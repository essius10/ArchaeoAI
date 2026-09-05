# ArchaeoAI preliminary commercial threat model

## Scope and status

This threat model identifies design risks for a possible professional product. It is not an
independent security assessment, penetration test, compliance claim, or deployment authorization.
Controls require validation before implementation and again before any pilot.

| Threat | Potential impact | Proposed control | Required validation/review before implementation |
| --- | --- | --- | --- |
| Malicious uploads | Parser compromise, data exposure, resource exhaustion. | Authenticate first; strict extension/MIME/magic allowlist; byte quotas; quarantine; isolated parsing. | Adversarial upload tests, sandbox review, incident procedure. |
| Malformed GeoTIFFs | Crash, unsafe parser behavior, misleading processing. | Preserve canonical fail-closed Phase 5 validation; patched Rasterio/GDAL; isolate process. | Fuzz corpus, dependency review, malformed-file regression tests. |
| Raster decompression/resource attack | Excess CPU, memory, disk, or service denial. | Inspect metadata before decode; dimension/band/compression limits; worker memory/CPU/time/disk quotas. | Decompression-bomb tests and measured worst-case limits. |
| Path traversal | Read/write outside project storage. | Server-generated object keys; no caller filesystem paths; Phase 5 containment and allowlists. | Traversal, encoding, platform-path, and archive tests. |
| Symlink or link attack | Escape workspace or substitute content. | Reject links; isolated non-shared workspace; recheck identity/hash immediately before use. | Race/link tests on supported filesystems. |
| Cross-tenant access | Exposure of terrain, locations, reports, or annotations. | Prefer single-organization first deployment; project-scoped authorization and encryption keys. | Tenant-boundary tests and independent authorization review before SaaS. |
| IDOR/broken authorization | User accesses another project by changing an identifier. | Deny-by-default object authorization on every request; opaque IDs are not authorization. | Role matrix, negative API tests, review of every object endpoint. |
| Data or coordinate leakage | Sensitive archaeology/project location becomes visible. | Separate spatial data; output allowlists; redacted errors; no coordinates in logs/analytics. | Privacy tests, tracked-file scan, report/export review. |
| Log/telemetry leakage | Persistent sensitive metadata in third-party or support systems. | Structured controlled events; field allowlist; analytics off by default; short retention. | Log-schema tests and processor/subprocessor privacy review. |
| Object-storage exposure | Public bucket/link reveals source or results. | Block public access; least-privilege service identities; short-lived scoped URLs; encryption. | Cloud/local configuration audit and access probes. |
| Report leakage | Confidential hypotheses or locations reach an unauthorized recipient. | Project permissions, sensitivity labels, preview, export audit, expiring delivery. | Report red-team review and recipient/access tests. |
| Model theft or substitution | IP loss, malicious scoring, invalid evidence. | Isolated runtime; controlled distribution; signed/hash-bound artifact/config/state; no download fallback. | Ownership/licence decision, artifact-chain review, tamper tests. |
| Malicious pickle/model loading | Arbitrary code execution. | Never accept user models; verify approved provenance before hash; prefer safer format if validated; isolated loader. | Serialization-format decision, code-execution threat test, independent security review. |
| Dependency compromise | Compromised parser/runtime or build artifact. | Locked dependencies, hashes/signatures, SBOM, minimal image, vulnerability/change monitoring. | Supply-chain review, clean reproducible build, update policy. |
| Prompt injection if an LLM is introduced | Untrusted text changes workflow, leaks data, or fabricates claims. | No LLM in decision path by default; isolate untrusted text; strict tools/output schema; no secret/data access. | Separate LLM threat model, adversarial evaluation, explicit owner gate. |
| Privilege escalation | Worker or user gains host/admin access. | Non-admin services, sandboxing, capability reduction, secrets isolation, patched host. | Host/container hardening review and penetration test. |
| Abusive large jobs | Denial of service or unexpected cost. | Preserve 64-item primitive; project quotas; admission control; sequential/bounded jobs; cancellation. | Load/abuse tests and cost/resource alarms. |
| Queue/retry replay | Duplicate reports, scoring, or retention beyond policy. | Idempotency keys, immutable job state machine, bounded retries, duplicate-content controls. | Failure/recovery and concurrent-state tests. |
| Unauthorized candidate scraping | Systematic extraction of sensitive ranked locations. | No public endpoint/map; role-limited views; pagination/export caps; access anomaly review. | Abuse-case review and enumeration tests. |
| Public exposure of sensitive archaeology | Harm to sites and violation of professional obligations. | Private-by-default outputs; sensitivity review; prohibit public candidate publishing. | Archaeological professional and privacy approval for every publication class. |
| Insider/support misuse | Authorized account accesses data without project need. | Least privilege, just-in-time support access, dual approval for sensitive exports, audit alerts. | Operational access review and tabletop exercise. |
| Credential/session compromise | Unauthorized project and report access. | Strong identity, MFA, short sessions, secure recovery, revocation, device/session visibility. | Authentication design review and session security tests. |
| Deletion failure | Data persists in cache, backup, queue, or failed workspace. | Data inventory, lifecycle jobs, verified cleanup, backup-expiry policy, deletion audit. | End-to-end deletion and restore-path tests. |

## Abuse controls

A future service needs named users, acceptable-use terms, project-purpose recording, authorization
attestation, request and storage quotas, concurrent-job limits, controlled export, anomaly handling,
account suspension, and a private incident channel. These controls do not permit public or
unbounded scanning and must not rely on secrecy of identifiers.

## Trust assumptions to challenge

The first design assumes an owner-approved model, lawfully supplied terrain, an authenticated
professional organization, qualified reviewers, a patched trusted runtime, and a deployment
operator capable of enforcing deletion. Each assumption needs evidence at the applicable decision
gate. Failure or ambiguity is a stop condition, not a reason to silently degrade controls.
