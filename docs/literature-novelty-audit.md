# Literature and novelty audit — initial scan, 27 August 2026

## What the scan establishes

LiDAR archaeological mapping is mature, and both CNN/object-detection and segmentation systems already exist. A generic "AI detects archaeology from LiDAR" project would not be novel. The defensible opening is a smaller, transparent study of **representation sensitivity and spatial-validation inflation** using a fully documented, reproducible public-data pipeline.

This is a preliminary audit, not a systematic review. Searches included peer-reviewed archaeology/remote-sensing papers and official data providers through 27 August 2026.

| Source | Setting/method | Relevant finding | Implication for ArchaeoAI |
|---|---|---|---|
| Vinci (2024), *LiDAR Applications in Archaeology: A Systematic Review*, DOI 10.1002/arp.1931 | Review of 291 studies, 2001–2022 | Results depend on material culture, vegetation, and resolution; open institutional data underpin much European/North American work. | Record resolution/terrain context; do not generalize broadly. |
| Verschoof-van der Vaart & Lambers (2019), *JCAA*, DOI 10.5334/jcaa.32 | R-CNN on Dutch LiDAR archaeology | Established automated-object-detection workflow. | Avoid merely reproducing object detection. |
| Trier et al. (2021), *JCAA*, DOI 10.5334/jcaa.64 | Detection/segmentation of LiDAR structures | Explicitly raises spatial and typological generalization. | Geographic holdout becomes a core research contribution. |
| Character et al. (2024), *J. Archaeological Science*, DOI 10.1016/j.jas.2024.106022 | Broadscale CNN detection across 615 km² Maya area | Multi-area training is feasible and meaningful. | Do not claim geographic robustness from one random split. |
| Historic England (updated 2024), *LiDAR* | Official guidance and English public data context | LiDAR can reveal subtle earthworks but interpretation remains expert work. | Use cautious archaeological language and public data only. |
| Environment Agency, National LIDAR Programme | England-wide 1 m elevation data | Accessible public DTM coverage is available. | Candidate terrain source, subject to retrieval/licensing confirmation. |

## Novelty audit

| Type | Assessment | Position |
|---|---|---|
| Problem | Saturated if framed as generic detection | Reject generic framing. |
| Method | New architectures are unrealistic and unnecessary initially | Do not pursue algorithmic novelty. |
| Dataset/benchmark | Potentially useful only if labels and splits are openly redistributable | Investigate; do not promise. |
| Analysis | Under-reported spatial leakage and representation sensitivity are plausible, testable gaps | Primary contribution candidate. |
| Application | England public DTM plus documented heritage records is feasible, but label access is the key risk | Prioritize data/licensing audit. |

## Literature gap statement

Within this initial search, the strongest feasible gap is not detection itself but a transparent measurement of how representation and split design affect apparent performance for a narrowly defined archaeological earthwork task. This must be re-evaluated after a systematic search and data audit.

## Next literature task

Build a PRISMA-style search log and expand this matrix to 20–30 primary papers before locking the study design.
