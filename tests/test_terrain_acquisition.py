from pathlib import Path

import pytest

from archaeoai.terrain.acquisition import (
    AcceptedSite,
    build_wcs_url,
    opaque_sample_id,
    select_diverse_pilot,
)
from archaeoai.terrain.patches import Bounds
from archaeoai.terrain.privacy import assert_coordinate_safe_mapping, ensure_private_output


def _accepted(list_entry: int, group: str, year: str) -> AcceptedSite:
    return AcceptedSite(list_entry, group, year, "1", "National LIDAR Programme")


def test_wcs_request_is_bounded_and_preserves_repeated_subsets() -> None:
    url = build_wcs_url(Bounds(100, 200, 228, 328))

    assert "GetCoverage" in url
    assert "E%28100%2C228%29" in url
    assert "N%28200%2C328%29" in url
    assert url.count("subset=") == 2


def test_pilot_selection_is_deterministic_and_group_diverse() -> None:
    records = tuple(_accepted(index, f"G{index}", str(2000 + index)) for index in range(10))

    first = select_diverse_pilot(records, count=5)
    second = select_diverse_pilot(records, count=5)

    assert first == second
    assert len({record.geographic_group_id for record in first}) == 5


def test_opaque_sample_id_is_stable() -> None:
    assert opaque_sample_id(123) == opaque_sample_id(123)
    assert opaque_sample_id(123) != opaque_sample_id(124)


def test_private_output_cannot_escape_controlled_root(tmp_path: Path) -> None:
    private = tmp_path / "data" / "private" / "site.json"
    assert ensure_private_output(tmp_path, private) == private.resolve()

    with pytest.raises(ValueError, match="must remain under"):
        ensure_private_output(tmp_path, tmp_path / "outputs" / "site.json")


def test_coordinate_fields_are_rejected_from_tracked_metadata() -> None:
    with pytest.raises(ValueError, match="coordinate-bearing field"):
        assert_coordinate_safe_mapping({"sample_id": "safe", "easting": 123.0})
