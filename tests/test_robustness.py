import hashlib
import json
from pathlib import Path

import numpy as np

from archaeoai.robustness import (
    MODEL_SEEDS,
    REPRESENTATION_CONFIGS,
    RobustnessRecord,
    build_frozen_random_forest,
    deterministic_geographic_folds,
    deterministic_training_units,
    fold_assignment_hash,
    read_robustness_index,
    validate_fold_assignments,
    validate_robustness_protocol,
)
from archaeoai.terrain.full_dataset import load_processed_archive
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping
from archaeoai.terrain.representations import normalize_elevation

ROOT = Path(__file__).resolve().parents[1]


def _record(index: int, group: str, label: str, related: str) -> RobustnessRecord:
    return RobustnessRecord(
        sample_id=f"sample-{index}",
        class_label=label,
        observation_group_id=related,
        overlap_component_id="",
        geographic_block_id=group,
        provenance_id="provenance",
        survey_year="2020",
        source_resolution_m="1.0",
        patch_sha256="a" * 64,
        qa_status="pass",
    )


def _synthetic_records() -> tuple[RobustnessRecord, ...]:
    records = []
    index = 0
    for group_index in range(10):
        for pair_index in range(group_index % 3 + 1):
            related = f"related-{group_index}-{pair_index}"
            records.append(_record(index, f"group-{group_index}", "positive_bowl_barrow", related))
            index += 1
            records.append(_record(index, f"group-{group_index}", "unlabelled_background", related))
            index += 1
    return tuple(records)


def test_geographic_folds_are_deterministic_balanced_and_keep_related_units() -> None:
    records = _synthetic_records()
    first = deterministic_geographic_folds(records)
    second = deterministic_geographic_folds(records)
    assert first == second
    counts = validate_fold_assignments(records, first)
    assert all(
        item["positive_bowl_barrow"] == item["unlabelled_background"] for item in counts.values()
    )
    assert fold_assignment_hash(first) == fold_assignment_hash(second)


def test_group_aware_training_fraction_is_deterministic_and_keeps_pairs() -> None:
    records = _synthetic_records()
    assignments = deterministic_geographic_folds(records)
    first = deterministic_training_units(
        records, test_fold=0, assignments=assignments, fraction=0.5
    )
    second = deterministic_training_units(
        records, test_fold=0, assignments=assignments, fraction=0.5
    )
    assert first == second
    assert first
    assert all(
        (record.related_unit_id in first)
        == any(
            other.related_unit_id == record.related_unit_id and other.related_unit_id in first
            for other in records
        )
        for record in records
    )


def test_seed_and_representation_sets_are_frozen() -> None:
    assert MODEL_SEEDS == (20260829, 20260830, 20260831, 20260901, 20260902)
    assert build_frozen_random_forest(20260829).get_params()["n_estimators"] == 300
    assert REPRESENTATION_CONFIGS["all_four"] == (
        "elevation_normalized",
        "slope_degrees",
        "hillshade_315_45",
        "local_relief_r16m",
    )
    assert set(REPRESENTATION_CONFIGS) == {
        "normalized_elevation",
        "slope",
        "hillshade",
        "local_relief",
        "all_four",
        "all_minus_elevation",
        "all_minus_slope",
        "all_minus_hillshade",
        "all_minus_local_relief",
    }


def test_median_normalization_is_invariant_to_absolute_offset() -> None:
    values = np.arange(64, dtype=np.float32).reshape(8, 8)
    mask = np.zeros_like(values, dtype=bool)
    mask[0, 0] = True
    original = normalize_elevation(values, mask)
    shifted = normalize_elevation(values + 1234.5, mask)
    np.testing.assert_allclose(original, shifted, atol=1e-6, equal_nan=True)


def test_serialization_order_compression_path_and_name_do_not_change_arrays(tmp_path: Path) -> None:
    arrays = {
        "elevation": np.arange(16, dtype=np.float32).reshape(4, 4),
        "mask": np.zeros((4, 4), dtype=bool),
        "elevation_normalized": np.zeros((4, 4), dtype=np.float32),
        "slope_degrees": np.ones((4, 4), dtype=np.float32),
        "hillshade_315_45": np.full((4, 4), 0.5, dtype=np.float32),
        "local_relief_r16m": np.full((4, 4), -0.25, dtype=np.float32),
    }
    first_path = tmp_path / "positive" / "positive-name.npz"
    second_path = tmp_path / "background" / "background-name.npz"
    first_path.parent.mkdir()
    second_path.parent.mkdir()
    np.savez(first_path, **arrays)
    np.savez_compressed(second_path, **dict(reversed(list(arrays.items()))))
    first = load_processed_archive(first_path)
    second = load_processed_archive(second_path)
    for first_array, second_array in zip(first[:2], second[:2], strict=True):
        np.testing.assert_array_equal(first_array, second_array)
    for key in arrays.keys() - {"elevation", "mask"}:
        np.testing.assert_array_equal(first[2][key], second[2][key])


