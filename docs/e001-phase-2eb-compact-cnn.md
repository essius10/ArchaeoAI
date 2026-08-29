# E001 Phase 2E-B0: frozen compact-CNN methodology

## Status

**READY_NOT_TRAINED.** This document records setup and preregistration only. No real E001 sample
has been loaded through the CNN dataset, no CNN has been trained, no geographic cross-validation
has been run, and no CNN performance metric exists.

The Phase 2D Random Forest geographic final result remains the primary confirmatory E001 result.
Any future CNN experiment is a later, explicitly stronger-model comparison; it cannot turn the
already-observed Phase 2D final partition into an unseen test.

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

The machine-readable protocol is
`outputs/deep_learning/e001_cnn_protocol.json`. Its SHA-256 is computed from canonical JSON while
excluding only its own `protocol_sha256` field. The protocol status must remain
`READY_NOT_TRAINED` until a separately approved training phase begins.

Frozen protocol SHA-256:
`6007a2b62157195c26a05474935d88f1e3ed7b6c6780572f35c1162ab08d39c0`.

## Explicitly not performed

- real E001 CNN training;
- geographic CNN cross-validation;
- CNN accuracy, balanced accuracy, F1, ROC-AUC, or other performance calculation;
- CNN versus Random Forest comparison;
- new fold creation or background changes;
- unknown-terrain scanning;
- Phase 2F or website work.
