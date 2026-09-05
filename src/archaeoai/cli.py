"""Offline, privacy-bounded single-patch command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from enum import IntEnum, StrEnum
from pathlib import Path
from types import MappingProxyType

from archaeoai import __version__
from archaeoai.inference import FEATURE_COUNT, REPRESENTATION_CHANNELS
from archaeoai.inference_system import (
    ApprovedModelArtifactReference,
    ModelArtifactIntegrityError,
    ModelArtifactUnavailableError,
    ModelIdentifier,
    verify_approved_model_artifact,
)
from archaeoai.inference_system.batch import (
    BatchManifestError,
    load_batch_manifest,
    run_feature_batch,
)
from archaeoai.inference_system.contracts import APPROVED_MODEL_CONFIG_SHA256
from archaeoai.inference_system.geotiff import (
    CanonicalGeoTIFF,
    GeoTIFFValidationError,
)
from archaeoai.inference_system.geotiff import (
    load_canonical_geotiff as _load_canonical_geotiff,
)
from archaeoai.paths import ProjectPathError, find_project_root

SCHEMA_VERSION = "archaeoai-offline-cli-v1"
INPUT_LABEL = "local_geotiff"
MODEL_NOT_PERFORMED = "NOT_PERFORMED"
INSPECT_PUBLIC_FIELDS = frozenset(
    {
        "schema_version",
        "command",
        "status",
        "input_label",
        "readable",
        "width",
        "height",
        "band_count",
        "crs",
        "resolution_m",
        "dtype",
        "nodata_status",
        "nodata_fraction",
        "finite_value_qa",
        "canonical_feature_contract",
        "model_inference",
    }
)
FEATURES_PUBLIC_FIELDS = frozenset(
    {
        "schema_version",
        "command",
        "status",
        "input_label",
        "feature_shape",
        "feature_dtype",
        "representation_order",
        "feature_values_exposed",
        "model_inference",
    }
)
ERROR_PUBLIC_FIELDS = frozenset(
    {
        "schema_version",
        "command",
        "status",
        "error_code",
        "message",
        "model_inference",
    }
)


class ExitCode(IntEnum):
    """Stable Phase 5C process exit codes."""

    SUCCESS = 0
    INVALID_INPUT = 2
    MODEL_UNAVAILABLE = 3
    ARTIFACT_INTEGRITY = 4
    CONFIGURATION_MISMATCH = 5
    INTERNAL_ERROR = 10


class CliErrorCode(StrEnum):
    """Controlled public error categories."""

    USAGE_ERROR = "USAGE_ERROR"
    FILE_UNAVAILABLE = "FILE_UNAVAILABLE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    RASTER_UNREADABLE = "RASTER_UNREADABLE"
    NONCANONICAL_INPUT = "NONCANONICAL_INPUT"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    MODEL_NOT_AUTHORIZED = "MODEL_NOT_AUTHORIZED"
    ARTIFACT_INTEGRITY = "ARTIFACT_INTEGRITY"
    CONFIGURATION_MISMATCH = "CONFIGURATION_MISMATCH"
    MANIFEST_UNAVAILABLE = "MANIFEST_UNAVAILABLE"
    MANIFEST_TOO_LARGE = "MANIFEST_TOO_LARGE"
    MALFORMED_MANIFEST = "MALFORMED_MANIFEST"
    MANIFEST_SCHEMA_MISMATCH = "MANIFEST_SCHEMA_MISMATCH"
    ITEM_LIMIT_EXCEEDED = "ITEM_LIMIT_EXCEEDED"
    INVALID_ITEM = "INVALID_ITEM"
    DUPLICATE_ITEM_ID = "DUPLICATE_ITEM_ID"
    DUPLICATE_FILE_REFERENCE = "DUPLICATE_FILE_REFERENCE"
    DUPLICATE_FILE_CONTENT = "DUPLICATE_FILE_CONTENT"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    CUMULATIVE_SIZE_EXCEEDED = "CUMULATIVE_SIZE_EXCEEDED"
    PATH_ESCAPE = "PATH_ESCAPE"
    SYMLINK_NOT_ALLOWED = "SYMLINK_NOT_ALLOWED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


ERROR_MESSAGES = MappingProxyType(
    {
        CliErrorCode.USAGE_ERROR: "Invalid command or arguments.",
        CliErrorCode.FILE_UNAVAILABLE: "The local GeoTIFF is unavailable or unreadable.",
        CliErrorCode.UNSUPPORTED_FORMAT: "The input must be a local .tif or .tiff GeoTIFF.",
        CliErrorCode.RASTER_UNREADABLE: "The input could not be read as a GeoTIFF.",
        CliErrorCode.NONCANONICAL_INPUT: (
            "The GeoTIFF does not satisfy the frozen single-patch input contract; "
            "no correction was applied."
        ),
        CliErrorCode.MODEL_UNAVAILABLE: (
            "Inference unavailable: the approved private model artifact was not supplied."
        ),
        CliErrorCode.MODEL_NOT_AUTHORIZED: (
            "Inference unavailable: approved private model execution is not authorized in Phase 5C."
        ),
        CliErrorCode.ARTIFACT_INTEGRITY: (
            "Inference unavailable: approved model artifact integrity verification failed."
        ),
        CliErrorCode.CONFIGURATION_MISMATCH: (
            "Inference unavailable: model identity, configuration, or private path is invalid."
        ),
        CliErrorCode.MANIFEST_UNAVAILABLE: (
            "The local batch manifest is unavailable or is not a JSON file."
        ),
        CliErrorCode.MANIFEST_TOO_LARGE: "The batch manifest exceeds the fixed size limit.",
        CliErrorCode.MALFORMED_MANIFEST: "The batch manifest is not valid strict JSON.",
        CliErrorCode.MANIFEST_SCHEMA_MISMATCH: (
            "The batch manifest does not satisfy the fixed Phase 5D schema."
        ),
        CliErrorCode.ITEM_LIMIT_EXCEEDED: "The batch exceeds the fixed item-count limit.",
        CliErrorCode.INVALID_ITEM: "A batch item does not satisfy the fixed admission contract.",
        CliErrorCode.DUPLICATE_ITEM_ID: "The batch contains a duplicate opaque item ID.",
        CliErrorCode.DUPLICATE_FILE_REFERENCE: (
            "The batch contains a duplicate terrain-file reference."
        ),
        CliErrorCode.DUPLICATE_FILE_CONTENT: (
            "The batch contains byte-identical terrain-file content."
        ),
        CliErrorCode.FILE_TOO_LARGE: "A terrain file exceeds the fixed per-file size limit.",
        CliErrorCode.CUMULATIVE_SIZE_EXCEEDED: (
            "The batch exceeds the fixed cumulative input-size limit."
        ),
        CliErrorCode.PATH_ESCAPE: (
            "A terrain reference escapes the manifest's authorized input directory."
        ),
        CliErrorCode.SYMLINK_NOT_ALLOWED: "Symbolic links are not accepted by the batch boundary.",
        CliErrorCode.INTERNAL_ERROR: "The offline operation failed safely.",
    }
)


class CliExpectedError(Exception):
    """An expected bounded CLI error whose original details remain private."""

    def __init__(self, code: CliErrorCode, exit_code: ExitCode):
        self.code = code
        self.exit_code = exit_code
        super().__init__(ERROR_MESSAGES[code])


class SafeArgumentParser(argparse.ArgumentParser):
    """Prevent argparse from echoing arbitrary user input in errors."""

    def error(self, message: str) -> None:
        del message
        self.print_usage(sys.stderr)
        self.exit(
            int(ExitCode.INVALID_INPUT),
            f"ERROR [{CliErrorCode.USAGE_ERROR.value}]: "
            f"{ERROR_MESSAGES[CliErrorCode.USAGE_ERROR]}\n",
        )


def load_canonical_geotiff(path: str | Path) -> CanonicalGeoTIFF:
    """Map the reusable GeoTIFF reader onto controlled CLI failures."""
    try:
        return _load_canonical_geotiff(path)
    except GeoTIFFValidationError as exc:
        raise CliExpectedError(CliErrorCode(exc.code.value), ExitCode.INVALID_INPUT) from exc


def inspection_payload(loaded: CanonicalGeoTIFF) -> dict[str, object]:
    """Return the strict, coordinate-free inspection allowlist."""
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "command": "inspect",
        "status": "VALID",
        "input_label": INPUT_LABEL,
        "readable": True,
        "width": loaded.width,
        "height": loaded.height,
        "band_count": loaded.band_count,
        "crs": "EPSG:27700",
        "resolution_m": [1.0, 1.0],
        "dtype": loaded.dtype,
        "nodata_status": ("NONE" if loaded.nodata_fraction == 0.0 else "EXPLICIT_MASK_PRESENT"),
        "nodata_fraction": loaded.nodata_fraction,
        "finite_value_qa": "PASS",
        "canonical_feature_contract": "COMPATIBLE",
        "model_inference": MODEL_NOT_PERFORMED,
    }
    if set(payload) != INSPECT_PUBLIC_FIELDS:
        raise RuntimeError("inspection public-field contract changed")
    return payload


def features_payload(loaded: CanonicalGeoTIFF) -> dict[str, object]:
    """Return safe feature-contract facts without exposing feature values."""
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "command": "features",
        "status": "FEATURES_READY",
        "input_label": INPUT_LABEL,
        "feature_shape": [FEATURE_COUNT],
        "feature_dtype": str(loaded.features.feature_vector.dtype),
        "representation_order": list(REPRESENTATION_CHANNELS),
        "feature_values_exposed": False,
        "model_inference": MODEL_NOT_PERFORMED,
    }
    if set(payload) != FEATURES_PUBLIC_FIELDS:
        raise RuntimeError("features public-field contract changed")
    return payload


def error_payload(command: str, code: CliErrorCode) -> dict[str, object]:
    """Render errors only through fixed codes and fixed messages."""
    safe_command = (
        command if command in {"inspect", "features", "infer", "batch-features"} else "cli"
    )
    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "command": safe_command,
        "status": "ERROR",
        "error_code": code.value,
        "message": ERROR_MESSAGES[code],
        "model_inference": MODEL_NOT_PERFORMED,
    }
    if set(payload) != ERROR_PUBLIC_FIELDS:
        raise RuntimeError("error public-field contract changed")
    return payload


def _render_human(payload: dict[str, object]) -> str:
    command = payload["command"]
    if payload["status"] == "ERROR":
        return f"ERROR [{payload['error_code']}]: {payload['message']}"
    if command == "inspect":
        resolution = payload["resolution_m"]
        return "\n".join(
            (
                "ArchaeoAI offline terrain inspection",
                f"Status: {payload['status']}",
                f"Input: {payload['input_label']}",
                f"Readable: {str(payload['readable']).lower()}",
                f"Dimensions: {payload['width']} x {payload['height']}",
                f"Bands: {payload['band_count']}",
                f"CRS: {payload['crs']}",
                f"Resolution: {resolution[0]} m x {resolution[1]} m",  # type: ignore[index]
                f"Dtype: {payload['dtype']}",
                f"No-data: {payload['nodata_status']} ({payload['nodata_fraction']:.6f})",
                f"Finite-value QA: {payload['finite_value_qa']}",
                f"Feature contract: {payload['canonical_feature_contract']}",
                "Model inference: not performed",
            )
        )
    if command == "batch-features":
        return "\n".join(
            (
                "ArchaeoAI bounded offline batch",
                f"Status: {payload['status']}",
                f"Manifest: {payload['manifest_label']}",
                f"Processing order: {payload['processing_order']}",
                f"Submitted: {payload['total_items']}",
                f"Accepted: {payload['accepted_items']}",
                f"Invalid: {payload['invalid_items']}",
                f"Features prepared: {payload['feature_preparation_succeeded']}",
                f"Processing failures: {payload['processing_failures']}",
                "Model execution: not performed",
                "Input retention: none",
                "Temporary artifacts retained: no",
            )
        )
    return "\n".join(
        (
            "ArchaeoAI offline feature preparation",
            f"Status: {payload['status']}",
            f"Input: {payload['input_label']}",
            f"Feature shape: ({payload['feature_shape'][0]},)",  # type: ignore[index]
            f"Feature dtype: {payload['feature_dtype']}",
            "Representations: " + ", ".join(payload["representation_order"]),  # type: ignore[arg-type]
            "Feature values exposed: no",
            "Model inference: not performed",
        )
    )


def _emit(payload: dict[str, object], *, json_output: bool, error: bool = False) -> None:
    text = (
        json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
        if json_output
        else _render_human(payload)
    )
    print(text, file=sys.stderr if error else sys.stdout)


def _run_infer(args: argparse.Namespace) -> ExitCode:
    if args.model is None:
        raise CliExpectedError(CliErrorCode.MODEL_UNAVAILABLE, ExitCode.MODEL_UNAVAILABLE)
    try:
        project_root = find_project_root()
        identifier = ModelIdentifier.E001_FROZEN_RANDOM_FOREST
        reference = ApprovedModelArtifactReference(
            path=Path(args.model),
            model_identifier=identifier,
            model_config_sha256=APPROVED_MODEL_CONFIG_SHA256[identifier],
        )
        verify_approved_model_artifact(project_root, reference)
    except ModelArtifactUnavailableError as exc:
        raise CliExpectedError(CliErrorCode.MODEL_UNAVAILABLE, ExitCode.MODEL_UNAVAILABLE) from exc
    except ModelArtifactIntegrityError as exc:
        raise CliExpectedError(
            CliErrorCode.ARTIFACT_INTEGRITY, ExitCode.ARTIFACT_INTEGRITY
        ) from exc
    except (ProjectPathError, TypeError, ValueError) as exc:
        raise CliExpectedError(
            CliErrorCode.CONFIGURATION_MISMATCH, ExitCode.CONFIGURATION_MISMATCH
        ) from exc
    raise CliExpectedError(CliErrorCode.MODEL_NOT_AUTHORIZED, ExitCode.MODEL_UNAVAILABLE)


def _run_batch_features(args: argparse.Namespace) -> ExitCode:
    try:
        manifest = load_batch_manifest(args.manifest)
    except BatchManifestError as exc:
        raise CliExpectedError(CliErrorCode(exc.code.value), ExitCode.INVALID_INPUT) from exc
    result = run_feature_batch(manifest)
    payload = result.to_public_dict()
    _emit(payload, json_output=args.json_output)
    return ExitCode.SUCCESS if result.invalid_items == 0 else ExitCode.INVALID_INPUT


def build_parser() -> SafeArgumentParser:
    parser = SafeArgumentParser(
        prog="archaeoai",
        description="Offline, single-patch ArchaeoAI terrain inspection.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subcommands = parser.add_subparsers(dest="command", required=True)
    for command, help_text in (
        ("inspect", "validate one canonical local GeoTIFF without model inference"),
        ("features", "prepare the canonical feature contract without exposing values"),
    ):
        subparser = subcommands.add_parser(command, help=help_text)
        subparser.add_argument("terrain", metavar="TERRAIN.tif")
        subparser.add_argument("--json", action="store_true", dest="json_output")
    infer = subcommands.add_parser(
        "infer",
        help="check the private model gate; Phase 5C does not execute inference",
    )
    infer.add_argument("terrain", metavar="TERRAIN.tif")
    infer.add_argument("--model", metavar="PRIVATE_MODEL.pkl")
    infer.add_argument("--json", action="store_true", dest="json_output")
    batch = subcommands.add_parser(
        "batch-features",
        help="prepare a bounded manifest of canonical patches without model inference",
    )
    batch.add_argument("manifest", metavar="MANIFEST.json")
    batch.add_argument("--json", action="store_true", dest="json_output")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "infer":
            return int(_run_infer(args))
        if args.command == "batch-features":
            return int(_run_batch_features(args))
        loaded = load_canonical_geotiff(args.terrain)
        payload = (
            inspection_payload(loaded) if args.command == "inspect" else features_payload(loaded)
        )
        _emit(payload, json_output=args.json_output)
        return int(ExitCode.SUCCESS)
    except CliExpectedError as exc:
        _emit(error_payload(args.command, exc.code), json_output=args.json_output, error=True)
        return int(exc.exit_code)
    except Exception:
        _emit(
            error_payload(args.command, CliErrorCode.INTERNAL_ERROR),
            json_output=args.json_output,
            error=True,
        )
        return int(ExitCode.INTERNAL_ERROR)


__all__ = [
    "ERROR_PUBLIC_FIELDS",
    "FEATURES_PUBLIC_FIELDS",
    "INSPECT_PUBLIC_FIELDS",
    "CanonicalGeoTIFF",
    "CliErrorCode",
    "ExitCode",
    "build_parser",
    "error_payload",
    "features_payload",
    "inspection_payload",
    "load_canonical_geotiff",
    "main",
]
