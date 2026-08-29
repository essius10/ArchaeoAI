"""Freeze the Phase 2E-B compact-CNN protocol without training or evaluating it."""

from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np
import torch

from archaeoai.deep_learning import (
    CNN_CHANNELS,
    CNN_INPUT_SHAPE,
    CNN_SEEDS,
    EXPECTED_FOLD_SHA256,
    CompactTerrainCNN,
    cnn_protocol_hash,
    read_fold_assignments,
    trainable_parameter_count,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    destination = root / "outputs/deep_learning/e001_cnn_protocol.json"
    if destination.exists():
        raise FileExistsError("refusing to overwrite the frozen E001 CNN protocol")
    assignments = read_fold_assignments(root / "outputs/robustness/e001_geographic_fold_groups.csv")
    model = CompactTerrainCNN()
    cuda_available = torch.cuda.is_available()
    payload: dict[str, object] = {
        "phase": "2E-B0",
        "status": "READY_NOT_TRAINED",
        "purpose": "setup_only_no_real_e001_training_or_scoring",
        "architecture": {
            "name": "CompactTerrainCNN",
            "input_shape": list(CNN_INPUT_SHAPE),
            "channels": list(CNN_CHANNELS),
            "feature_extractor": [
                "Conv2d(4,24,kernel_size=3,padding=1)",
                "ReLU",
                "MaxPool2d(2)",
                "Conv2d(24,48,kernel_size=3,padding=1)",
                "ReLU",
                "MaxPool2d(2)",
                "Conv2d(48,96,kernel_size=3,padding=1)",
                "ReLU",
                "MaxPool2d(2)",
                "AdaptiveAvgPool2d(1)",
            ],
            "head": ["Flatten", "Linear(96,64)", "ReLU", "Linear(64,1)"],
            "output": "one_binary_logit",
            "pretrained": False,
        },
        "parameter_count": trainable_parameter_count(model),
        "loss": "BCEWithLogitsLoss",
        "optimizer": {
            "name": "AdamW",
            "learning_rate": 0.001,
            "weight_decay": 0.0001,
            "betas": [0.9, 0.999],
            "epsilon": 1e-8,
        },
        "batch_size": 16,
        "max_epochs": 100,
        "early_stopping": {
            "monitor": "internal_validation_bce_loss",
            "mode": "min",
            "patience_epochs": 12,
            "minimum_delta": 0.0,
            "restore_best_weights": True,
            "internal_validation_fraction_of_outer_training_groups": 0.2,
            "group_selection": (
                "sha256_ranked_complete_BNG_groups_with_e001-cnn-internal-validation-v1_salt"
            ),
            "matched_and_overlap_units_kept_together": True,
            "held_out_geographic_fold_used": False,
        },
        "normalization": {
            "method": "per_channel_mean_and_population_standard_deviation",
            "fitted_on": "internal_training_pixels_only_per_outer_fold",
            "validation_or_holdout_statistics_used": False,
            "degenerate_channel_policy": "fail_closed",
        },
        "augmentation": "none",
        "seeds": list(CNN_SEEDS),
        "determinism": {
            "python_random_seeded": True,
            "numpy_seeded": True,
            "torch_cpu_seeded": True,
            "torch_cuda_all_devices_seeded": True,
            "deterministic_algorithms": True,
            "cudnn_deterministic": True,
            "cudnn_benchmark": False,
        },
        "geographic_folds": {
            "source": "outputs/robustness/e001_geographic_fold_groups.csv",
            "fold_count": 5,
            "geographic_group_count": len(assignments),
            "assignment_regenerated": False,
        },
        "fold_assignment_sha256": EXPECTED_FOLD_SHA256,
        "data_policy": {
            "input": "four_private_128x128_processed_terrain_representations",
            "labels_source": "outputs/dataset/e001_modelling_index.csv_only",
            "coordinates_as_features": False,
            "geographic_group_as_feature": False,
            "provenance_as_feature": False,
            "survey_year_as_feature": False,
            "sample_id_filename_or_path_as_feature": False,
        },
        "checkpoint_policy": {
            "private_and_git_ignored": True,
            "weights_only_payload": True,
            "sample_ids_coordinates_paths_and_provenance_excluded": True,
        },
        "software_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": torch.__version__,
            "torch_cuda_runtime": torch.version.cuda,
            "cudnn": str(torch.backends.cudnn.version()),
            "platform": platform.platform(),
        },
        "hardware_verification": {
            "cuda_available": cuda_available,
            "gpu_count": torch.cuda.device_count(),
            "gpu_name": torch.cuda.get_device_name(0) if cuda_available else None,
            "compute_capability": (
                list(torch.cuda.get_device_capability(0)) if cuda_available else None
            ),
        },
        "execution_state": {
            "real_e001_samples_loaded_by_cnn": False,
            "cnn_trained": False,
            "geographic_cv_run": False,
            "cnn_performance_metrics_computed": False,
            "random_forest_comparison_performed": False,
        },
    }
    payload["protocol_sha256"] = cnn_protocol_hash(payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Frozen READY_NOT_TRAINED CNN protocol: {payload['protocol_sha256']}")


if __name__ == "__main__":
    main()
