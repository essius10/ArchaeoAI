import json
import shutil
from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin

from archaeoai.cli import ExitCode, main
from archaeoai.inference import FEATURE_COUNT, REPRESENTATION_CHANNELS
from archaeoai.inference_system import (
    BATCH_MANIFEST_SCHEMA_VERSION,
    MAX_BATCH_ITEMS,
    MAX_CUMULATIVE_INPUT_BYTES,
    MAX_MANIFEST_BYTES,
    MAX_SINGLE_FILE_BYTES,
    BatchManifestError,
    BatchManifestErrorCode,
    BatchProcessingError,
    TerrainInputMetadata,
    TerrainPatch,
    load_batch_manifest,
    run_feature_batch,
    transform_single_patch,
)
from archaeoai.inference_system.batch import (
    BATCH_ITEM_PUBLIC_FIELDS,
    BATCH_PUBLIC_FIELDS,
)
from archaeoai.inference_system.geotiff import load_canonical_geotiff as read_geotiff


def _surface(kind: str) -> np.ndarray:
    y, x = np.mgrid[-64:64, -64:64]
    if kind == "plane":
        values = 100.0 + (0.02 * x) + (0.01 * y)
    elif kind == "mound":
        values = 100.0 + 1.5 * np.exp(-((x**2 + y**2) / 260.0))
    elif kind == "depression":
        values = 100.0 - 1.1 * np.exp(-((x**2 + y**2) / 340.0))
    elif kind == "sinusoid":
        values = 100.0 + 0.3 * np.sin(x / 7.0) + 0.2 * np.cos(y / 9.0)
    elif kind == "noise":
        values = 100.0 + np.random.default_rng(20260905).normal(0.0, 0.05, (128, 128))
    else:
        raise ValueError("unknown synthetic surface")
    return np.asarray(values, dtype=np.float32)


def _write_geotiff(
    path: Path,
    kind: str,
    *,
    crs: str = "EPSG:27700",
    tags: dict[str, str] | None = None,
) -> np.ndarray:
    values = _surface(kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=128,
        height=128,
        count=1,
        dtype="float32",
        crs=crs,
        transform=from_origin(0.0, 128.0, 1.0, 1.0),
    ) as dataset:
        dataset.write(values, 1)
        if tags:
            dataset.update_tags(**tags)
    return values


def _write_manifest(path: Path, items: list[dict[str, object]]) -> Path:
    path.write_text(
        json.dumps({"schema_version": BATCH_MANIFEST_SCHEMA_VERSION, "items": items}),
        encoding="utf-8",
    )
    return path


def _direct_features(values: np.ndarray) -> np.ndarray:
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
    return direct.feature_vector


def _snapshot(root: Path) -> set[str]:
    return {path.relative_to(root).as_posix() for path in root.rglob("*")}


def test_manifest_is_strict_and_items_are_sorted_by_opaque_id(tmp_path: Path) -> None:
    _write_geotiff(tmp_path / "second.tif", "mound")
    _write_geotiff(tmp_path / "first.tif", "plane")
    source = _write_manifest(
        tmp_path / "batch.json",
        [
            {"item_id": "item-0002", "terrain": "second.tif"},
            {"item_id": "item-0001", "terrain": "first.tif"},
        ],
    )
    manifest = load_batch_manifest(source)
    assert [item.item_id for item in manifest.items] == ["item-0001", "item-0002"]
    assert str(tmp_path) not in repr(manifest)
    assert "content_sha256" not in repr(manifest)


