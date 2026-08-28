import pytest

from archaeoai.terrain.background import BackgroundSamplingPolicy


def test_background_policy_uses_uncertainty_aware_label() -> None:
    policy = BackgroundSamplingPolicy()

    assert policy.label == "unlabelled_background"
    assert policy.require_survey_provenance_matching
    assert policy.require_geographic_group_assignment


def test_true_negative_label_is_rejected() -> None:
    with pytest.raises(ValueError, match="unlabelled_background"):
        BackgroundSamplingPolicy(label="true_negative")
