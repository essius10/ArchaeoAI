from pathlib import Path

import pytest

from archaeoai.config import ConfigurationError, load_experiment_config

VALID_CONFIG = """
[experiment]
id = "E001"
seed = 42

[paths]
data_root = "data"
output_root = "outputs/E001"
dataset_manifest = "data/manifests/example.toml"

[split]
strategies = ["random", "geographic"]
random_test_fraction = 0.2
geographic_group_field = "region_id"
geographic_holdout_groups = ["EXAMPLE_REGION"]

[parameters]
patch_size_m = 128
target_resolution_m = 1.0
max_nodata_fraction = 0.2
"""


def _write_config(tmp_path: Path, content: str = VALID_CONFIG) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(content, encoding="utf-8")
    return path


def test_load_example_configuration() -> None:
    root = Path(__file__).resolve().parents[1]

    config = load_experiment_config(root / "configs" / "e001.example.toml")

    assert config.experiment_id == "E001"
    assert config.seed == 20260915
    assert config.split.strategies == ("random", "geographic")
    assert config.paths.data_root == root / "data"
    assert config.paths.output_root == root / "outputs" / "E001"
    assert config.parameters.patch_size_m == 128
    assert config.parameters.target_resolution_m == 1.0


def test_rejects_invalid_split_strategy(tmp_path: Path) -> None:
    path = _write_config(tmp_path, VALID_CONFIG.replace('"geographic"', '"nearby"'))

    with pytest.raises(ConfigurationError, match="Unsupported split strategies"):
        load_experiment_config(path, project_root=tmp_path)


def test_rejects_invalid_seed(tmp_path: Path) -> None:
    path = _write_config(tmp_path, VALID_CONFIG.replace("seed = 42", "seed = -1"))

    with pytest.raises(ConfigurationError, match="seed"):
        load_experiment_config(path, project_root=tmp_path)


def test_rejects_configured_path_escape(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path, VALID_CONFIG.replace('data_root = "data"', 'data_root = "../data"')
    )

    with pytest.raises(ValueError, match="inside project root"):
        load_experiment_config(path, project_root=tmp_path)


def test_rejects_malformed_toml(tmp_path: Path) -> None:
    path = _write_config(tmp_path, "[experiment\nid = 'E001'")

    with pytest.raises(ConfigurationError, match="Could not load configuration"):
        load_experiment_config(path, project_root=tmp_path)


def test_rejects_fractional_patch_dimensions(tmp_path: Path) -> None:
    path = _write_config(
        tmp_path, VALID_CONFIG.replace("target_resolution_m = 1.0", "target_resolution_m = 3.0")
    )

    with pytest.raises(ConfigurationError, match="integer number of target pixels"):
        load_experiment_config(path, project_root=tmp_path)
