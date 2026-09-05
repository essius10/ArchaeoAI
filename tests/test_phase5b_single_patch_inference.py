import json
from pathlib import Path

import numpy as np
import pytest

from archaeoai.inference import (
    FEATURE_COUNT,
    REPRESENTATION_CHANNELS,
    features_from_elevation,
)
from archaeoai.inference_system import (
    APPROVED_MODEL_ARTIFACT_SHA256,
    APPROVED_MODEL_RELATIVE_PATH,
    ApprovedModelArtifactReference,
    EvidenceLevel,
    ModelAdapterIdentityError,
    ModelAdapterOutputError,
    ModelAdapterUnavailableError,
    ModelArtifactIntegrityError,
    ModelArtifactUnavailableError,
    ModelIdentifier,
    SinglePatchFeatures,
    SinglePatchValidationError,
    TerrainInputMetadata,
    TerrainPatch,
    run_approved_single_patch_inference,
    score_single_patch_model_adapter,
    transform_single_patch,
    verify_approved_model_artifact,
)
from archaeoai.inference_system.contracts import PUBLIC_RESULT_FIELDS
from archaeoai.model_data import mean_pool_4x4
from archaeoai.terrain.representations import terrain_representations

FROZEN_CONFIG_SHA256 = "20cd377c17373eeeb5403c84119084287f193d93b42c8004d99c823e01a157e4"


def _metadata(**overrides: object) -> TerrainInputMetadata:
    values: dict[str, object] = {
        "crs": "EPSG:27700",
        "width": 128,
        "height": 128,
        "resolution_m": (1.0, 1.0),
        "band_count": 1,
        "nodata_fraction": 0.0,
    }
    values.update(overrides)
    return TerrainInputMetadata(**values)  # type: ignore[arg-type]


def _surface(kind: str) -> np.ndarray:
    y, x = np.mgrid[-64:64, -64:64]
    if kind == "plane":
        values = 100.0 + 0.03 * x - 0.02 * y
    elif kind == "mound":
        values = 100.0 + 1.5 * np.exp(-((x**2 + y**2) / 240.0))
    elif kind == "depression":
        values = 100.0 - 1.2 * np.exp(-((x**2 + y**2) / 300.0))
    elif kind == "sinusoidal":
        values = 100.0 + 0.4 * np.sin(x / 9.0) * np.cos(y / 13.0)
    elif kind == "noise":
        values = 100.0 + np.random.default_rng(20260905).normal(0.0, 0.05, (128, 128))
    elif kind == "constant":
        values = np.full((128, 128), 100.0)
    else:
        raise AssertionError("unknown synthetic fixture")
    return np.asarray(values, dtype=np.float32)


def _patch(kind: str = "mound") -> TerrainPatch:
    elevation = _surface(kind)
    return TerrainPatch(elevation, np.zeros(elevation.shape, dtype=bool), _metadata())


@pytest.mark.parametrize(
    "surface_kind", ["plane", "mound", "depression", "sinusoidal", "noise", "constant"]
)
def test_inference_path_is_bit_exact_to_canonical_research_path(surface_kind: str) -> None:
    patch = _patch(surface_kind)
    research = features_from_elevation(patch.elevation, patch.mask, resolution_m=1.0)
    reusable = transform_single_patch(patch)

    assert reusable.representation_names == REPRESENTATION_CHANNELS
    assert reusable.feature_vector.shape == (FEATURE_COUNT,)
    assert reusable.feature_vector.dtype == np.float32
    assert np.array_equal(reusable.feature_vector, research)


def test_exact_channel_pooling_flattening_and_concatenation_order() -> None:
    patch = _patch("sinusoidal")
    representations = terrain_representations(
        patch.elevation,
        resolution_m=1.0,
        mask=patch.mask,
        local_relief_radius_m=16.0,
        hillshade_azimuth_deg=315.0,
        hillshade_altitude_deg=45.0,
    )
    explicit = np.concatenate(
        [mean_pool_4x4(representations[name]) for name in REPRESENTATION_CHANNELS]
    ).astype(np.float32, copy=False)
    reusable = transform_single_patch(patch)

    assert tuple(representations) == REPRESENTATION_CHANNELS
    assert all(mean_pool_4x4(representations[name]).shape == (1024,) for name in representations)
    assert np.array_equal(reusable.feature_vector, explicit)


