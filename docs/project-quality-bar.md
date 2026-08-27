# ArchaeoAI project-quality bar

This is a research maturity standard, not an admissions checklist. No item may be represented as complete before the evidence exists.

## Four gates before a public claim

| Gate | Question | Required evidence | Stop condition |
|---|---|---|---|
| 1. Data trust | Do we have lawful, safe, auditable inputs? | Source registry, license record, sensitivity assessment, visual/CRS QA | Missing reuse right, unsafe location handling, or unreliable labels. |
| 2. Method trust | Does the experiment test the stated question without leakage? | Pre-specified split, baseline, seed, metric, negative-sampling logic, code review | Random-only split, tile/acquisition confound, or held-out data used in development. |
| 3. Result trust | Does the result survive independent regional evaluation and error review? | Geographic holdout, block-level uncertainty, false-positive/negative sample review, negative control | No independent blocks or effect disappears beyond uncertainty. |
| 4. Communication trust | Can a skeptical reader reproduce and understand the limitation? | Dataset card, experiment report, environment lock, claims register, plain-language explanation | Overclaiming, hidden AI assistance, opaque code, or unreproducible result. |

## Evidence hierarchy

1. Reproducible result with data provenance and geographic holdout.
2. Clear negative result that rules out a plausible claim.
3. Documented methodological improvement compared with a meaningful baseline.
4. Independent critique that changes the project.
5. Public-facing communication *after* the preceding evidence exists.

Awards, web traffic, a large model, or a polished demo are not evidence of research quality.

## Required artifacts for a mature release

- A research report that states one bounded contribution.
- An executable clean-environment reproduction of the headline table/figure.
- A dataset card that distinguishes what can be shared from what must remain private for heritage protection.
- A claims register with evidence and wording limits for every headline statement.
- At least one external reviewer question that produced a documented revision.
- A student-authored oral defense: 10 minutes of method and 10 minutes of skeptical questions, with no notes.

## No-go language

Never say “discovered a site,” “proved,” “works generally,” or “AI archaeologist” unless the precise evidentiary burden has been met—which this project is not designed to do. Prefer: “the model identified a terrain signature consistent with the labelled class under this evaluation protocol.”
