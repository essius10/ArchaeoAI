# Phase 5E licensing, data, and model questions

Status: `QUALIFIED_REVIEW_REQUIRED`

This is a question set, not legal advice or a licence grant. ArchaeoAI has no repository-wide
licence. Formal public software release remains blocked until the owner obtains appropriately
qualified advice and records the intended scope and decisions.

## Exact questions for qualified review

### Original work and contributions

1. Who owns copyright in owner-directed, materially AI-assisted source code and prose under the
   law relevant to the owner and intended distribution?
2. Is there sufficient human authorship to license each material class, and how should generated or
   heavily AI-assisted passages be treated?
3. Are rights to every accepted contribution documented, or is a contributor attestation/DCO/CLA
   needed before redistribution?
4. Should software, prose, third-party-derived summaries, and non-redistributable private material
   use separate notices or licences rather than one root licence?

### Source data and derived outputs

5. Do the Historic England Open Data Hub terms, Open Government Licence, Ordnance Survey notice,
   and Environment Agency terms permit redistribution of each tracked aggregate artifact as used?
6. Which attribution wording, dates, provenance records, and non-endorsement notices are mandatory?
7. Does any row-level or location-linked derivative engage database rights, excluded third-party
   rights, archaeological-sensitivity limits, or additional provider permissions?
8. What rights attach to derived terrain representations, aggregate figures, trained parameters,
   score summaries, and reports, and which inputs constrain their reuse?

### Private model artifact

9. Who owns the frozen model artifact and the human/AI-authored training pipeline that produced it?
10. Is there documented authority to use, retain, transfer, reproduce, or redistribute the artifact
    separately from authority to publish the loader code?
11. Do source-data terms permit the artifact's intended private or commercial use, and could the
    trained state encode protected or location-sensitive information?
12. What provenance/custody evidence is needed before deserialization and before any third party is
    given access?

### Dependencies and distribution

13. Are the direct and transitive dependency licences compatible with the proposed binary, source,
    hosted-service, research-archive, or commercial distribution model?
14. What notices, source offers, attribution files, or patent/trademark statements would each
    distribution form require?
15. Does bundling PyTorch, GDAL/Rasterio, PROJ/PyProj, scikit-learn, FastAPI/Uvicorn, or their
    transitive components change the obligations compared with installation from package indexes?

### Intended use and future publication

16. What additional contractual, data-protection, heritage, export, consumer, or professional-duty
    questions arise for research sharing, private pilots, paid use, or public model execution?
17. Does any confidential or potentially patent-relevant owner material need review before public
    disclosure, without publishing that material in the review record?
18. What precise licence structure and release inventory can be approved without implying provider,
    academic, institutional, or reviewer endorsement?

## Required output

The qualified reviewer should identify jurisdiction and scope, state assumptions and limitations,
answer or defer each question, specify required notices/permissions, and distinguish legal advice
from technical observations. The owner must then record dispositions in
`PHASE_5E_OWNER_DISPOSITION.md`. No licence or formal release is created by this checklist.
