# E001 Phase 2E-B: compact-CNN stronger-model evaluation

## Status

**COMPLETE.** The frozen setup was committed before training. All 15 pre-specified runs—five
geographic folds by three seeds—then completed without a technical failure, retry, hyperparameter
change, or added experiment.

The Phase 2D Random Forest geographic final result remains the primary confirmatory E001 result.
Any future CNN experiment is a later, explicitly stronger-model comparison; it cannot turn the
already-observed Phase 2D final partition into an unseen test.

## Result boundary

The **primary confirmatory result remains the Phase 2D Random Forest geographic final balanced
accuracy of 0.870968** with its previously reported uncertainty. Phase 2E-B instead reuses the
post-hoc Phase 2E-A geographic folds for a stronger-model comparison. Its results are not another
untouched final test and did not influence the architecture, optimizer, preprocessing, threshold,
early stopping, seeds, or folds.

The compact CNN averaged **0.700866 balanced accuracy**, compared descriptively with the frozen
Random Forest geographic-CV mean of **0.823406**. The difference is **−0.122540**, or −12.254
percentage points. The CNN was weaker on all five folds. No statistical-significance claim is made.

## Geographic fold and seed results

| Fold | Seed 20260829 | Seed 20260830 | Seed 20260831 | CNN mean ± population SD | RF | CNN − RF |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 0.768519 | 0.740741 | 0.759259 | 0.756173 ± 0.011548 | 0.796296 | −0.040123 |
| 2 | 0.707547 | 0.613208 | 0.660377 | 0.660377 ± 0.038514 | 0.839623 | −0.179246 |
| 3 | 0.690000 | 0.690000 | 0.690000 | 0.690000 ± 0.000000 | 0.790000 | −0.100000 |
| 4 | 0.675926 | 0.712963 | 0.694444 | 0.694444 ± 0.015120 | 0.861111 | −0.166667 |
| 5 | 0.700000 | 0.700000 | 0.710000 | 0.703333 ± 0.004714 | 0.830000 | −0.126667 |

Across the five fold means, the median was 0.694444, population standard deviation 0.031188,
minimum 0.660377, and maximum 0.756173. Across all 15 individual runs, the population standard
deviation was 0.036691 and range 0.613208–0.768519.

| Seed | Mean balanced accuracy across five folds |
|---:|---:|
| 20260829 | 0.708398 |
| 20260830 | 0.691382 |
| 20260831 | 0.702816 |

The seed-mean range was 0.017016. Seed variation was therefore small relative to the consistent
gap from the Random Forest; no best seed was selected or promoted.

## Other metrics and confusion

Mean metrics across the 15 complete outer-fold runs were:

| Metric | Mean | Population SD | Minimum | Maximum |
|---|---:|---:|---:|---:|
| Accuracy | 0.700866 | 0.036691 | 0.613208 | 0.768519 |
| Precision | 0.708583 | 0.065812 | 0.573171 | 0.857143 |
| Positive-class recall | 0.720275 | 0.128767 | 0.480000 | 0.888889 |
| F1 | 0.702256 | 0.048217 | 0.615385 | 0.793388 |
| ROC-AUC | 0.773282 | 0.041528 | 0.656461 | 0.831962 |
| Average precision | 0.768963 | 0.053511 | 0.630695 | 0.834297 |

Summing the 15 fold/seed confusion matrices gives TN=532, FP=251, FN=217, and TP=566. Each
observation appears once per seed in this sum. Aggregate background recall was 0.679438 and
positive-class recall 0.722861. Here a false positive means a bowl-barrow prediction on
`unlabelled_background`; it does not prove that archaeology is absent.

Coordinate-safe group summaries ranged from 0.555556 to 0.864583 balanced accuracy, but the
smallest groups are intrinsically unstable and were neither removed nor used for tuning.

## Training and overfitting diagnostics

All 15 runs early-stopped before epoch 100. The median best epoch was 23, with range 7–42. Mean
training loss declined from 0.692766 initially to 0.446335 at stopping. Mean internal-validation
loss improved from 0.690849 to a best-checkpoint mean of 0.569108, then rose to 0.611179 at
stopping. This divergence is evidence of overfitting; restoring the best internal-validation
checkpoint limited but did not eliminate it. Fold 2 had the largest seed SD (0.038514). No run
collapsed to predicting only one class.

## Computational cost

- total measured GPU training time: 89.055 seconds;
- total runner wall time: 105.883 seconds;
- mean GPU training time per run: 5.937 seconds;
- mean GPU inference time: approximately 0.194 ms per 128×128 patch;
- synthetic CPU inference: approximately 1.962 ms per patch;
- private checkpoint size: 240,853 bytes each (about 235 KiB);
- maximum allocated GPU memory observed: 159,191,552 bytes (about 152 MiB).

These are approximate measurements from this machine, not optimized deployment benchmarks.

## Interpretation and recommendation

**Stronger-model classification: CNN NOT JUSTIFIED AT CURRENT DATA SCALE.** The CNN learned a
repeatable above-chance signal and was reasonably seed-stable, but it was weaker than the simpler
Random Forest on every geographic fold and showed internal-validation overfitting. The complete
five-fold/three-seed evidence does not justify its extra training complexity for E001.

