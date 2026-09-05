# 2026-09-05 — Phase 5A public-serialization correction

## Review finding

The final Phase 5A review found a substantive defect in the first public-result contract. Python
type annotations did not prevent arbitrary runtime objects in `warnings` and `limitations`, and
`model_identifier` required only non-whitespace content. Fictional probes demonstrated that path
strings, nested mappings, lists, custom objects, and unsupported archaeological-claim language
could be copied into the public payload.

## Correction

The result now accepts only required `WarningCode` and `LimitationCode` tuples, renders them through
fixed coordinate-safe messages, rejects duplicate or missing safety codes, and restricts the model
identifier to an approved enum with a 1–64 character lowercase alphanumeric/hyphen value. The enum
is bound to its exact frozen configuration digest. Evidence level, score, digest, and
private-metadata container types are also checked at runtime. Serialization remains a flat,
explicit eight-field allowlist and never traverses private metadata.

Adversarial regression tests cover Windows and POSIX paths, path-like and URL identifiers,
whitespace and control characters, overlong identifiers, nested mappings, lists of dictionaries,
custom objects, unsafe claim text, valid identifiers, deterministic output, JSON safety, and exact
field membership.

## Boundary preserved

This correction did not load or execute a model, deserialize an artifact, process terrain, train,
tune, score, reuse the spent external test, or change a frozen scientific result. No CLI, API,
website feature, deployment, release, or Phase 5B work was started. The finding occurred before any
public inference interface existed and did not expose real private data.
