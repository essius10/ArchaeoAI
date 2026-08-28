from pathlib import Path
from urllib.error import URLError

import pytest

from archaeoai.terrain.acquisition import (
    AcceptedSite,
    WcsRequestError,
    build_wcs_url,
    fetch_wcs_payload,
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


class _Headers:
    def __init__(self, content_length: int):
        self._content_length = content_length

    def get_content_type(self) -> str:
        return "image/tiff"

    def get(self, name: str) -> str | None:
        return str(self._content_length) if name == "Content-Length" else None


class _Response:
    def __init__(self, payload: bytes, *, advertised_length: int | None = None):
        self.payload = payload
        self.headers = _Headers(advertised_length or len(payload))

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, _limit: int) -> bytes:
        return self.payload


def test_wcs_retry_is_bounded_and_accounted() -> None:
    payload = b"II*\x00synthetic"
    outcomes: list[object] = [URLError("temporary"), _Response(payload)]
    sleeps: list[int] = []

    def opener(*_args: object, **_kwargs: object) -> _Response:
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        assert isinstance(outcome, _Response)
        return outcome

    result = fetch_wcs_payload(Bounds(100, 200, 228, 328), opener=opener, sleeper=sleeps.append)

    assert result.content == payload
    assert result.attempts == 2
    assert result.retries == 1
    assert sleeps == [1]


def test_partial_wcs_response_is_retried_then_reason_coded() -> None:
    payload = b"II*\x00short"

    with pytest.raises(WcsRequestError) as error:
        fetch_wcs_payload(
            Bounds(100, 200, 228, 328),
            maximum_attempts=2,
            opener=lambda *_args, **_kwargs: _Response(payload, advertised_length=len(payload) + 5),
            sleeper=lambda _seconds: None,
        )

    assert error.value.reason == "retry_exhausted_partial"
    assert error.value.attempts == 2
    assert error.value.retries == 1
