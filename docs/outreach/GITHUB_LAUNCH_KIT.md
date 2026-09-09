# ArchaeoAI GitHub launch kit

Status: **DRAFT PUBLIC COPY — PUBLICATION NOT AUTHORIZED BY THIS DOCUMENT**

This kit offers factual, community-specific starting points for sharing ArchaeoAI without spam,
engagement manipulation, discovery claims, or exposure of sensitive material. Adapt each draft to
the venue, disclose the author's connection to the project, read community rules, and participate
in the discussion. Never mass-post identical copy or ask for votes.

## Core shareable hook

> Can a machine-learning model recognize archaeological terrain patterns when you force it to
> generalize geographically rather than letting nearby terrain leak between training and testing?

ArchaeoAI studies that question for documented bowl barrows in LiDAR-derived terrain. The bounded
results are 87.1% balanced accuracy on one frozen two-group geographic test (n=62), 82.3% mean over
five post-hoc geographic robustness folds, and 84.2% (95% CI 77.5–90.0%, n=120) on one independent
external test, which is now spent. These are terrain-classification results, not archaeological
probabilities or discovery evidence.

## 1. Hacker News

### Readiness

`SHOW_HN_READY_WITH_SYNTHETIC_SCOPE`

Something inspectable and runnable exists: source, tests, aggregate evidence, a static research
site, and a local synthetic portal. A legitimate submission must say prominently that normal public
clones cannot run the real frozen model and that real-terrain public execution is not authorized.
The author should be available to discuss spatial leakage, validation design, privacy, and the
negative CNN result. If that limitation would make the submission confusing, wait until a separately
authorized public-safe model demonstration exists; do not weaken the gate for publicity.

### Potential submission

**Title:** Show HN: ArchaeoAI – testing geographic leakage in archaeological LiDAR ML

**Text:**

> I built ArchaeoAI to examine a narrow question: does a model that recognizes terrain patterns
> associated with documented bowl barrows still work when nearby geography cannot leak across the
> split? The repository includes the full coordinate-safe research trail, tests, aggregate results,
> a negative compact-CNN comparison, and a synthetic local portal. The frozen Random Forest's
> approved artifact and all sensitive terrain remain private, so public clones do not run the real
> model. Scores are terrain similarity, not archaeological probability, and this is not a discovery
> system. I would value technical discussion about spatial validation, reproducibility, and whether
> the evidence boundaries are clear.

## 2. GIS and geospatial communities

**Discussion title:** How should we validate terrain classifiers when nearby LiDAR patches share
landscape and survey history?

> Random splits can put spatially related terrain on both sides of an evaluation. In ArchaeoAI I
> used geographic groups, nonadjacent holdouts, acquisition-provenance audits, and a separate
> external dataset to test how much performance survived. The repository documents the split and
> leakage controls, including what remains uncertain. How do practitioners choose block size and
> separation distance without making evaluation either leaky or unrepresentative?

## 3. Machine-learning communities

**Discussion title:** A small geospatial case where a Random Forest beat a compact CNN across every
held-out fold

> ArchaeoAI compares a frozen Random Forest using four pooled terrain representations with a compact
> CNN on the same five geographic folds. The RF averaged 82.3% balanced accuracy and the CNN 70.1%;
> the simpler model was retained. The useful question is not “trees always beat deep learning,” but
> how dataset size, inductive bias, representation engineering, and geographic validation interact.
> The protocol, aggregate outputs, and negative result are public for critique.

## 4. Archaeology and digital-archaeology communities

**Discussion title:** Where should AI-assisted terrain screening stop and archaeological
interpretation begin?

> ArchaeoAI studies documented bowl-barrow terrain while treating unrecorded background as
> unlabelled—not archaeology-free. Its evidence ladder keeps model output below morphology review,
> records checks, and field or specialist evidence. Candidate coordinates remain private and there
> is no discovery claim. I would welcome critique of the terminology, label limitations, and human
> review boundary from archaeological practitioners.

## 5. LinkedIn

