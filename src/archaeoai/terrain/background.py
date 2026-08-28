"""Pre-specified policy contract for future unlabelled-background sampling only."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BackgroundSamplingPolicy:
    label: str = "unlabelled_background"
    positive_exclusion_buffer_m: float = 256.0
    known_archaeology_exclusion_buffer_m: float = 256.0
    minimum_sample_separation_m: float = 128.0
    deterministic_seed: int = 20260915
    require_landscape_matching: bool = True
    require_survey_provenance_matching: bool = True
    require_geographic_group_assignment: bool = True
    require_modern_feature_screen: bool = True
    maximum_nodata_fraction: float = 0.2

    def __post_init__(self) -> None:
        if self.label != "unlabelled_background":
            raise ValueError("unknown terrain must be labelled unlabelled_background")
        if (
            min(
                self.positive_exclusion_buffer_m,
                self.known_archaeology_exclusion_buffer_m,
                self.minimum_sample_separation_m,
            )
            <= 0
        ):
            raise ValueError("background distances must be positive")
        if not 0 <= self.maximum_nodata_fraction <= 1:
            raise ValueError("maximum_nodata_fraction must be between zero and one")
