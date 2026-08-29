"""Fit the full-data frozen RF and freeze Phase 2F-A before new-terrain scoring."""

from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import numpy as np
import sklearn

from archaeoai.inference import (
    DEDUPLICATION_DISTANCE_M,
    DEDUPLICATION_IOU,
    DOMAIN_SIZE_PIXELS,
    EXPECTED_PRIMARY_CONFIG_SHA256,
    FEATURE_COUNT,
    MEDIUM_PERCENTILE_RANGE,
    MODEL_SEED,
    PATCH_SIZE_M,
    PATCH_SIZE_PIXELS,
    QUEUE_LIMIT,
    REPRESENTATION_CHANNELS,
    REVIEW_SAMPLE_SEED,
    STRIDE_M,
    STRIDE_PIXELS,
    fit_frozen_random_forest,
    model_state_sha256,
    protocol_hash,
    write_private_candidate_receipt,
    write_private_model,
)

SOURCE_COMMIT = "696534a6eb7ce42b3023478696087785ca963b4c"
IMMUTABLE_ARTIFACTS = {
    "outputs/modelling/e001_primary_baseline_config.json": (
        "035cd8d8c9d78a56f2261de71facfc54e74f4a8e19d61baf4eda387e90b8d385"
    ),
    "outputs/modelling/e001_final_results.csv": (
        "28b7503965ea75143616f5e726890b842030a20be8c283e2e9a7dd3c540e39a6"
    ),
    "outputs/modelling/e001_random_vs_geographic.json": (
        "6d6d8cf9ebca15d7cf28c99e9d05d9b94b5837695aaf29a973c80d708aad9055"
    ),
    "outputs/modelling/e001_final_model_audit.json": (
        "ad1204c002b6eb591b9ccf8cfdc89021ffcc6f8b709b30aae6fefd0ec9e891c2"
    ),
    "outputs/robustness/e001_robustness_summary.json": (
        "6ebf881562458110562e7181824c677acf7ecfa7edc673152e96bf1a7c319591"
    ),
    "outputs/robustness/e001_geographic_fold_manifest.json": (
        "2575232a392925eedcbabe343e599df58a789137bad3b356b3774e9ef9637157"
    ),
    "outputs/deep_learning/e001_cnn_summary.json": (
        "465681bc0b296e856b46b98268c11576cc8fc5dc9198a8601d7ed1afb50df1e5"
    ),
    "outputs/deep_learning/e001_cnn_vs_rf.json": (
        "7cfaa9973bb47bf364778a8070aff9b30b893bec00f7e3d3d8bd29831dd82214"
    ),
    "outputs/deep_learning/e001_cnn_fold_results.csv": (
        "1a0a3efeffb1c65cb10928dfb8b4e658411a652c28854a4d9a9eca586b5f9d5c"
    ),
    "outputs/dataset/e001_modelling_index.csv": (
        "f03df4ab5952746f7d841c7acef12cbcf1cc8e7a233b93b03d7317057b974f72"
    ),
    "outputs/dataset/e001_random_split_manifest.json": (
        "755660bab25be1c33b2ffdc462d82021a62c9378c7e1c2b964ee0086b353d432"
    ),
    "outputs/dataset/e001_geographic_split_manifest.json": (
        "0176c747176747376df74ff427326c64be61a6e0b624244919b800f3e813bc55"
    ),
}


