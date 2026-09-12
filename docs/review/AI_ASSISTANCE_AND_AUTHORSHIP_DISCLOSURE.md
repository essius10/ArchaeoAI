# AI assistance and authorship disclosure

Status: `PUBLIC_SAFE_DISCLOSURE_READY`

This disclosure consolidates the human, external-expert, generative-AI, and automated-tool roles in
ArchaeoAI. It is based on the tracked research logs and decision history. It is not a claim that an
independent review has occurred, and it does not assign authorship under any journal's policy.

## Summary

ArchaeoAI is owner-directed and materially generative-AI-assisted. The project owner originated and
pursued the project direction, set priorities and authorization boundaries, communicated with
outside academics, decided which proposed phases and changes could proceed, reviewed deliverables,
and retains responsibility for material accepted into the repository. Generative AI—principally
identified in the project record as OpenAI Codex—made substantial contributions to planning,
implementation, analysis workflows, testing, documentation, and drafting.

It would be inaccurate to claim that the owner manually wrote every line of code or independently
conceived every implementation and methodological choice. It would also be inaccurate to describe
AI-generated work as independent scientific or archaeological review.

## A. Human and project-owner contributions

The repository history supports the following owner roles:

- originating and continuing the ArchaeoAI project and selecting archaeology, LiDAR, and geospatial
  machine learning as its broad direction;
- defining project priorities, issuing phase-specific briefs, and setting stop conditions;
- making owner authorization decisions for data access, modelling, final-test use, private
  inference, runtime work, review preparation, and merges;
- requiring geographic evaluation, cautious claims, privacy controls, reproducibility, and
  external-review gates;
- communicating with outside academics and deciding how owner-relayed suggestions should be
  recorded or acted upon;
- reviewing and accepting, rejecting, or requesting changes to generated work; and
- retaining final responsibility for repository content and public claims.

The record does **not** support saying that the owner independently hand-authored all software,
analysis, documentation, or methodological detail. The Phase 2A.5 record says the structured
primary curation was performed in one Codex session and was not independent human review. Other
research logs distinguish owner authorization from Codex implementation. The frozen 40-record
independent label-reliability review remains outstanding.

## B. External human expert influence

Two owner-relayed inputs are currently documented:

1. An external professor/expert whose identity was not supplied for publication recommended a clear
   separation between AI/model output, hypotheses, human-vetted observations, and
   archaeologist-validated evidence. This careful paraphrase informed the evidence ladder. It is
   not a quotation, endorsement, supervision relationship, collaboration, or completed review.
2. The project owner reports that Professor James Conolly requested clearer transparency about the
   division between human and generative-AI contributions before providing detailed feedback. This
   is an owner-relayed paraphrase of a review prerequisite, not a quotation, endorsement,
   collaboration, supervision, or evidence that detailed or independent review occurred.

No institution is represented as sponsoring, supervising, approving, or endorsing ArchaeoAI.

## C. Generative-AI and tool contributions

Tracked logs explicitly identify Codex or OpenAI Codex as a material contributor across project
phases. Its recorded work includes:

- brainstorming and research-planning support;
- proposing methodological alternatives, decision gates, and implementation plans;
- generating and refactoring Python, PowerShell, tests, validation logic, and CI configuration;
- debugging cross-platform and continuous-integration failures;
- implementing data-curation, terrain-processing, modelling, robustness, external-validation,
  controlled-inference, privacy, and portal workflows under owner authorization;
- running scripted analyses and technical/private QA steps described in the research logs;
- drafting and editing research documentation, the manuscript, review materials, product
  architecture, and interface copy;
- assisting literature discovery and citation checking, without constituting a systematic
  literature review or source authority;
- checking interpretations against frozen results and claim limits;
- suggesting security/privacy threat controls and evidence boundaries; and
- preparing repository and contributor-facing materials.
- designing and implementing the Phase 5E-C review-evidence schema, deterministic bundle tooling,
  validation tests, gate derivation, and reviewer workflow under owner authorization.

Standard software libraries and deterministic tools—including Python, Git, pytest, Ruff,
scikit-learn, PyTorch, Rasterio, and GitHub Actions—also executed code or checks. Their output is not
human review and is distinct from generative-AI drafting.

The repository did not maintain a complete session-by-session inventory of every underlying model
name, model version, system prompt, sampling setting, or transient tool call. OpenAI Codex is
explicitly documented; no complete model/version chronology is claimed. This disclosure does not
attribute work to other named AI products where the tracked history does not establish their use.

## D. Verification and responsibility

Generated suggestions were subject to owner acceptance, rejection, revision, authorization, and
Git review. Automated tests, checksums, frozen-artifact validators, privacy scans, and CI provide
technical evidence for specific properties such as deterministic transformations, exact stored
values, fail-closed boundaries, and repository consistency.

Those safeguards do not prove archaeological truth, label validity, model generality, legal
compliance, source ownership, harmless model deserialization, or the quality of scientific
judgement. AI assistance is not an independent external review. Qualified outside review must be
attributable, conflict-declared, scoped, and recorded separately. The bowl-barrow-only scope,
unlabelled backgrounds, limited geography, spent external test, private-data constraints, and
`RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW` status remain controlling.

## Concise manuscript-ready disclosure

The frozen manuscript is not edited in Phase 5E-B because its bytes are bound by the manuscript
evidence manifest. At the next explicitly authorized manuscript revision, the following wording is
suitable for an acknowledgements or methods disclosure, subject to venue policy and author review:

> ArchaeoAI was directed by the project owner and materially assisted by generative AI, principally
> documented as OpenAI Codex. AI assistance included research and implementation planning, code and
> test generation, analysis-workflow implementation, debugging, documentation and manuscript
> drafting, literature-discovery support, and privacy/security design suggestions. The owner set
> scope and authorization decisions, reviewed generated work, and remains responsible for accepted
> content. Automated tests and frozen-artifact checks verify defined technical properties but do not
> establish archaeological truth or independent scientific review. See the
> [full AI assistance and authorship disclosure](../review/AI_ASSISTANCE_AND_AUTHORSHIP_DISCLOSURE.md).

Adopting this paragraph later must be a deliberate manuscript revision with corresponding evidence-
manifest handling. It must not be presented as contemporaneous independent review or as compliance
with a particular publisher's authorship policy until that policy is checked.
