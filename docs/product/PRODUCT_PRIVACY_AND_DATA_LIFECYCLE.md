# Product privacy and data lifecycle

## Default policy

Collect the minimum data needed for a defined, authorized project; keep precise locations and
location-linked material private; exclude them from ordinary logs and analytics; apply short,
explicit retention; and publish no candidate location. This proposal requires privacy, legal, and
archaeological review before implementation.

## Lifecycle

```text
authorized input → validation → isolated processing → private derived data
→ permissioned review → bounded report → verified retention/deletion action
```

Validation failure should minimize retained content. Processing must not create undocumented
copies. Review and reporting must preserve machine/human provenance. Project closure triggers the
approved deletion schedule unless a documented legal hold applies.

## Data classification and proposed handling

“Project-private” means encrypted storage scoped to one authorized project. “Runtime-only” means
memory or a controlled workspace deleted at job completion. Exact durations are blockers for legal,
customer, and operational review; “project term” is not permission for indefinite retention.

| Data class | Sensitivity | Needed? | Proposed location | Proposed retention | Logs | Analytics | Public output |
| --- | --- | ---:| --- | --- | --- | --- | --- |
| Project metadata | Internal/confidential | Yes | Project-private metadata store | Project term plus agreed short closure period | Opaque IDs/status only | De-identified operational counts only, with consent | No, unless owner approves non-sensitive summary |
| Terrain raster | Highly sensitive, location-linked | Yes | Local/private encrypted object store or runtime-only | Minimum processing/review period; delete on schedule | Never | Never | Never |
| Coordinates | Highly sensitive archaeological/project data | Often | Separate project-private spatial store | Minimum review/report need | Never | Never | Never by default |
| Bounds/transforms | Highly sensitive, reversible location data | Processing only | Runtime-only or protected spatial store | Job duration unless review need is approved | Never | Never | Never |
| Derived terrain products | Highly sensitive, location-linked | Sometimes | Runtime-only by default; project-private if review requires | Short review period | Never | Never | Never |
| Feature vectors | Sensitive derived model input | Transiently | Runtime-only | Delete after scoring unless a justified audit requirement exists | Never | Never | Never |
| AI scores | Sensitive project result | Yes for review | Results store separated from public reporting | Project/report lifecycle, then delete or restricted archive | Never | Aggregate service health only; no location linkage | Aggregate only if approved |
| Candidate locations | Highest sensitivity | Yes for review | Separate project-private spatial store | Minimum professional-review need | Never | Never | Never by default |
| Reviewer annotations | Confidential professional evidence | Yes | Project-private evidence store | Report/audit period under agreed policy | Event type only | De-identified workflow counts only if approved | Only bounded attributed report content with permission |
| Final report | Confidential deliverable | Yes | Project-private document store and authorized recipient copy | Contractual/professional record period | Access event only | Never use content | Only with explicit owner/client and sensitivity approval |
| Model artifact | Restricted IP/security asset | Yes only in authorized scored deployment | Isolated runtime or controlled local installation | Supported deployment life; revoke obsolete versions | Digest/version only | Version counts only | Never |
| Audit records | Security/professional record; metadata-sensitive | Yes | Append-only access-controlled store | Defined compliance/contract period | This is the controlled log | Aggregate operational metrics only | Bounded audit excerpt only with authorization |

## Logging and analytics rules

Logs may contain authenticated actor token, opaque project/job ID, controlled event/error code,
software/model version, timestamps, and bounded resource counts where justified. They must exclude
coordinates, bounds, transforms, paths, filenames, raster metadata, feature values, scores,
candidate IDs reversible to location, annotation text, report contents, and credentials.

Analytics are off by default for a first private pilot. Any later analytics require purpose,
consent/legal basis, data minimization, aggregation thresholds, retention, access, and opt-out
review. Debug mode must not weaken the privacy boundary.

## Retention and deletion requirements

- Select and display a project policy before input admission; do not rely on an implicit default.
- Support early owner-requested deletion, scheduled expiry, and separately authorized legal holds.
- Delete primary objects, derived products, indexes, caches, temporary workspaces, queues, and
  eligible backups; document unavoidable backup expiry.
- Record deletion evidence without retaining deleted sensitive values.
- Revoke links, credentials, and worker access when a project closes.
- Test interrupted jobs, partial failures, support access, exports, and restoration paths.

## Public and export boundary

No public candidate-location publication is allowed. Exports require role authorization, an
explicit content preview, controlled terminology, sensitivity marking, and an audit event. Reports
must distinguish AI and human evidence and cannot transform a score into archaeological fact.

## Incident and subject handling

Before a pilot, define breach triage, owner/client notification, credential revocation, evidence
preservation, and archaeological-sensitivity escalation. Also define who can request access,
correction, export, or deletion and how conflicting professional-record obligations are resolved.
These are open governance requirements, not claims of current compliance.