def _validate_immutable_artifacts(root: Path) -> None:
    for relative, expected in IMMUTABLE_ARTIFACTS.items():
        observed = hashlib.sha256((root / relative).read_bytes()).hexdigest()
        if observed != expected:
            raise ValueError(f"frozen artifact changed: {relative}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    destination = root / "configs/e001-phase-2f-a-inference-protocol.json"
    if destination.exists():
        raise FileExistsError("refusing to overwrite the frozen Phase 2F-A protocol")
    _validate_immutable_artifacts(root)

    estimator, training = fit_frozen_random_forest(root)
    state_sha256 = model_state_sha256(estimator)
    private_model_path, artifact_sha256 = write_private_model(
        root,
        estimator,
        destination=root / "data/private/e001/inference/e001_phase2f_random_forest.pkl",
    )
    fit_receipt = {
        "phase": "2F-A",
        "purpose": "private_full_e001_fit_receipt_before_new_terrain_scoring",
        "training_observations": int(training.features.shape[0]),
        "class_counts": {
            "positive_bowl_barrow": int(training.labels.sum()),
            "unlabelled_background": int((training.labels == 0).sum()),
        },
        "feature_count": int(training.features.shape[1]),
        "model_seed": MODEL_SEED,
        "primary_config_sha256": EXPECTED_PRIMARY_CONFIG_SHA256,
        "modelling_index_sha256": training.modelling_index_sha256,
        "terrain_inventory_sha256": training.terrain_inventory_sha256,
        "model_state_sha256": state_sha256,
        "private_model_artifact_sha256": artifact_sha256,
        "private_model_relative_path": str(private_model_path.relative_to(root)).replace("\\", "/"),
        "new_terrain_loaded": False,
        "new_terrain_scored": False,
        "candidate_locations_created": False,
    }
    write_private_candidate_receipt(
        root,
        root / "data/private/e001/inference/e001_phase2f_fit_receipt.json",
        fit_receipt,
    )

    axis_windows = (DOMAIN_SIZE_PIXELS - PATCH_SIZE_PIXELS) // STRIDE_PIXELS + 1
    maximum_windows = axis_windows**2
    covered_side_m = (axis_windows - 1) * STRIDE_M + PATCH_SIZE_M
    payload: dict[str, object] = {
        "schema_version": "e001-phase-2f-a-controlled-inference-v1",
        "phase": "2F-A",
        "status": "READY_NO_REAL_SCAN",
        "frozen": True,
        "created_before_new_terrain_scoring": True,
        "source_commit": SOURCE_COMMIT,
        "primary_config_sha256": EXPECTED_PRIMARY_CONFIG_SHA256,
        "immutable_artifact_sha256": IMMUTABLE_ARTIFACTS,
        "objective": (
            "rank unseen terrain patches by similarity to the bounded E001 bowl-barrow class "
            "without claiming archaeological probability, detection, or discovery"
        ),
        "controlled_domain": {
            "public_alias": "CONTROLLED_DOMAIN_001",
            "maximum_domains": 1,
            "shape": "one_contiguous_5000m_by_5000m_square",
            "maximum_area_km2": 25.0,
            "exact_extent": "private_git_ignored_domain_receipt_required_before_acquisition",
            "domain_binding_status": "NOT_YET_BOUND",
            "selection_must_be_score_independent": True,
            "selection_requirements": [
                "public_Environment_Agency_1m_DTM_coverage",
                "EPSG_27700_OSGB36_British_National_Grid",
                "single_compatible_acquisition_where_practical",
                "no_overlap_with_any_E001_training_or_evaluation_window",
                "computationally_bounded",
                "exact_extent_not_public",
            ],
        },
        "terrain_policy": {
            "allowed": "public_Environment_Agency_1m_LiDAR_DTM_only",
            "required_crs": "EPSG:27700",
            "required_resolution_m": 1.0,
            "excluded": [
                "DSM_or_surface_models",
                "non_public_or_unclearly_licensed_terrain",
                "incompatible_resolution_or_CRS",
                "terrain_overlapping_any_E001_modelling_window",
                "terrain_selected_after_model_score_inspection",
            ],
        },
        "patch_generation": {
            "patch_dimensions_m": [PATCH_SIZE_M, PATCH_SIZE_M],
            "patch_dimensions_pixels": [PATCH_SIZE_PIXELS, PATCH_SIZE_PIXELS],
            "stride_m": STRIDE_M,
            "stride_pixels": STRIDE_PIXELS,
            "grid_anchor": "private_domain_upper_left_pixel_grid",
            "order": "row_major",
            "manual_pre_score_browsing": False,
            "maximum_complete_domain_windows_before_QA": maximum_windows,
            "maximum_effectively_covered_area_km2": (covered_side_m**2) / 1_000_000,
            "required_counts": [
                "total_windows",
                "valid_windows",
                "rejected_windows",
                "no_data_windows",
            ],
        },
        "preprocessing": {
            "terrain_QA": "same_automatic_E001_patch_and_representation_QA",
            "representations_in_order": list(REPRESENTATION_CHANNELS),
            "normalized_elevation": "subtract_valid_per_patch_median",
            "slope": "degrees_at_1m_resolution",
            "hillshade": {"azimuth_degrees": 315.0, "altitude_degrees": 45.0},
            "local_relief_radius_m": 16.0,
            "pooling": {
                "method": "non_overlapping_mean",
                "block_shape": [4, 4],
                "input_shape": [128, 128],
                "output_shape": [32, 32],
                "features_per_representation": 1024,
            },
            "feature_count": FEATURE_COUNT,
            "training_inference_equivalence_required": True,
        },
        "model": {
            "family": "RandomForestClassifier",
            "parameters": {
                "n_estimators": 300,
                "max_depth": 8,
                "min_samples_leaf": 5,
                "max_features": "sqrt",
                "n_jobs": 1,
                "random_state": MODEL_SEED,
            },
            "standard_scaler": False,
            "metadata_features": False,
            "fit_policy": (
                "fit_once_on_all_522_curated_E001_modelling_observations_after_all_Phase_2D_"
                "and_Phase_2E_evaluation"
            ),
            "training_observations": 522,
            "training_class_counts": {
                "positive_bowl_barrow": 261,
                "unlabelled_background": 261,
            },
            "model_state_sha256": state_sha256,
            "private_model_artifact_sha256": artifact_sha256,
            "model_artifact": "private_git_ignored",
            "candidate_result_retraining_allowed": False,
        },
        "score_semantics": {
            "preferred_terms": [
                "model_score",
                "terrain_similarity_score",
                "bowl_barrow_class_score",
                "candidate_ranking_score",
            ],
            "forbidden_terms": [
                "probability_archaeology",
                "probability_of_a_site",
                "archaeological_confidence",
                "discovery_probability",
            ],
            "calibration_claimed": False,
            "required_statement": (
                "A score of 0.90 does not mean there is a 90% chance archaeology exists."
            ),
            "binary_site_decision": False,
        },
        "ranking": {
            "all_valid_windows_scored_before_review": True,
            "order": "descending_model_score_then_private_token",
            "highest_score_queue": {
                "eligible": "at_or_above_99th_percentile_after_deduplication",
                "maximum": QUEUE_LIMIT,
            },
            "medium_score_diagnostic_queue": {
                "eligible_percentile_interval_inclusive": list(MEDIUM_PERCENTILE_RANGE),
                "selection": "sha256_rank_with_frozen_review_seed",
                "maximum": QUEUE_LIMIT,
            },
            "random_reference_queue": {
                "eligible": "remaining_deduplicated_windows",
                "selection": "sha256_rank_with_frozen_review_seed",
                "maximum": QUEUE_LIMIT,
            },
            "review_sample_seed": REVIEW_SAMPLE_SEED,
            "threshold_into_site_or_no_site": False,
        },
        "deduplication": {
            "method": "deterministic_greedy_non_maximum_suppression",
            "input_order": "descending_model_score_then_private_token",
            "suppress_if_centre_distance_less_than_m": DEDUPLICATION_DISTANCE_M,
            "suppress_if_window_IOU_greater_than": DEDUPLICATION_IOU,
            "cluster_representative": "highest_model_score_then_private_token",
        },
        "review": {
            "reviewer_initially_blinded_to_score_and_band": True,
            "queues": ["highest_score", "medium_score_diagnostic", "random_reference"],
            "categories": [
                "mound-like terrain morphology",
                "modern/engineered feature",
                "geomorphic/natural relief",
                "ambiguous",
                "insufficient evidence",
            ],
            "confirmation_of_archaeology_allowed": False,
            "known_record_cross_check": ("only_after_scores_ranking_and_blinded_review_are_frozen"),
            "database_absence_means_discovery": False,
            "false_positive_categories": [
                "modern",
                "geological_or_geomorphic",
                "forestry_related",
                "agricultural",
                "road_or_track_related",
                "drainage_or_boundary_related",
                "otherwise_ambiguous",
            ],
        },
        "privacy": {
            "exact_domain_extent_private": True,
            "exact_candidate_locations_private": True,
            "private_ranked_tables_git_ignored": True,
            "candidate_rasters_git_ignored": True,
            "georeferenced_candidate_images_git_ignored": True,
            "tracked_outputs_aggregate_only": True,
            "tracked_coordinates_NGR_GeoJSON_or_candidate_identifiers": False,
        },
        "public_outputs": [
            "total_window_counts",
            "aggregate_score_distribution",
            "aggregate_review_queue_counts",
            "aggregate_review_category_counts",
            "coarse_non_identifying_geographic_summary_if_safe",
            "model_and_pipeline_checksums",
            "software_versions",
            "performance_summary",
        ],
        "performance_measurement": {
            "CPU_only_required": True,
            "record": [
                "patches_per_second",
                "peak_CPU_RAM",
                "private_model_size",
                "model_load_time",
                "per_patch_model_latency",
                "approximate_area_throughput",
                "terrain_processing_bottleneck",
            ],
        },
        "safe_API": {
            "allowed_fields": [
                "model_version",
                "score_semantics",
                "aggregate_counts",
                "aggregate_score_distribution",
                "pipeline_status",
            ],
            "never_expose": [
                "exact_coordinates",
                "NGR_or_grid_reference",
                "private_window_token",
                "source_filename_or_path",
                "sample_identifier",
                "candidate_raster_or_georeferenced_image",
                "private_ranked_table",
            ],
            "website_or_API_built": False,
        },
        "stopping_criteria": [
            "any_frozen_artifact_or_model_checksum_mismatch",
            "private_domain_receipt_missing_or_not_git_ignored",
            "domain_exceeds_one_5km_by_5km_area",
            "terrain_CRS_resolution_type_or_license_mismatch",
            "any_E001_window_overlap",
            "training_inference_feature_equivalence_failure",
            "candidate_receipt_or_exact_location_would_be_tracked",
            "more_than_20_percent_windows_rejected_or_no_data",
            "fewer_than_100_valid_windows",
            "any_request_to_retune_from_candidate_results",
        ],
        "software_versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
            "platform": platform.platform(),
        },
        "execution_state": {
            "full_E001_RF_fit_completed": True,
            "new_terrain_loaded": False,
            "new_terrain_scored": False,
            "real_candidate_scan_completed": False,
            "candidate_scores_computed": False,
            "candidate_locations_created": False,
            "candidate_locations_exposed": False,
            "website_or_API_built": False,
        },
    }
    payload["protocol_sha256"] = protocol_hash(payload)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Frozen Phase 2F-A protocol: {payload['protocol_sha256']}")
    print(f"Full-data RF model state: {state_sha256}")
    print(f"Private model artifact: {artifact_sha256}")


if __name__ == "__main__":
    main()
