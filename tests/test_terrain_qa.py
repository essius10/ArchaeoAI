import numpy as np
import pytest

from archaeoai.terrain.qa import FULL_QA_ORDER, QA_ORDER, qa_mosaic, qa_strip


def test_qa_mosaic_is_deterministic_and_has_four_quadrants() -> None:
    representations = {name: np.arange(16, dtype=np.float32).reshape(4, 4) for name in QA_ORDER}

    first = qa_mosaic(representations)
    second = qa_mosaic(representations)

    assert first.shape == (10, 10)
    np.testing.assert_array_equal(first, second)
    assert (first[4:6, :] == 255).all()
    assert (first[:, 4:6] == 255).all()


def test_qa_mosaic_rejects_missing_representation() -> None:
    with pytest.raises(ValueError, match="missing QA"):
        qa_mosaic({"elevation_normalized": np.ones((4, 4))})


def test_qa_mosaic_rejects_all_nodata() -> None:
    representations = {name: np.full((4, 4), np.nan, dtype=np.float32) for name in QA_ORDER}

    with pytest.raises(ValueError, match="all-nodata"):
        qa_mosaic(representations)


def test_full_qa_strip_has_raw_plus_four_frozen_views() -> None:
    layers = {name: np.arange(16, dtype=np.float32).reshape(4, 4) for name in FULL_QA_ORDER}

    strip = qa_strip(layers)

    assert strip.shape == (4, 28)
    assert (strip[:, 4:6] == 255).all()


def test_full_qa_strip_rejects_incomplete_layers() -> None:
    with pytest.raises(ValueError, match="missing full QA"):
        qa_strip({"elevation": np.ones((4, 4))})