def test_original_phase_2d_result_files_are_immutable() -> None:
    expected = {
        "e001_final_results.csv": (
            "28b7503965ea75143616f5e726890b842030a20be8c283e2e9a7dd3c540e39a6",
            "6fbcc43600b382e154ce159adcd705001b1b8c88a3d6b1ae39431d0153d58b60",
        ),
        "e001_random_vs_geographic.json": (
            "6d6d8cf9ebca15d7cf28c99e9d05d9b94b5837695aaf29a973c80d708aad9055",
            "a524c72d61fb2b20e6283e360d5bc790fd0be9744487aadc7ddc98ba9b2c33d9",
        ),
        "e001_final_model_audit.json": (
            "ad1204c002b6eb591b9ccf8cfdc89021ffcc6f8b709b30aae6fefd0ec9e891c2",
            "dfe1d98847a8d3a9f0c6fcad027cd63dc1d98b0ee674195b4d11f6ca3ed141b7",
        ),
    }
    for name, (digest, canonical_lf) in expected.items():
        payload = (ROOT / "outputs/modelling" / name).read_bytes()
        observed = hashlib.sha256(payload).hexdigest()
        if observed != digest:
            normalized = payload.replace(b"\r\n", b"\n")
            assert hashlib.sha256(normalized).hexdigest() == canonical_lf


def test_real_fold_manifest_matches_score_independent_algorithm_when_present() -> None:
    manifest_path = ROOT / "outputs/robustness/e001_geographic_fold_manifest.json"
    if not manifest_path.exists():
        return
    records = read_robustness_index(ROOT / "outputs/dataset/e001_modelling_index.csv")
    assignments = deterministic_geographic_folds(records)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["assignment_sha256"] == fold_assignment_hash(assignments)
    assert manifest["integrity"]["model_scores_used"] is False


def test_robustness_protocol_is_hash_frozen_before_scoring() -> None:
    protocol = validate_robustness_protocol(
        ROOT / "configs/e001-phase-2e-a-robustness-protocol.json"
    )
    assert protocol["geographic_folds"]["assignment_sha256"] == (
        "825eb1088a53f764f991bf6bb22f2c9fe6eeb868916a5abab92012eed85d90ab"
    )
    assert protocol["confirmatory_result_remains_phase_2d"] is True
    assert protocol["hard_background_stress"]["performed"] is False


def test_robustness_outputs_are_coordinate_safe_posthoc_and_complete() -> None:
    summary = json.loads(
        (ROOT / "outputs/robustness/e001_robustness_summary.json").read_text(encoding="utf-8")
    )
    assert_coordinate_safe_mapping(summary)
    assert summary["analysis_label"] == "posthoc_geographic_robustness"
    assert summary["posthoc_not_confirmatory"] is True
    assert summary["original_result_files_unchanged"] is True
    assert summary["no_phase_2d_reselection_or_retuning"] is True
    assert len(summary["primary_geographic_cv"]["folds"]) == 5
    assert summary["robustness_classification"] == "ROBUST"
    assert summary["recommendation"] == "GO FOR PHASE 2E-B STRONGER MODELS"
    assert summary["privacy"] == {
        "aggregate_only": True,
        "coordinates_written": False,
        "sample_identifiers_written": False,
        "maps_created": False,
    }


def test_robustness_sensitivity_matrix_and_permutations_are_frozen() -> None:
    summary = json.loads(
        (ROOT / "outputs/robustness/e001_robustness_summary.json").read_text(encoding="utf-8")
    )
    permutation = json.loads(
        (ROOT / "outputs/robustness/e001_permutation_diagnostic.json").read_text(encoding="utf-8")
    )
    assert set(summary["representation_summaries"]) == set(REPRESENTATION_CONFIGS)
    assert set(summary["seed_summaries"]) == {str(seed) for seed in MODEL_SEEDS}
    assert set(summary["training_fraction_summaries"]) == {
        str(fraction) for fraction in (1.0, 0.75, 0.5, 0.25)
    }
    assert permutation["runs"] == 100
    assert permutation["used_for_selection_or_tuning"] is False
    assert len(permutation["results"]) == 100
    assert all(
        interval["valid_replicates"] == 5000 and interval["undefined_replicates"] == 0
        for interval in summary["bootstrap_seed_sensitivity"].values()
    )
