import json
import subprocess
import sys
import tomllib
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from archaeoai.cli import (
    ERROR_PUBLIC_FIELDS,
    FEATURES_PUBLIC_FIELDS,
    INSPECT_PUBLIC_FIELDS,
    ExitCode,
    load_canonical_geotiff,
    main,
)
from archaeoai.inference import FEATURE_COUNT, REPRESENTATION_CHANNELS
from archaeoai.inference_system import TerrainInputMetadata, TerrainPatch, transform_single_patch


def _surface() -> np.ndarray:
    y, x = np.mgrid[-64:64, -64:64]
    return np.asarray(
        100.0 + 1.2 * np.exp(-((x**2 + y**2) / 280.0)) + 0.02 * x,
        dtype=np.float32,
    )


def _write_geotiff(
    path: Path,
    *,
    data: np.ndarray | None = None,
    width: int = 128,
    height: int = 128,
    count: int = 1,
    resolution: float = 1.0,
    crs: str | None = "EPSG:27700",
    nodata: float | None = None,
    tags: dict[str, str] | None = None,
) -> np.ndarray:
    values = _surface() if data is None else data
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=count,
        dtype=str(values.dtype),
        crs=crs,
        transform=from_origin(0.0, float(height) * resolution, resolution, resolution),
        nodata=nodata,
    ) as dataset:
        for band in range(1, count + 1):
            dataset.write(values[:height, :width], band)
        if tags:
            dataset.update_tags(**tags)
    return values[:height, :width]