**Recommendation: USE RANDOM FOREST FOR PHASE 2F.** This recommendation combines stronger
geographic performance, simpler inference, interpretability, and the already-established robust
baseline evidence. More independently reviewed labelled data could justify revisiting compact CNNs
later, but no post-hoc architecture or hyperparameter search is added here.

## Runtime decision

The project adds only `torch>=2.13,<2.14`; torchvision, torchaudio, pretrained-model packages, and
system CUDA are not required. PyTorch's official Windows guidance supports Python 3.10–3.14. The
setup environment uses CPython 3.14.7 and the official `torch 2.13.0+cu130` wheel. It detected the
RTX 5060 Laptop GPU as CUDA compute capability 12.0 through the wheel's CUDA 13.0 runtime. No
Python downgrade, CUDA Toolkit installation, or system-software modification was performed.

Authoritative compatibility references:

- <https://pytorch.org/get-started/locally/>
- <https://pytorch.org/get-started/previous-versions/>
- <https://pytorch.org/blog/pytorch-2-12-release-blog/>
- <https://developer.nvidia.com/cuda/gpus>

## Frozen input and labels

Each observation is a `float32` tensor with shape `4 × 128 × 128`, ordered as:

1. per-patch normalized elevation;
2. slope;
3. hillshade;
4. local relief.

Labels are read only from `outputs/dataset/e001_modelling_index.csv`. The private NPZ archive is
selected only after that index supplies the class label, and terrain-content checksums are verified
before an image is returned. Coordinates, coarse BNG groups, provenance, survey year, source
resolution, sample identifiers, filenames, and paths are never tensor features. Dataset items
return only the four-channel image and binary label.

## Frozen geographic design

The CNN must reuse the five Phase 2E-A folds exactly. It does not regenerate, optimize, or reorder
them. Their assignment SHA-256 remains:

`825eb1088a53f764f991bf6bb22f2c9fe6eeb868916a5abab92012eed85d90ab`

For each future outer fold, early stopping uses an internal validation split drawn only from the
other four folds' training groups. Complete BNG groups are deterministically SHA-256 ranked with
the frozen `e001-cnn-internal-validation-v1` salt; 20% of eligible groups, rounded to the nearest
whole group with a minimum of one, form internal validation. Complete geographic groups, matched
observation groups, and overlap components remain together. The outer held-out fold is never used
for normalization, early stopping, checkpoint choice, or any other training decision.

## Frozen architecture

The compact network has 59,145 trainable parameters:

```text
4×128×128
→ Conv 4→24, 3×3, padding 1 → ReLU → 2×2 max pool
→ Conv 24→48, 3×3, padding 1 → ReLU → 2×2 max pool
→ Conv 48→96, 3×3, padding 1 → ReLU → 2×2 max pool
→ adaptive average pooling to 1×1
→ Linear 96→64 → ReLU → Linear 64→1
→ one binary logit
```

There is no pretrained backbone, ResNet, transformer, augmentation, or probability-calibration
claim.

## Frozen training protocol

Future Phase 2E-B training, if separately authorized, must use:

- loss: `BCEWithLogitsLoss`;
- optimizer: AdamW;
- learning rate: `0.001`;
- weight decay: `0.0001`;
- Adam betas: `(0.9, 0.999)` and epsilon `1e-8`;
- batch size: `16`;
- maximum epochs: `100`;
- seeds: `20260829`, `20260830`, and `20260831`;
- no augmentation;
- per-channel mean and population-standard-deviation normalization fitted from internal-training
  pixels only;
- early stopping on internal-validation BCE loss, patience 12 epochs, minimum delta 0, restoring
  the best weights.

Python, NumPy, Torch CPU, and all Torch CUDA devices are seeded. Deterministic algorithms and
deterministic cuDNN behavior are enabled, while cuDNN benchmarking is disabled. Operations that
cannot satisfy the deterministic policy must fail rather than silently relax it.

## Checkpoint and privacy policy

Future checkpoints are private, ignored `.pt`/`.pth` artifacts. The defined payload contains only
the CPU state dictionary, protocol hash, and epoch. It excludes coordinates, sample identifiers,
paths, filenames, provenance, survey year, predictions, and observations. No checkpoint is created
in Phase 2E-B0.

## Frozen protocol

The immutable pre-training protocol is
`outputs/deep_learning/e001_cnn_protocol.json`. Its SHA-256 is computed from canonical JSON while
excluding only its own `protocol_sha256` field. Its historical `READY_NOT_TRAINED` status records
that it was frozen before training and is not rewritten afterward. Completed evidence is stored in
the separate coordinate-safe result summary.

Frozen protocol SHA-256:
`6007a2b62157195c26a05474935d88f1e3ed7b6c6780572f35c1162ab08d39c0`.

## Limitations and explicitly not performed

- only 522 curated observations and 23 coarse geographic groups are available;
- labels remain curated Scheduled Monument records and uncertain unlabelled backgrounds;
- no independent CPython 3.12 or external-researcher reproduction has occurred;
- the comparison is post-hoc and not a new untouched final test;
- no secondary condition was pre-registered, so none was run;
- no post-result tuning, new fold creation, augmentation, or background change;
- unknown-terrain scanning;
- Phase 2F or website work.

The CNN experiment does not demonstrate unknown-site discovery and does not create archaeological
candidate predictions.
