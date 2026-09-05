"""Offline, privacy-bounded single-patch command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from pathlib import Path
from types import MappingProxyType

import numpy as np
import rasterio
from rasterio.errors import RasterioIOError

from archaeoai import __version__
from archaeoai.inference import FEATURE_COUNT, REPRESENTATION_CHANNELS
from archaeoai.inference_system import (
    E001_TERRAIN_INPUT,
    ApprovedModelArtifactReference,
    ModelArtifactIntegrityError,
    ModelArtifactUnavailableError,
    ModelIdentifier,
    SinglePatchFeatures,
    TerrainInputMetadata,
    TerrainPatch,
    transform_single_patch,
    verify_approved_model_artifact,
)
from archaeoai.inference_system.contracts import APPROVED_MODEL_CONFIG_SHA256
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


@dataclass(frozen=True, slots=True)
class CanonicalGeoTIFF:
    """Private in-memory patch plus the safe facts allowed in CLI reports."""

    features: SinglePatchFeatures = field(repr=False)
    width: int
    height: int
    band_count: int
    dtype: str
    nodata_fraction: float


def _local_geotiff_path(raw_path: str | Path) -> Path:
    try:
        source = Path(raw_path).resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise CliExpectedError(CliErrorCode.FILE_UNAVAILABLE, ExitCode.INVALID_INPUT) from exc
    if not source.is_file():
        raise CliExpectedError(CliErrorCode.FILE_UNAVAILABLE, ExitCode.INVALID_INPUT)
    if source.suffix.casefold() not in {".tif", ".tiff"}:
        raise CliExpectedError(CliErrorCode.UNSUPPORTED_FORMAT, ExitCode.INVALID_INPUT)
    return source


def load_canonical_geotiff(path: str | Path) -> CanonicalGeoTIFF:
    """Read one canonical local GeoTIFF without retaining spatial metadata in output."""
    source = _local_geotiff_path(path)
    try:
        with rasterio.open(source) as dataset:
            if dataset.driver != "GTiff":
                raise CliExpectedError(CliErrorCode.UNSUPPORTED_FORMAT, ExitCode.INVALID_INPUT)
            crs = dataset.crs.to_string() if dataset.crs is not None else None
            resolution = (abs(float(dataset.res[0])), abs(float(dataset.res[1])))
            preliminary = TerrainInputMetadata(
                crs=crs,
                width=dataset.width,
                height=dataset.height,
                resolution_m=resolution,
                band_count=dataset.count,
                nodata_fraction=0.0,
            )
            E001_TERRAIN_INPUT.validate(preliminary)
            band = dataset.read(1, masked=True)
            elevation = np.asarray(band.data)
            mask = np.ma.getmaskarray(band)
            dtype = str(dataset.dtypes[0])
    except CliExpectedError:
        raise
    except (RasterioIOError, OSError) as exc:
        raise CliExpectedError(CliErrorCode.RASTER_UNREADABLE, ExitCode.INVALID_INPUT) from exc
    except (TypeError, ValueError) as exc:
        raise CliExpectedError(CliErrorCode.NONCANONICAL_INPUT, ExitCode.INVALID_INPUT) from exc

    nodata_fraction = float(mask.mean())
    metadata = TerrainInputMetadata(
        crs=crs,
        width=preliminary.width,
        height=preliminary.height,
        resolution_m=resolution,
        band_count=preliminary.band_count,
        nodata_fraction=nodata_fraction,
    )
    try:
        features = transform_single_patch(TerrainPatch(elevation, mask, metadata))
    except (TypeError, ValueError) as exc:
        raise CliExpectedError(CliErrorCode.NONCANONICAL_INPUT, ExitCode.INVALID_INPUT) from exc
    return CanonicalGeoTIFF(
        features=features,
        width=metadata.width,
        height=metadata.height,
        band_count=metadata.band_count,
        dtype=dtype,
        nodata_fraction=nodata_fraction,
    )


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
    safe_command = command if command in {"inspect", "features", "infer"} else "cli"
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "infer":
            return int(_run_infer(args))
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