def test_transform_is_repeatable_read_only_and_rng_independent() -> None:
    patch = _patch("noise")
    np.random.seed(1)
    first = transform_single_patch(patch)
    np.random.seed(999)
    second = transform_single_patch(patch)

    assert np.array_equal(first.feature_vector, second.feature_vector)
    assert first.feature_vector.flags.writeable is False
    assert first.model_input().shape == (1, FEATURE_COUNT)
    assert first.model_input().flags.writeable is False


def test_hand_built_or_reordered_feature_contract_fails_closed() -> None:
    vector = np.zeros(FEATURE_COUNT, dtype=np.float32)
    with pytest.raises(ValueError, match="frozen finite float32"):
        score_single_patch_model_adapter(
            SinglePatchFeatures(vector),
            _InertTestOnlyModelDouble(vector),
        )

    vector.setflags(write=False)
    with pytest.raises(ValueError, match="frozen finite float32"):
        score_single_patch_model_adapter(
            SinglePatchFeatures(
                vector,
                tuple(reversed(REPRESENTATION_CHANNELS)),
            ),
            _InertTestOnlyModelDouble(vector),
        )


@pytest.mark.parametrize(
    ("elevation", "reason"),
    [
        (np.zeros((128,), dtype=np.float32), "dimensions"),
        (np.zeros((1, 128, 128), dtype=np.float32), "dimensions"),
        (np.empty((0, 0), dtype=np.float32), "shape"),
        (np.full((128, 128), "not-numeric", dtype=object), "real_numeric"),
        (np.zeros((128, 128), dtype=bool), "real_numeric"),
        (np.zeros((128, 128), dtype=np.complex64), "real_numeric"),
    ],
)
def test_invalid_dimensions_shape_or_dtype_fail_closed(elevation: np.ndarray, reason: str) -> None:
    patch = TerrainPatch(elevation, np.zeros(elevation.shape, dtype=bool), _metadata())
    with pytest.raises(SinglePatchValidationError, match=reason):
        transform_single_patch(patch)


@pytest.mark.parametrize("invalid_value", [np.nan, np.inf, -np.inf])
def test_unmasked_nonfinite_values_fail_closed(invalid_value: float) -> None:
    elevation = _surface("plane")
    elevation[4, 7] = invalid_value
    patch = TerrainPatch(elevation, np.zeros_like(elevation, dtype=bool), _metadata())
    with pytest.raises(SinglePatchValidationError, match="unmasked_nan_or_infinity"):
        transform_single_patch(patch)


def test_explicit_masked_nodata_uses_frozen_finite_mean_policy() -> None:
    elevation = _surface("mound")
    mask = np.zeros_like(elevation, dtype=bool)
    mask[:4, :4] = True
    elevation[mask] = np.nan
    fraction = float(mask.mean())
    result = transform_single_patch(
        TerrainPatch(elevation, mask, _metadata(nodata_fraction=fraction))
    )
    assert result.feature_vector.shape == (FEATURE_COUNT,)
    assert np.isfinite(result.feature_vector).all()


@pytest.mark.parametrize(
    ("metadata", "reason"),
    [
        (_metadata(crs="EPSG:4326"), "crs_mismatch"),
        (_metadata(resolution_m=(2.0, 2.0)), "resolution_mismatch"),
        (_metadata(width=127), "dimensions_mismatch"),
        (_metadata(band_count=2), "band_count_mismatch"),
        (_metadata(resolution_m="one metre"), "resolution_mismatch"),
        (_metadata(nodata_fraction="none"), "nodata_policy_failed"),
    ],
)
def test_wrong_or_malformed_metadata_fails_closed(
    metadata: TerrainInputMetadata, reason: str
) -> None:
    patch = _patch()
    with pytest.raises(ValueError, match=reason):
        transform_single_patch(TerrainPatch(patch.elevation, patch.mask, metadata))