def _json_output(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    return json.loads(captured.out)


def test_help_version_and_unknown_command_have_stable_exit_behavior(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as help_exit:
        main(["--help"])
    assert help_exit.value.code == int(ExitCode.SUCCESS)
    help_text = capsys.readouterr().out
    assert all(command in help_text for command in ("inspect", "features", "infer"))
    assert "dummy" not in help_text.casefold()
    assert "mock" not in help_text.casefold()
    assert "test-score" not in help_text.casefold()

    with pytest.raises(SystemExit) as version_exit:
        main(["--version"])
    assert version_exit.value.code == int(ExitCode.SUCCESS)
    assert capsys.readouterr().out.strip() == "archaeoai 0.1.0"

    unsafe_command = r"C:\Users\fictional\CONFIRMED_ARCHAEOLOGICAL_DISCOVERY"
    with pytest.raises(SystemExit) as unknown_exit:
        main([unsafe_command])
    assert unknown_exit.value.code == int(ExitCode.INVALID_INPUT)
    error = capsys.readouterr().err
    assert "USAGE_ERROR" in error
    assert unsafe_command not in error
    assert "Traceback" not in error


def test_python_module_entry_point_exposes_safe_help() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "archaeoai", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == int(ExitCode.SUCCESS)
    assert "offline" in completed.stdout.casefold()
    assert completed.stderr == ""


def test_inspect_accepts_canonical_synthetic_geotiff_with_exact_allowlist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "synthetic_patch.tif"
    _write_geotiff(source)

    assert main(["inspect", str(source), "--json"]) == int(ExitCode.SUCCESS)
    payload = _json_output(capsys)
    assert set(payload) == INSPECT_PUBLIC_FIELDS
    assert payload == {
        "band_count": 1,
        "canonical_feature_contract": "COMPATIBLE",
        "command": "inspect",
        "crs": "EPSG:27700",
        "dtype": "float32",
        "finite_value_qa": "PASS",
        "height": 128,
        "input_label": "local_geotiff",
        "model_inference": "NOT_PERFORMED",
        "nodata_fraction": 0.0,
        "nodata_status": "NONE",
        "readable": True,
        "resolution_m": [1.0, 1.0],
        "schema_version": "archaeoai-offline-cli-v1",
        "status": "VALID",
        "width": 128,
    }


def test_inspect_human_output_is_bounded_and_path_free(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "CONFIRMED_ARCHAEOLOGICAL_DISCOVERY_private_identifier.tif"
    _write_geotiff(source)
    assert main(["inspect", str(source)]) == int(ExitCode.SUCCESS)
    output = capsys.readouterr().out
    assert "Status: VALID" in output
    assert "Dimensions: 128 x 128" in output
    assert "Model inference: not performed" in output
    assert str(tmp_path) not in output
    assert source.name not in output
    assert "bounds" not in output.casefold()
    assert "transform" not in output.casefold()
    assert "0.0, 128.0" not in output


def test_file_path_and_direct_phase5b_features_are_bit_exact(tmp_path: Path) -> None:
    source = tmp_path / "synthetic_equivalence.tif"
    values = _write_geotiff(source)
    loaded = load_canonical_geotiff(source)
    direct = transform_single_patch(
        TerrainPatch(
            elevation=values,
            mask=np.zeros_like(values, dtype=bool),
            metadata=TerrainInputMetadata(
                crs="EPSG:27700",
                width=128,
                height=128,
                resolution_m=(1.0, 1.0),
                band_count=1,
                nodata_fraction=0.0,
            ),
        )
    )
    assert loaded.features.feature_vector.shape == (FEATURE_COUNT,)
    assert loaded.features.feature_vector.dtype == np.float32
    assert np.array_equal(loaded.features.feature_vector, direct.feature_vector)


def test_features_reports_contract_without_dumping_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "synthetic_features.tif"
    _write_geotiff(source)
    assert main(["features", str(source), "--json"]) == int(ExitCode.SUCCESS)
    payload = _json_output(capsys)
    assert set(payload) == FEATURES_PUBLIC_FIELDS
    assert payload["feature_shape"] == [FEATURE_COUNT]
    assert payload["feature_dtype"] == "float32"
    assert payload["representation_order"] == list(REPRESENTATION_CHANNELS)
    assert payload["feature_values_exposed"] is False
    assert "feature_values" not in payload
    assert "score" not in json.dumps(payload).casefold()


@pytest.mark.parametrize(
    ("overrides", "expected_fragment"),
    [
        ({"width": 127}, "NONCANONICAL_INPUT"),
        ({"height": 127}, "NONCANONICAL_INPUT"),
        ({"resolution": 2.0}, "NONCANONICAL_INPUT"),
        ({"crs": "EPSG:4326"}, "NONCANONICAL_INPUT"),
        ({"crs": None}, "NONCANONICAL_INPUT"),
        ({"count": 2}, "NONCANONICAL_INPUT"),
    ],
)
def test_noncanonical_geotiff_metadata_fails_without_correction(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    overrides: dict[str, object],
    expected_fragment: str,
) -> None:
    source = tmp_path / "synthetic_invalid_metadata.tif"
    _write_geotiff(source, **overrides)  # type: ignore[arg-type]
    assert main(["inspect", str(source), "--json"]) == int(ExitCode.INVALID_INPUT)
    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert captured.out == ""
    assert set(payload) == ERROR_PUBLIC_FIELDS
    assert payload["error_code"] == expected_fragment
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("invalid_value", [np.nan, np.inf, -np.inf])
def test_unmasked_nonfinite_geotiff_values_fail_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    invalid_value: float,
) -> None:
    values = _surface()
    values[10, 12] = invalid_value
    source = tmp_path / "synthetic_nonfinite.tif"
    _write_geotiff(source, data=values)
    assert main(["features", str(source), "--json"]) == int(ExitCode.INVALID_INPUT)
    payload = json.loads(capsys.readouterr().err)
    assert payload["error_code"] == "NONCANONICAL_INPUT"
    assert payload["model_inference"] == "NOT_PERFORMED"


def test_explicit_nodata_is_reported_without_value_repair(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    values = _surface()
    values[:4, :4] = -9999.0
    source = tmp_path / "synthetic_masked_nodata.tif"
    _write_geotiff(source, data=values, nodata=-9999.0)
    assert main(["inspect", str(source), "--json"]) == int(ExitCode.SUCCESS)
    payload = _json_output(capsys)
    assert payload["nodata_status"] == "EXPLICIT_MASK_PRESENT"
    assert payload["nodata_fraction"] == 16 / (128 * 128)


def test_malformed_or_unsupported_file_fails_with_controlled_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    malformed = tmp_path / "malformed.tif"
    malformed.write_bytes(b"not a GeoTIFF")
    assert main(["inspect", str(malformed), "--json"]) == int(ExitCode.INVALID_INPUT)
    payload = json.loads(capsys.readouterr().err)
    assert payload["error_code"] == "RASTER_UNREADABLE"

    unsupported = tmp_path / "synthetic.txt"
    unsupported.write_text("not terrain", encoding="utf-8")
    assert main(["inspect", str(unsupported), "--json"]) == int(ExitCode.INVALID_INPUT)
    payload = json.loads(capsys.readouterr().err)
    assert payload["error_code"] == "UNSUPPORTED_FORMAT"


def test_non_geotiff_driver_with_tif_suffix_fails_closed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "synthetic_disguised.tif"
    with rasterio.open(
        source,
        "w",
        driver="AAIGrid",
        width=128,
        height=128,
        count=1,
        dtype="float32",
        crs="EPSG:27700",
        transform=from_origin(0.0, 128.0, 1.0, 1.0),
    ) as dataset:
        dataset.write(_surface(), 1)

    assert main(["inspect", str(source), "--json"]) == int(ExitCode.INVALID_INPUT)
    payload = json.loads(capsys.readouterr().err)
    assert payload["error_code"] == "UNSUPPORTED_FORMAT"


def test_arbitrary_tags_urls_claims_coordinates_and_huge_strings_never_render(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    injected = {
        "source_path": r"C:\Users\fictional\private.tif",
        "url": "https://example.invalid/private",
        "nested": json.dumps({"easting": 123456, "northing": 654321}),
        "claim": "CONFIRMED ARCHAEOLOGICAL DISCOVERY",
        "huge": "X" * 20_000,
    }
    source = tmp_path / "synthetic_malicious_tags.tif"
    _write_geotiff(source, tags=injected)
    assert main(["inspect", str(source), "--json"]) == int(ExitCode.SUCCESS)
    serialized = json.dumps(_json_output(capsys), sort_keys=True)
    for forbidden in injected.values():
        assert forbidden not in serialized
    assert "easting" not in serialized.casefold()
    assert "northing" not in serialized.casefold()


@pytest.mark.parametrize(
    "private_path",
    [
        r"C:\Users\fictional\private-terrain.tif",
        "/home/fictional/private-terrain.tif",
        "https://example.invalid/private-terrain.tif",
    ],
)
def test_missing_path_errors_never_echo_windows_posix_or_url_inputs(
    capsys: pytest.CaptureFixture[str], private_path: str
) -> None:
    assert main(["inspect", private_path, "--json"]) == int(ExitCode.INVALID_INPUT)
    captured = capsys.readouterr()
    assert private_path not in captured.err
    assert "FILE_UNAVAILABLE" in captured.err
    assert "Traceback" not in captured.err


def test_infer_without_model_fails_before_reading_terrain(
    capsys: pytest.CaptureFixture[str],
) -> None:
    private_input = r"C:\Users\fictional\private-terrain.tif"
    assert main(["infer", private_input, "--json"]) == int(ExitCode.MODEL_UNAVAILABLE)
    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert set(payload) == ERROR_PUBLIC_FIELDS
    assert payload["error_code"] == "MODEL_UNAVAILABLE"
    assert payload["model_inference"] == "NOT_PERFORMED"
    assert private_input not in captured.err
    assert "score" not in captured.err.casefold()


def test_infer_rejects_wrong_hash_without_loading_or_scoring(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pyproject.toml").write_text("[project]\nname='synthetic'\n", encoding="utf-8")
    artifact = tmp_path / "data/private/e001/inference/e001_phase2f_random_forest.pkl"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"fictional invalid artifact bytes, not model weights")
    assert main(["infer", "synthetic.tif", "--model", str(artifact), "--json"]) == int(
        ExitCode.ARTIFACT_INTEGRITY
    )
    payload = json.loads(capsys.readouterr().err)
    assert payload["error_code"] == "ARTIFACT_INTEGRITY"
    assert payload["model_inference"] == "NOT_PERFORMED"


def test_infer_configuration_or_authorization_boundaries_are_fail_closed(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "archaeoai.cli.verify_approved_model_artifact",
        lambda project_root, reference: (_ for _ in ()).throw(ValueError("fictional mismatch")),
    )
    assert main(["infer", "synthetic.tif", "--model", str(tmp_path), "--json"]) == int(
        ExitCode.CONFIGURATION_MISMATCH
    )
    assert json.loads(capsys.readouterr().err)["error_code"] == "CONFIGURATION_MISMATCH"

    monkeypatch.setattr(
        "archaeoai.cli.verify_approved_model_artifact",
        lambda project_root, reference: "test-only verified boundary",
    )
    assert main(["infer", "synthetic.tif", "--model", str(tmp_path), "--json"]) == int(
        ExitCode.MODEL_UNAVAILABLE
    )
    payload = json.loads(capsys.readouterr().err)
    assert payload["error_code"] == "MODEL_NOT_AUTHORIZED"
    assert payload["model_inference"] == "NOT_PERFORMED"


def test_unexpected_internal_error_is_bounded_without_traceback(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "archaeoai.cli.load_canonical_geotiff",
        lambda path: (_ for _ in ()).throw(RuntimeError("private implementation detail")),
    )
    assert main(["inspect", str(tmp_path), "--json"]) == int(ExitCode.INTERNAL_ERROR)
    captured = capsys.readouterr()
    assert set(json.loads(captured.err)) == ERROR_PUBLIC_FIELDS
    assert "private implementation detail" not in captured.err
    assert "Traceback" not in captured.err


def test_cli_source_has_no_model_execution_training_download_or_test_switches() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/archaeoai/cli.py").read_text(encoding="utf-8")
    for forbidden in (
        "pickle.loads",
        "predict_proba",
        ".fit(",
        "urlopen",
        "requests.",
        "--dummy-model",
        "--mock",
        "--fake-prediction",
        "--test-score",
    ):
        assert forbidden not in source
    assert not (root / "src/archaeoai/inference_system/api.py").exists()


def test_phase5c_packaging_and_documentation_preserve_bounded_status() -> None:
    root = Path(__file__).resolve().parents[1]
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["scripts"] == {"archaeoai": "archaeoai.cli:main"}

    required_text = {
        "README.md": "Phase 5C complete",
        "docs/CURRENT_STATUS.md": "Phase 5C has completed",
        "docs/architecture/PHASE_5_INFERENCE_ARCHITECTURE.md": (
            "Complete and merged; synthetic validation only; model execution disabled"
        ),
        "docs/roadmap.md": "Complete; synthetic validation only; inference disabled",
        "docs/reproducibility.md": "Phase 5C offline single-patch CLI",
        "research-log/2026-09-05-phase-5c-offline-cli.md": ("does not authorize model execution"),
    }
    combined = []
    for relative_path, expected in required_text.items():
        text = (root / relative_path).read_text(encoding="utf-8")
        assert expected in text
        combined.append(text)
    documentation = "\n".join(combined)
    assert "RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW" in documentation
    assert "no archaeological discovery claim" in documentation.casefold()
