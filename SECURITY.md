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

## Scope

This policy covers software vulnerabilities and accidental data exposure. It is not a channel for
submitting possible archaeological discoveries. ArchaeoAI does not assess, publish, or recommend
visiting unreviewed locations.