def test_wrong_metadata_object_fails_closed() -> None:
    patch = _patch()
    with pytest.raises(ValueError, match="metadata_type_invalid"):
        transform_single_patch(
            TerrainPatch(patch.elevation, patch.mask, {"crs": "EPSG:27700"})  # type: ignore[arg-type]
        )


def test_unexpected_or_excess_nodata_fails_closed() -> None:
    elevation = _surface("plane")
    one_masked = np.zeros_like(elevation, dtype=bool)
    one_masked[0, 0] = True
    with pytest.raises(SinglePatchValidationError, match="metadata_mismatch"):
        transform_single_patch(TerrainPatch(elevation, one_masked, _metadata()))

    excessive_mask = np.zeros_like(elevation, dtype=bool)
    excessive_mask[:27, :] = True
    with pytest.raises(ValueError, match="nodata_policy_failed"):
        transform_single_patch(
            TerrainPatch(
                elevation, excessive_mask, _metadata(nodata_fraction=float(excessive_mask.mean()))
            )
        )


def test_non_boolean_or_wrong_shape_mask_fails_closed() -> None:
    elevation = _surface("plane")
    with pytest.raises(SinglePatchValidationError, match="boolean"):
        transform_single_patch(TerrainPatch(elevation, np.zeros_like(elevation), _metadata()))
    with pytest.raises(SinglePatchValidationError, match="mask_shape"):
        transform_single_patch(TerrainPatch(elevation, np.zeros((64, 64), dtype=bool), _metadata()))


class _InertTestOnlyModelDouble:
    """Plumbing probe only; its fixed score has zero scientific meaning."""

    model_identifier = ModelIdentifier.E001_FROZEN_RANDOM_FOREST
    model_config_sha256 = FROZEN_CONFIG_SHA256
    model_artifact_sha256 = APPROVED_MODEL_ARTIFACT_SHA256

    def __init__(self, expected: np.ndarray) -> None:
        self.expected = expected
        self.calls = 0

    def score_model_input(self, feature_matrix: np.ndarray) -> float:
        self.calls += 1
        assert feature_matrix.shape == (1, FEATURE_COUNT)
        assert feature_matrix.dtype == np.float32
        assert feature_matrix.flags.writeable is False
        assert np.array_equal(feature_matrix[0], self.expected)
        return 0.25


def test_inert_model_double_receives_exact_vector_once() -> None:
    features = transform_single_patch(_patch())
    adapter = _InertTestOnlyModelDouble(features.feature_vector)
    score = score_single_patch_model_adapter(features, adapter)

    assert adapter.calls == 1
    assert score == 0.25


def test_model_adapter_absence_or_invalid_output_fails_closed() -> None:
    features = transform_single_patch(_patch())
    with pytest.raises(ModelAdapterUnavailableError, match="explicit approved"):
        score_single_patch_model_adapter(features, None)

    class _InvalidOutputDouble:
        model_identifier = ModelIdentifier.E001_FROZEN_RANDOM_FOREST
        model_config_sha256 = FROZEN_CONFIG_SHA256
        model_artifact_sha256 = APPROVED_MODEL_ARTIFACT_SHA256

        def score_model_input(self, feature_matrix: np.ndarray) -> float:
            assert feature_matrix.shape == (1, FEATURE_COUNT)
            return float("nan")

    with pytest.raises(ModelAdapterOutputError, match="finite float"):
        score_single_patch_model_adapter(features, _InvalidOutputDouble())


def test_model_adapter_identity_binding_mismatch_fails_closed() -> None:
    features = transform_single_patch(_patch())
    adapter = _InertTestOnlyModelDouble(features.feature_vector)
    adapter.model_config_sha256 = "a" * 64
    with pytest.raises(ModelAdapterIdentityError, match="identity binding mismatch"):
        score_single_patch_model_adapter(features, adapter)
    assert adapter.calls == 0


