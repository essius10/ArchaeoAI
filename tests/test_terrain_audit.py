import numpy as np

from archaeoai.terrain.audit import cross_cell_seams, extract_described_diameter
from archaeoai.terrain.patches import Bounds


def test_extracts_description_diameter_for_qa_stratification() -> None:
    assert extract_described_diameter("The barrow mound measures 12m across and is 1m high.") == 12
    assert extract_described_diameter("The mound is 20m in diameter.") == 20
    assert extract_described_diameter("No dimensional evidence is stated.") is None


def test_cross_cell_seam_reports_boundary_without_coordinates() -> None:
    elevation = np.tile(np.arange(8, dtype=np.float32), (8, 1))
    slope = np.ones_like(elevation)
    relief = np.zeros_like(elevation)

    diagnostics = cross_cell_seams(
        elevation,
        slope,
        relief,
        bounds=Bounds(4996, 100, 5004, 108),
    )

    assert len(diagnostics) == 1
    assert diagnostics[0].orientation == "vertical"
    assert diagnostics[0].pixel_index == 4
    assert diagnostics[0].elevation_median_step == 1
    assert not diagnostics[0].duplicate_edge
