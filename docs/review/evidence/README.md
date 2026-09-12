# Phase 5E external-review evidence

This directory is reserved for completed, public-safe, attributable Phase 5E review records. It
currently contains **no completed review evidence**. Its existence does not advance the Phase 5E
gate.

Copy `../templates/phase5e_review.template.json` outside the repository, replace every template
value, set `record_status` to `COMPLETE`, and validate it before proposing it for inclusion:

```powershell
python scripts/validate_phase5e_review.py --review path/to/completed-review.json
```

The template includes one illustrative placeholder finding so every required field is visible.
Replace it for a real finding, add further findings with unique IDs, or remove the object and use an
empty `findings` list only when the review genuinely found none.

Each record covers exactly one review domain and one reviewed commit. A reviewer may use an agreed
stable public attribution; private contact details are neither required nor permitted in a tracked
record. The owner privately verifies attribution and preserves any necessary correspondence outside
Git.

Do not commit exact archaeological locations, terrain, model bytes, credentials, exploitable
details, private correspondence, or unnecessary personal information. For a sensitive finding,
prepare a redacted public finding and give its sensitive evidence an owner-controlled opaque
reference. Arrange private transfer directly with the owner through an already agreed channel; the
repository intentionally invents no public contact route. Public GitHub issues are not suitable for
sensitive evidence.

The validator rejects blank templates, placeholder values, malformed domains or findings, missing
declarations, and prohibited private-data fields. A structurally valid record is evidence of what
the attributed reviewer declared; it is not proof of reviewer identity, institutional endorsement,
archaeological truth, or legal compliance.