def _reference(root: Path, **overrides: object) -> ApprovedModelArtifactReference:
    values: dict[str, object] = {
        "path": root / APPROVED_MODEL_RELATIVE_PATH,
        "model_identifier": ModelIdentifier.E001_FROZEN_RANDOM_FOREST,
        "model_config_sha256": FROZEN_CONFIG_SHA256,
    }
    values.update(overrides)
    return ApprovedModelArtifactReference(**values)  # type: ignore[arg-type]


def test_missing_approved_artifact_fails_without_fallback(tmp_path: Path) -> None:
    with pytest.raises(ModelArtifactUnavailableError, match="retraining is prohibited"):
        verify_approved_model_artifact(tmp_path, _reference(tmp_path))
    assert not (tmp_path / APPROVED_MODEL_RELATIVE_PATH).exists()


def test_changed_or_invalid_artifact_bytes_fail_integrity(tmp_path: Path) -> None:
    path = tmp_path / APPROVED_MODEL_RELATIVE_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes(b"opaque invalid synthetic test bytes")
    with pytest.raises(ModelArtifactIntegrityError, match="SHA-256 mismatch"):
        verify_approved_model_artifact(tmp_path, _reference(tmp_path))


def test_unapproved_identity_configuration_or_path_fails_closed(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unapproved model identity"):
        verify_approved_model_artifact(
            tmp_path,
            _reference(tmp_path, model_identifier="arbitrary-model"),
        )
    with pytest.raises(ValueError, match="configuration identity mismatch"):
        verify_approved_model_artifact(
            tmp_path,
            _reference(tmp_path, model_config_sha256="a" * 64),
        )
    with pytest.raises(ValueError, match="unexpected private model artifact path"):
        verify_approved_model_artifact(
            tmp_path,
            _reference(tmp_path, path=tmp_path / "data/private/alternate.pkl"),
        )


def test_production_result_path_requires_artifact_before_adapter(tmp_path: Path) -> None:
    features = transform_single_patch(_patch())
    adapter = _InertTestOnlyModelDouble(features.feature_vector)
    with pytest.raises(ModelArtifactUnavailableError, match="retraining is prohibited"):
        run_approved_single_patch_inference(tmp_path, _reference(tmp_path), features, adapter)
    assert adapter.calls == 0


def test_verified_production_plumbing_maps_only_to_safe_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    features = transform_single_patch(_patch())
    adapter = _InertTestOnlyModelDouble(features.feature_vector)
    monkeypatch.setattr(
        "archaeoai.inference_system.single_patch.verify_approved_model_artifact",
        lambda project_root, reference: "test-only-verified-boundary",
    )
    result = run_approved_single_patch_inference(tmp_path, _reference(tmp_path), features, adapter)
    payload = result.to_public_dict()
    serialized = json.dumps(payload, sort_keys=True, allow_nan=False).casefold()

    assert adapter.calls == 1
    assert result.terrain_similarity_score == 0.25
    assert result.evidence_level is EvidenceLevel.AI_OUTPUT
    assert result.model_identifier is ModelIdentifier.E001_FROZEN_RANDOM_FOREST
    assert result.model_config_sha256 == FROZEN_CONFIG_SHA256
    assert set(payload) == PUBLIC_RESULT_FIELDS
    assert "private_metadata" not in serialized
    for forbidden in ("easting", "northing", "source_path", "filename", "archaeological discovery"):
        assert forbidden not in serialized


def test_phase5b_core_contains_no_training_loading_or_real_model_execution() -> None:
    source = (
        Path(__file__).resolve().parents[1] / "src/archaeoai/inference_system/single_patch.py"
    ).read_text(encoding="utf-8")
    for forbidden in ("pickle.loads", "predict_proba", ".fit(", "rasterio.open", "urlopen"):
        assert forbidden not in source
