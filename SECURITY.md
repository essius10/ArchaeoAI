# Security and responsible-data reporting

ArchaeoAI currently supports the latest state of the `main` branch only. This project does not yet
publish releases or deploy a service.

## Report privately

Do not open a public issue if a report contains:

- credentials, API keys, tokens, or private service URLs;
- sensitive archaeological coordinates or raw designation geometry;
- restricted-source data or a machine-ready archaeological location table;
- unreviewed potential-site or future model-prediction coordinates; or
- a path that could expose private local data.

Use GitHub's private vulnerability-reporting feature if it is enabled. Otherwise contact the
repository owner privately through their GitHub profile and include only enough non-sensitive detail
to establish contact. Do not attach the sensitive material until a safe channel is agreed.

If a credential may have been exposed, revoke or rotate it immediately. Removing it from the latest
commit is not sufficient because Git history and forks may retain it.

## Public reports

Ordinary bugs, reproducibility problems, documentation errors, and methodology questions that do
not contain sensitive information can use the repository's issue templates.

## Inference-result boundary

Phase 5A defines contracts only; no supported inference interface is deployed. Phase 5C later adds
an offline single-patch inspection and feature-contract CLI, but it is not a deployed or model-backed
inference service: its `infer` command fails closed without authorization and never executes the
private model. Any future public result must use the explicit serializer allowlist. Model identifiers accept only an approved enum
whose short lowercase alphanumeric/hyphen value is bound to its frozen configuration digest, while
warnings and limitations accept only approved controlled message codes with fixed coordinate-safe
rendering. Free-form strings, paths, URLs, nested containers, and custom objects must fail before
serialization. Private request metadata must never be traversed, logged, or copied into a public
result.

Phase 5D adds only bounded local batch feature preparation. Manifests accept a fixed schema,
opaque IDs, and relative POSIX terrain references contained beneath the manifest directory.
Symbolic links, traversal, absolute paths, duplicate IDs/references/content, oversized inputs, and
extra metadata fail closed. Batch output uses fixed aggregate fields and bounded opaque item
statuses; it excludes paths, coordinates, raster tags, feature values, timings, and model details.
The implementation reads admitted inputs in place, creates no temporary copies or hidden cache,
and performs no model execution. Reports involving a bypass of these controls should be handled as
private security reports.

The Phase 5A final review found and corrected a pre-deployment defect in the original free-form
warning/limitation fields. No real private data passed through that contract and no model-backed
public interface existed. A report showing a way around the corrected allowlist should be treated
as a private security report under the rules above.

## Scope

This policy covers software vulnerabilities and accidental data exposure. It is not a channel for
submitting possible archaeological discoveries. ArchaeoAI does not assess, publish, or recommend
visiting unreviewed locations.
