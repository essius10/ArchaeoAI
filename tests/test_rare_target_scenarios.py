import math

import pytest

from scripts.rare_target_scenarios import NOTICE, demonstration, evaluate, required_specificity


def scenario(**overrides):
    return evaluate(
        **(
            {
                "prevalence": 0.001,
                "sensitivity": 0.9,
                "specificity": 0.99,
                "decision_units": 100_000,
            }
            | overrides
        )
    )


def test_worked_example_and_conservation():
    result = scenario(
        units_per_km2=100,
        density_basis="Disjoint fictional grid cells",
        area_km2=1_000,
        minutes_per_review=2,
        budget_minutes=240,
    )
    assert result[:4] == pytest.approx((90, 999, 98_901, 10))
    assert sum(result[:4]) == pytest.approx(100_000)
    assert result.positive_predictive_value == pytest.approx(90 / 1089)
    assert result.negative_predictive_value == pytest.approx(98_901 / 98_911)
    assert result.balanced_accuracy == pytest.approx(0.945)
    assert result.expected_reviews == pytest.approx(1089)
    assert result.number_needed_to_review == pytest.approx(1089 / 90)
    assert result.false_alerts_per_1000 == pytest.approx(9.99)
    assert result.false_alerts_per_km2 == pytest.approx(0.999)
    assert result.expected_review_minutes == pytest.approx(2178)
    assert result.expected_minutes_over_budget == pytest.approx(1938)


def test_degenerate_predicted_classes_are_explicit():
    all_negative = scenario(sensitivity=0, specificity=1)
    assert all_negative.positive_predictive_value is None
    assert all_negative.number_needed_to_review is None
    assert all_negative.expected_reviews == 0
    all_positive = scenario(sensitivity=1, specificity=0)
    assert all_positive.negative_predictive_value is None
    assert all_positive.expected_reviews == 100_000
    assert scenario(prevalence=0).positive_predictive_value == 0
    assert scenario(prevalence=1).positive_predictive_value == 1
    assert scenario(prevalence=1).false_positives == 0
    assert scenario(decision_units=0).expected_reviews == 0


def test_specificity_inverts_bayes_formula():
    specificity = required_specificity(prevalence=0.001, sensitivity=0.9, target_precision=0.5)
    assert specificity is not None
    assert scenario(specificity=specificity).positive_predictive_value == pytest.approx(0.5)
    assert required_specificity(prevalence=0.2, sensitivity=1, target_precision=1) == 1
    assert required_specificity(prevalence=1, sensitivity=1, target_precision=1) == 0
    assert required_specificity(prevalence=0, sensitivity=1, target_precision=0.3) is None
    assert required_specificity(prevalence=0.5, sensitivity=0, target_precision=0.3) is None
    with pytest.raises(ValueError, match="positive"):
        required_specificity(prevalence=0.2, sensitivity=1, target_precision=0)


@pytest.mark.parametrize(
    "overrides",
    [
        {"prevalence": True},
        {"sensitivity": math.nan},
        {"specificity": 1.01},
        {"decision_units": 1.0},
        {"decision_units": -1},
        {"units_per_km2": 100},
        {"density_basis": "Grid"},
        {"units_per_km2": 100, "density_basis": " ", "area_km2": 1000},
        {"units_per_km2": 100, "density_basis": "Grid", "area_km2": 99},
        {"area_km2": math.inf},
        {"minutes_per_review": -1},
        {"minutes_per_review": 1e308},
        {"minutes_per_review": 10**309},
        {"budget_minutes": 30},
    ],
)
def test_invalid_inputs(overrides):
    with pytest.raises(ValueError):
        scenario(**overrides)


def test_no_implicit_density_and_budget_surplus():
    result = scenario(area_km2=100, minutes_per_review=0, budget_minutes=100)
    assert result.false_alerts_per_km2 is None
    assert result.expected_minutes_over_budget == 0


def test_demo_is_labelled_deterministic_and_covers_requested_prevalence():
    report = demonstration()
    assert report.startswith(NOTICE)
    assert report == demonstration()
    for prevalence in ("50.00", "10.00", "5.00", "1.00", "0.50", "0.10", "0.01"):
        assert report.count(f"| {prevalence}% |") == 2
