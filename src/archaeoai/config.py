"""Typed TOML configuration for reproducible ArchaeoAI experiments."""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from archaeoai.paths import ensure_within_project, find_project_root, resolve_project_path

SplitStrategy = Literal["random", "geographic"]
_ALLOWED_STRATEGIES = frozenset({"random", "geographic"})
_EXPERIMENT_ID = re.compile(r"^[A-Z][A-Z0-9_-]{1,31}$")


class ConfigurationError(ValueError):
    """Raised when an experiment configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class PathConfig:
    data_root: Path
    output_root: Path
    dataset_manifest: Path


@dataclass(frozen=True, slots=True)
class SplitConfig:
    strategies: tuple[SplitStrategy, ...]
    random_test_fraction: float
    geographic_group_field: str
    geographic_holdout_groups: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExperimentParameters:
    patch_size_m: int
    target_resolution_m: float
    max_nodata_fraction: float


@dataclass(frozen=True, slots=True)
class ExperimentConfig:
    experiment_id: str
    seed: int
    paths: PathConfig
    split: SplitConfig
    parameters: ExperimentParameters
    source_path: Path


def _table(document: dict[str, Any], name: str) -> dict[str, Any]:
    value = document.get(name)
    if not isinstance(value, dict):
        raise ConfigurationError(f"Missing or invalid [{name}] table")
    return value


def _reject_unknown(table: dict[str, Any], allowed: set[str], *, table_name: str) -> None:
    unknown = sorted(set(table) - allowed)
    if unknown:
        raise ConfigurationError(f"Unknown keys in [{table_name}]: {', '.join(unknown)}")


def _string(table: dict[str, Any], key: str, *, table_name: str) -> str:
    value = table.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"[{table_name}].{key} must be a non-empty string")
    return value.strip()


def _integer(table: dict[str, Any], key: str, *, table_name: str) -> int:
    value = table.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"[{table_name}].{key} must be an integer")
    return value


def _number(table: dict[str, Any], key: str, *, table_name: str) -> float:
    value = table.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"[{table_name}].{key} must be numeric")
    return float(value)


def _strings(table: dict[str, Any], key: str, *, table_name: str) -> tuple[str, ...]:
    value = table.get(key)
    if not isinstance(value, list) or not value:
        raise ConfigurationError(f"[{table_name}].{key} must be a non-empty list")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ConfigurationError(f"[{table_name}].{key} must contain non-empty strings")
    normalized = tuple(item.strip() for item in value)
    if len(set(normalized)) != len(normalized):
        raise ConfigurationError(f"[{table_name}].{key} must not contain duplicates")
    return normalized


def load_experiment_config(
    config_path: str | Path,
    *,
    project_root: Path | None = None,
) -> ExperimentConfig:
    """Load and validate an experiment TOML file without accessing any dataset."""
    source_path = Path(config_path).resolve()
    root = (project_root or find_project_root(source_path)).resolve()
    ensure_within_project(root, source_path, field_name="config_path")

    try:
        with source_path.open("rb") as config_file:
            document = tomllib.load(config_file)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigurationError(f"Could not load configuration {source_path}: {exc}") from exc

    _reject_unknown(
        document,
        {"experiment", "paths", "split", "parameters"},
        table_name="root",
    )

    experiment = _table(document, "experiment")
    _reject_unknown(experiment, {"id", "seed"}, table_name="experiment")
    experiment_id = _string(experiment, "id", table_name="experiment")
    if not _EXPERIMENT_ID.fullmatch(experiment_id):
        raise ConfigurationError("[experiment].id must look like E001 and contain no spaces")
    seed = _integer(experiment, "seed", table_name="experiment")
    if not 0 <= seed <= 2**32 - 1:
        raise ConfigurationError("[experiment].seed must be between 0 and 2^32 - 1")

    paths = _table(document, "paths")
    _reject_unknown(
        paths,
        {"data_root", "output_root", "dataset_manifest"},
        table_name="paths",
    )
    path_config = PathConfig(
        data_root=resolve_project_path(
            root,
            _string(paths, "data_root", table_name="paths"),
            field_name="paths.data_root",
        ),
        output_root=resolve_project_path(
            root,
            _string(paths, "output_root", table_name="paths"),
            field_name="paths.output_root",
        ),
        dataset_manifest=resolve_project_path(
            root,
            _string(paths, "dataset_manifest", table_name="paths"),
            field_name="paths.dataset_manifest",
        ),
    )

    split = _table(document, "split")
    _reject_unknown(
        split,
        {
            "strategies",
            "random_test_fraction",
            "geographic_group_field",
            "geographic_holdout_groups",
        },
        table_name="split",
    )
    strategies_raw = _strings(split, "strategies", table_name="split")
    invalid = sorted(set(strategies_raw) - _ALLOWED_STRATEGIES)
    if invalid:
        raise ConfigurationError(f"Unsupported split strategies: {', '.join(invalid)}")
    strategies = tuple(strategies_raw)
    random_test_fraction = _number(split, "random_test_fraction", table_name="split")
    if "random" in strategies and not 0.0 < random_test_fraction < 1.0:
        raise ConfigurationError("[split].random_test_fraction must be between 0 and 1")
    geographic_group_field = _string(split, "geographic_group_field", table_name="split")
    geographic_holdout_groups = _strings(split, "geographic_holdout_groups", table_name="split")
    split_config = SplitConfig(
        strategies=strategies,  # type: ignore[arg-type]
        random_test_fraction=random_test_fraction,
        geographic_group_field=geographic_group_field,
        geographic_holdout_groups=geographic_holdout_groups,
    )

    parameters = _table(document, "parameters")
    _reject_unknown(
        parameters,
        {"patch_size_m", "target_resolution_m", "max_nodata_fraction"},
        table_name="parameters",
    )
    patch_size_m = _integer(parameters, "patch_size_m", table_name="parameters")
    if patch_size_m <= 0:
        raise ConfigurationError("[parameters].patch_size_m must be positive")
    target_resolution_m = _number(parameters, "target_resolution_m", table_name="parameters")
    if target_resolution_m <= 0:
        raise ConfigurationError("[parameters].target_resolution_m must be positive")
    if not (patch_size_m / target_resolution_m).is_integer():
        raise ConfigurationError(
            "[parameters].patch_size_m must be an integer number of target pixels"
        )
    max_nodata_fraction = _number(parameters, "max_nodata_fraction", table_name="parameters")
    if not 0.0 <= max_nodata_fraction <= 1.0:
        raise ConfigurationError("[parameters].max_nodata_fraction must be between 0 and 1")

    return ExperimentConfig(
        experiment_id=experiment_id,
        seed=seed,
        paths=path_config,
        split=split_config,
        parameters=ExperimentParameters(
            patch_size_m=patch_size_m,
            target_resolution_m=target_resolution_m,
            max_nodata_fraction=max_nodata_fraction,
        ),
        source_path=source_path,
    )