@pytest.mark.parametrize("kind", ["plane", "mound", "depression", "sinusoid", "noise"])
def test_batch_features_are_bit_exact_to_direct_phase5b_for_each_surface(
    tmp_path: Path, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    values = _write_geotiff(tmp_path / f"synthetic_{kind}.tif", kind)
    manifest = load_batch_manifest(
        _write_manifest(
            tmp_path / "batch.json",
            [{"item_id": "item-0001", "terrain": f"synthetic_{kind}.tif"}],
        )
    )
    observed: dict[str, np.ndarray] = {}

    def capture(path: Path) -> object:
        loaded = read_geotiff(path)
        observed[manifest.items[0].item_id] = loaded.features.feature_vector.copy()
        return loaded

    monkeypatch.setattr("archaeoai.inference_system.batch.load_canonical_geotiff", capture)
    result = run_feature_batch(manifest)
    assert result.accepted_items == 1
    assert result.invalid_items == 0
    assert observed["item-0001"].shape == (FEATURE_COUNT,)
    assert observed["item-0001"].dtype == np.float32
    assert np.array_equal(observed["item-0001"], _direct_features(values))


def test_batch_json_is_deterministic_and_uses_exact_allowlists(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_geotiff(tmp_path / "a.tif", "plane")
    _write_geotiff(tmp_path / "b.tif", "mound")
    source = _write_manifest(
        tmp_path / "batch.json",
        [
            {"item_id": "item-0002", "terrain": "b.tif"},
            {"item_id": "item-0001", "terrain": "a.tif"},
        ],
    )
    assert main(["batch-features", str(source), "--json"]) == int(ExitCode.SUCCESS)
    first_text = capsys.readouterr().out
    assert main(["batch-features", str(source), "--json"]) == int(ExitCode.SUCCESS)
    second_text = capsys.readouterr().out
    assert first_text == second_text

    payload = json.loads(first_text)
    assert set(payload) == BATCH_PUBLIC_FIELDS
    assert payload["status"] == "COMPLETE"
    assert payload["total_items"] == payload["accepted_items"] == 2
    assert payload["invalid_items"] == payload["processing_failures"] == 0
    assert payload["feature_count"] == FEATURE_COUNT
    assert payload["feature_dtype"] == "float32"
    assert payload["representation_order"] == list(REPRESENTATION_CHANNELS)
    assert payload["model_execution"] == "NOT_PERFORMED"
    assert payload["retention_policy"] == "NO_INPUT_RETENTION"
    assert payload["temporary_artifacts_retained"] is False
    assert [item["item_id"] for item in payload["item_results"]] == [
        "item-0001",
        "item-0002",
    ]
    assert all(set(item) == BATCH_ITEM_PUBLIC_FIELDS for item in payload["item_results"])
    serialized = json.dumps(payload, sort_keys=True)
    assert "feature_vector" not in serialized
    assert "feature_values" not in serialized
    assert "terrain_similarity_score" not in serialized
    assert "probability" not in serialized.casefold()


def test_human_output_is_aggregate_only_and_path_free(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    private_name = "CONFIRMED_ARCHAEOLOGICAL_DISCOVERY_user_private_123456_654321.tif"
    _write_geotiff(tmp_path / private_name, "plane")
    source = _write_manifest(
        tmp_path / "private_owner_manifest.json",
        [{"item_id": "item-0001", "terrain": private_name}],
    )
    assert main(["batch-features", str(source)]) == int(ExitCode.SUCCESS)
    output = capsys.readouterr().out
    assert "Status: COMPLETE" in output
    assert "Submitted: 1" in output
    assert "Model execution: not performed" in output
    assert str(tmp_path) not in output
    assert private_name not in output
    assert source.name not in output
    assert "item-0001" not in output
    assert "123456" not in output
    assert "654321" not in output


def test_invalid_items_are_recorded_and_processing_continues_deterministically(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write_geotiff(tmp_path / "valid.tif", "plane")
    _write_geotiff(tmp_path / "wrong_crs.tif", "mound", crs="EPSG:4326")
    source = _write_manifest(
        tmp_path / "batch.json",
        [
            {"item_id": "item-0002", "terrain": "wrong_crs.tif"},
            {"item_id": "item-0001", "terrain": "valid.tif"},
        ],
    )
    assert main(["batch-features", str(source), "--json"]) == int(ExitCode.INVALID_INPUT)
    captured = capsys.readouterr()
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["status"] == "COMPLETE_WITH_INVALID_ITEMS"
    assert payload["accepted_items"] == 1
    assert payload["invalid_items"] == 1
    assert payload["processing_failures"] == 0
    assert payload["item_results"] == [
        {
            "error_code": "NONE",
            "feature_preparation": "SUCCEEDED",
            "item_id": "item-0001",
            "model_execution": "NOT_PERFORMED",
            "status": "FEATURES_READY",
        },
        {
            "error_code": "NONCANONICAL_INPUT",
            "feature_preparation": "FAILED",
            "item_id": "item-0002",
            "model_execution": "NOT_PERFORMED",
            "status": "INVALID_INPUT",
        },
    ]


def test_multiple_invalid_items_are_never_silently_skipped(tmp_path: Path) -> None:
    (tmp_path / "broken.tif").write_bytes(b"not a GeoTIFF")
    _write_geotiff(tmp_path / "wrong.tif", "plane", crs="EPSG:4326")
    manifest = load_batch_manifest(
        _write_manifest(
            tmp_path / "batch.json",
            [
                {"item_id": "item-0002", "terrain": "wrong.tif"},
                {"item_id": "item-0001", "terrain": "broken.tif"},
            ],
        )
    )
    result = run_feature_batch(manifest)
    assert result.accepted_items == 0
    assert result.invalid_items == 2
    assert [item.error_code for item in result.items] == [
        "RASTER_UNREADABLE",
        "NONCANONICAL_INPUT",
    ]


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        ({}, BatchManifestErrorCode.MANIFEST_SCHEMA_MISMATCH),
        ({"schema_version": "wrong", "items": []}, BatchManifestErrorCode.MANIFEST_SCHEMA_MISMATCH),
        (
            {"schema_version": BATCH_MANIFEST_SCHEMA_VERSION, "items": [], "metadata": {}},
            BatchManifestErrorCode.MANIFEST_SCHEMA_MISMATCH,
        ),
        (
            {
                "schema_version": BATCH_MANIFEST_SCHEMA_VERSION,
                "items": [{"item_id": "item-0001", "terrain": "a.tif", "metadata": {}}],
            },
            BatchManifestErrorCode.INVALID_ITEM,
        ),
        (
            {
                "schema_version": BATCH_MANIFEST_SCHEMA_VERSION,
                "items": [{"item_id": "descriptive-coordinate-123456", "terrain": "a.tif"}],
            },
            BatchManifestErrorCode.INVALID_ITEM,
        ),
    ],
)
def test_schema_rejects_empty_extra_nested_or_descriptive_content(
    tmp_path: Path, payload: dict[str, object], code: BatchManifestErrorCode
) -> None:
    source = tmp_path / "batch.json"
    source.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(BatchManifestError, match=code.value) as caught:
        load_batch_manifest(source)
    assert caught.value.code is code
    assert str(tmp_path) not in str(caught.value)


def test_malformed_duplicate_key_and_oversized_manifests_fail_before_processing(
    tmp_path: Path,
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{not-json", encoding="utf-8")
    with pytest.raises(BatchManifestError) as caught:
        load_batch_manifest(malformed)
    assert caught.value.code is BatchManifestErrorCode.MALFORMED_MANIFEST

    duplicate_key = tmp_path / "duplicate.json"
    duplicate_key.write_text(
        '{"schema_version":"archaeoai-batch-manifest-v1",'
        '"schema_version":"archaeoai-batch-manifest-v1","items":[]}',
        encoding="utf-8",
    )
    with pytest.raises(BatchManifestError) as caught:
        load_batch_manifest(duplicate_key)
    assert caught.value.code is BatchManifestErrorCode.MALFORMED_MANIFEST

    oversized = tmp_path / "oversized.json"
    oversized.write_text("X" * (MAX_MANIFEST_BYTES + 1), encoding="utf-8")
    with pytest.raises(BatchManifestError) as caught:
        load_batch_manifest(oversized)
    assert caught.value.code is BatchManifestErrorCode.MANIFEST_TOO_LARGE


def test_item_count_limit_is_enforced_before_file_access(tmp_path: Path) -> None:
    items = [
        {"item_id": f"item-{index:04d}", "terrain": "missing.tif"}
        for index in range(1, MAX_BATCH_ITEMS + 2)
    ]
    with pytest.raises(BatchManifestError) as caught:
        load_batch_manifest(_write_manifest(tmp_path / "batch.json", items))
    assert caught.value.code is BatchManifestErrorCode.ITEM_LIMIT_EXCEEDED


def test_duplicate_ids_references_and_byte_identical_content_are_distinct_failures(
    tmp_path: Path,
) -> None:
    _write_geotiff(tmp_path / "a.tif", "plane")
    _write_geotiff(tmp_path / "b.tif", "mound")

    duplicate_id = _write_manifest(
        tmp_path / "duplicate_id.json",
        [
            {"item_id": "item-0001", "terrain": "a.tif"},
            {"item_id": "item-0001", "terrain": "b.tif"},
        ],
    )
    with pytest.raises(BatchManifestError) as caught:
        load_batch_manifest(duplicate_id)
    assert caught.value.code is BatchManifestErrorCode.DUPLICATE_ITEM_ID

    duplicate_reference = _write_manifest(
        tmp_path / "duplicate_reference.json",
        [
            {"item_id": "item-0001", "terrain": "a.tif"},
            {"item_id": "item-0002", "terrain": "a.tif"},
        ],
    )
    with pytest.raises(BatchManifestError) as caught:
        load_batch_manifest(duplicate_reference)
    assert caught.value.code is BatchManifestErrorCode.DUPLICATE_FILE_REFERENCE

    shutil.copyfile(tmp_path / "a.tif", tmp_path / "copy.tif")
    duplicate_content = _write_manifest(
        tmp_path / "duplicate_content.json",
        [
            {"item_id": "item-0001", "terrain": "a.tif"},
            {"item_id": "item-0002", "terrain": "copy.tif"},
        ],
    )
    with pytest.raises(BatchManifestError) as caught:
        load_batch_manifest(duplicate_content)
    assert caught.value.code is BatchManifestErrorCode.DUPLICATE_FILE_CONTENT


@pytest.mark.parametrize(
    "unsafe_reference",
    [
        "../escape.tif",
        "/home/fictional/private.tif",
        r"C:\Users\fictional\private.tif",
        "https://example.invalid/private.tif",
        "nested/../../escape.tif",
    ],
)
def test_path_escape_windows_posix_and_url_references_fail_closed(
    tmp_path: Path, unsafe_reference: str
) -> None:
    source = _write_manifest(
        tmp_path / "batch.json",
        [{"item_id": "item-0001", "terrain": unsafe_reference}],
    )
    with pytest.raises(BatchManifestError) as caught:
        load_batch_manifest(source)
    assert caught.value.code is BatchManifestErrorCode.PATH_ESCAPE
    assert unsafe_reference not in str(caught.value)


def test_directory_and_unsupported_extension_are_rejected(tmp_path: Path) -> None:
    (tmp_path / "directory.tif").mkdir()
    source = _write_manifest(
        tmp_path / "directory.json",
        [{"item_id": "item-0001", "terrain": "directory.tif"}],
    )
    with pytest.raises(BatchManifestError) as caught:
        load_batch_manifest(source)
    assert caught.value.code is BatchManifestErrorCode.INVALID_ITEM

    (tmp_path / "terrain.txt").write_text("fictional", encoding="utf-8")
    source = _write_manifest(
        tmp_path / "extension.json",
        [{"item_id": "item-0001", "terrain": "terrain.txt"}],
    )
    with pytest.raises(BatchManifestError) as caught:
        load_batch_manifest(source)
    assert caught.value.code is BatchManifestErrorCode.INVALID_ITEM


def test_symlink_inputs_are_rejected_when_platform_supports_them(tmp_path: Path) -> None:
    _write_geotiff(tmp_path / "target.tif", "plane")
    link = tmp_path / "link.tif"
    try:
        link.symlink_to(tmp_path / "target.tif")
    except OSError:
        pytest.skip("symlink creation is unavailable in this test environment")
    source = _write_manifest(
        tmp_path / "batch.json",
        [{"item_id": "item-0001", "terrain": "link.tif"}],
    )
    with pytest.raises(BatchManifestError) as caught:
        load_batch_manifest(source)
    assert caught.value.code is BatchManifestErrorCode.SYMLINK_NOT_ALLOWED


def test_per_file_and_cumulative_byte_limits_are_enforced(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.tif"
    oversized.write_bytes(b"X" * (MAX_SINGLE_FILE_BYTES + 1))
    source = _write_manifest(
        tmp_path / "single.json",
        [{"item_id": "item-0001", "terrain": "oversized.tif"}],
    )
    with pytest.raises(BatchManifestError) as caught:
        load_batch_manifest(source)
    assert caught.value.code is BatchManifestErrorCode.FILE_TOO_LARGE

    items = []
    chunk_size = (MAX_CUMULATIVE_INPUT_BYTES // 9) + 1
    for index in range(1, 10):
        path = tmp_path / f"chunk_{index}.tif"
        path.write_bytes(bytes([index]) + (b"X" * (chunk_size - 1)))
        items.append({"item_id": f"item-{index:04d}", "terrain": path.name})
    source = _write_manifest(tmp_path / "cumulative.json", items)
    with pytest.raises(BatchManifestError) as caught:
        load_batch_manifest(source)
    assert caught.value.code is BatchManifestErrorCode.CUMULATIVE_SIZE_EXCEEDED


def test_input_changed_after_admission_is_reported_without_processing(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.tif"
    _write_geotiff(path, "plane")
    manifest = load_batch_manifest(
        _write_manifest(
            tmp_path / "batch.json",
            [{"item_id": "item-0001", "terrain": "synthetic.tif"}],
        )
    )
    path.write_bytes(b"changed after admission")
    result = run_feature_batch(manifest)
    assert result.invalid_items == 1
    assert result.items[0].error_code == "INPUT_CHANGED_AFTER_ADMISSION"


def test_success_invalid_manifest_and_unexpected_failure_retain_no_temporary_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_geotiff(tmp_path / "synthetic.tif", "plane")
    source = _write_manifest(
        tmp_path / "batch.json",
        [{"item_id": "item-0001", "terrain": "synthetic.tif"}],
    )
    before = _snapshot(tmp_path)
    manifest = load_batch_manifest(source)
    run_feature_batch(manifest)
    assert _snapshot(tmp_path) == before

    malformed = tmp_path / "malformed.json"
    malformed.write_text("not JSON", encoding="utf-8")
    before_malformed = _snapshot(tmp_path)
    with pytest.raises(BatchManifestError):
        load_batch_manifest(malformed)
    assert _snapshot(tmp_path) == before_malformed

    monkeypatch.setattr(
        "archaeoai.inference_system.batch.load_canonical_geotiff",
        lambda path: (_ for _ in ()).throw(RuntimeError("private internal detail")),
    )
    before_failure = _snapshot(tmp_path)
    with pytest.raises(BatchProcessingError, match="failed safely") as caught:
        run_feature_batch(manifest)
    assert "private internal detail" not in str(caught.value)
    assert _snapshot(tmp_path) == before_failure


def test_cli_expected_manifest_errors_are_path_free_and_have_no_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    private_path = tmp_path / "owner_private_manifest.json"
    private_path.write_text("not JSON", encoding="utf-8")
    assert main(["batch-features", str(private_path), "--json"]) == int(ExitCode.INVALID_INPUT)
    captured = capsys.readouterr()
    assert captured.out == ""
    payload = json.loads(captured.err)
    assert payload["command"] == "batch-features"
    assert payload["error_code"] == "MALFORMED_MANIFEST"
    assert str(tmp_path) not in captured.err
    assert private_path.name not in captured.err
    assert "Traceback" not in captured.err


def test_malicious_metadata_never_flows_to_batch_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    injected = {
        "windows": r"C:\Users\fictional\private.tif",
        "posix": "/home/fictional/private.tif",
        "url": "https://example.invalid/private",
        "coordinates": json.dumps({"easting": 123456, "northing": 654321}),
        "claim": "CONFIRMED ARCHAEOLOGICAL EVIDENCE",
        "huge": "Z" * 20_000,
        "model": r"C:\private\model.pkl",
    }
    _write_geotiff(tmp_path / "malicious_tags.tif", "plane", tags=injected)
    source = _write_manifest(
        tmp_path / "batch.json",
        [{"item_id": "item-0001", "terrain": "malicious_tags.tif"}],
    )
    assert main(["batch-features", str(source), "--json"]) == int(ExitCode.SUCCESS)
    output = capsys.readouterr().out
    for value in injected.values():
        assert value not in output
    assert "easting" not in output.casefold()
    assert "northing" not in output.casefold()
    assert "model.pkl" not in output


def test_batch_cli_exposes_no_model_test_double_concurrency_or_unsafe_option(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as help_exit:
        main(["batch-features", "--help"])
    assert help_exit.value.code == int(ExitCode.SUCCESS)
    help_text = capsys.readouterr().out.casefold()
    assert "--json" in help_text
    for forbidden in (
        "--model",
        "--dummy",
        "--mock",
        "--score",
        "--workers",
        "--retain",
        "--cache",
        "--output",
    ):
        assert forbidden not in help_text

    private_model = r"C:\Users\fictional\approved-private-model.pkl"
    with pytest.raises(SystemExit) as rejected:
        main(["batch-features", "synthetic_batch.json", "--model", private_model])
    assert rejected.value.code == int(ExitCode.INVALID_INPUT)
    error = capsys.readouterr().err
    assert private_model not in error
    assert "USAGE_ERROR" in error
    assert "Traceback" not in error


def test_batch_source_has_no_model_execution_training_network_temp_or_concurrency() -> None:
    root = Path(__file__).resolve().parents[1]
    source = (root / "src/archaeoai/inference_system/batch.py").read_text(encoding="utf-8")
    cli = (root / "src/archaeoai/cli.py").read_text(encoding="utf-8")
    for forbidden in (
        "predict_proba",
        "pickle.loads",
        ".fit(",
        "urlopen",
        "requests.",
        "TemporaryDirectory",
        "NamedTemporaryFile",
        "ThreadPool",
        "ProcessPool",
        "concurrent.futures",
    ):
        assert forbidden not in source
    assert "batch-features" in cli
    assert 'batch.add_argument("--model"' not in cli
    assert not (root / "src/archaeoai/inference_system/api.py").exists()


def test_phase5d_example_and_documentation_preserve_bounded_status() -> None:
    root = Path(__file__).resolve().parents[1]
    example = json.loads((root / "configs/phase5d-batch.example.json").read_text(encoding="utf-8"))
    assert set(example) == {"schema_version", "items"}
    assert example["schema_version"] == BATCH_MANIFEST_SCHEMA_VERSION
    assert all(set(item) == {"item_id", "terrain"} for item in example["items"])

    required_text = {
        "README.md": "Phase 5D complete",
        "docs/CURRENT_STATUS.md": "Phase 5D has completed",
        "docs/architecture/PHASE_5_INFERENCE_ARCHITECTURE.md": (
            "Complete and ready for review; synthetic validation only; "
            "no retention or model execution"
        ),
        "docs/roadmap.md": ("Complete; synthetic validation only; no model execution or retention"),
        "docs/reproducibility.md": "Phase 5D bounded batch feature preparation",
        "research-log/2026-09-05-phase-5d-bounded-batch.md": (
            "did not load or execute the approved"
        ),
    }
    combined = []
    for relative_path, expected in required_text.items():
        text = (root / relative_path).read_text(encoding="utf-8")
        assert expected in text
        combined.append(text)
    documentation = "\n".join(combined)
    assert "RQ1_PROVISIONALLY_ANSWERED_PENDING_REVIEW" in documentation
    assert "no archaeological discovery claim" in documentation.casefold()