> I have prepared ArchaeoAI's coordinate-safe research repository for external review. It asks a
> practical geospatial-ML question: can terrain-pattern performance survive geographic separation,
> not just a random split? The project documents a frozen Random Forest, a transparently negative
> CNN comparison, external geographic evaluation, reproducibility checks, and strict privacy and
> human-review boundaries. It does not claim archaeological discovery, and the external review is
> not complete. The repository is open for careful technical, archaeological, security, and
> reproducibility feedback.

## 6. X and short-form technical social media

> Can a terrain model generalize geographically when nearby LiDAR cannot leak across the split?
> ArchaeoAI documents a frozen RF baseline, a negative CNN comparison, external evaluation, and a
> privacy-first human-review boundary. Research code and synthetic demo: [repository link]. No
> discovery claim; real terrain/model execution is not public.

## 7. University and research mailing lists

**Subject:** Feedback invited: geographic validation and privacy boundaries in archaeological
LiDAR ML

> ArchaeoAI is an independently developed study of terrain-pattern classification for documented
> bowl barrows. The public package includes a manuscript draft, reproducibility instructions,
> aggregate results, a reviewer guide, and focused security/privacy/scientific checklists. I am
> seeking critique—not endorsement—on geographic leakage controls, label/background definitions,
> archaeological terminology, and the evidence ladder. Phase 5E review remains incomplete. No
> sensitive coordinates, terrain, candidate locations, or private model artifact are public.

## Community-surface recommendations

- **GitHub Discussions:** recommended, but not enabled in this phase. It would give researchers and
  developers a place for open-ended methodology, terminology, and reproducibility questions that
  are not code issues. If enabled later, begin with `Geospatial validation`, `Archaeology and
  terminology`, `Reproducibility`, and `Security and privacy`; pin a warning against posting
  sensitive locations or private data.
- **Issues and pull requests:** already supported by safe templates; use them for actionable defects
  and scoped changes rather than broad conversation.
- **Citation:** `CITATION.cff` exists and makes no DOI or affiliation claim.
- **Security, contribution, and roadmap:** `SECURITY.md`, `CONTRIBUTING.md`, and `docs/roadmap.md`
  provide visible entry points.
- **Release notes:** defer until a release is authorized.

GitHub Discussions can be enabled by a repository administrator under **Settings → Features**. See
[GitHub's Discussions guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/enabling-or-disabling-github-discussions-for-a-repository).

## Release readiness

`FORMAL_RELEASE_BLOCKED`

The code and coordinate-safe evidence are technically substantial enough for a future
external-review-ready research snapshot, but unresolved repository licensing and incomplete Phase
5E review block a formal release now. Do not create a version, tag, DOI, preprint, or GitHub release
for attention. Any later release must exclude the private model, coordinates, terrain, candidate
locations, secrets, and row-level private outputs, and must preserve all limitations.

## Three coordinate-safe public visuals

1. [`outputs/modelling/figures/e001_balanced_accuracy_comparison.svg`](../../outputs/modelling/figures/e001_balanced_accuracy_comparison.svg)
   — the random-versus-geographic evaluation question using aggregate final results.
2. [`website/assets/cnn-vs-rf-by-fold.svg`](../../website/assets/cnn-vs-rf-by-fold.svg)
   — the RF-versus-CNN comparison across geographic folds, including the negative CNN result.
3. The Mermaid **Architecture snapshot** in [`README.md`](../../README.md) — the safe workflow from
   documented archaeology and LiDAR through `AI_OUTPUT`, human review, and bounded reporting.

The first two are coordinate-safe aggregate figures. The third can later be exported as an
accessible static SVG if a platform cannot render Mermaid; its content must remain non-geographic.

## Distribution blockers

- Phase 5E independent external review is not completed and RQ1 remains provisional.
- Repository-wide licensing is unresolved, so redistribution and formal release remain constrained.
- The approved model and real terrain are private; strangers can inspect the implementation and run
  the synthetic demo, not reproduce real model execution from a normal clone.
- No public deployment, DOI, peer-reviewed paper, institutional endorsement, or human-reviewed
  candidate outcome exists.
- A social-preview asset is specified but not designed, reviewed, or uploaded.

None of these blockers should be hidden or relaxed to increase reach.
