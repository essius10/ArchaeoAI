"""Coordinate-free planning arithmetic. Run directly for a fixed synthetic table."""

from math import isclose, isfinite
from sys import float_info
from typing import NamedTuple

NOTICE = "HYPOTHETICAL MATHEMATICAL SCENARIO — NOT MEASURED ARCHAEOAI PERFORMANCE"


class Scenario(NamedTuple):
    true_positives: float
    false_positives: float
    true_negatives: float
    false_negatives: float
    positive_predictive_value: float | None
    negative_predictive_value: float | None
    balanced_accuracy: float
    expected_reviews: float
    number_needed_to_review: float | None
    false_alerts_per_1000: float
    false_alerts_per_km2: float | None
    expected_review_minutes: float | None
    expected_minutes_over_budget: float | None


def _validate(name: str, value: float, maximum: float | None = None) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (float, int))
        or value > float_info.max
        or not isfinite(value)
        or value < 0
        or (maximum is not None and value > maximum)
    ):
        raise ValueError(f"Invalid {name}")


def evaluate(
    *,
    prevalence: float,
    sensitivity: float,
    specificity: float,
    decision_units: int,
    units_per_km2: float | None = None,
    density_basis: str | None = None,
    area_km2: float | None = None,
    minutes_per_review: float | None = None,
    budget_minutes: float | None = None,
) -> Scenario:
    """Compute expectations for a common defined unit, with no independence assumption.

    Density requires a stated unit/coverage basis. This interface cannot verify that the
    basis is sound. Area alone does not authorize interpreting overlapping windows as objects.
    """
    for name, probability in (
        ("prevalence", prevalence),
        ("sensitivity", sensitivity),
        ("specificity", specificity),
    ):
        _validate(name, probability, 1)
    if type(decision_units) is not int or not 0 <= decision_units <= 2**53:
        raise ValueError("Decision units must be a nonnegative exactly representable count")
    for name, value in (
        ("density", units_per_km2),
        ("area", area_km2),
        ("review time", minutes_per_review),
        ("review budget", budget_minutes),
    ):
        if value is not None:
            _validate(name, value)
    if units_per_km2 is not None:
        if not isinstance(density_basis, str) or not density_basis.strip():
            raise ValueError("Density requires an explicit decision-unit and coverage basis")
        if area_km2 is not None and not isclose(units_per_km2 * area_km2, decision_units):
            raise ValueError("Area and density disagree with the decision-unit count")
    elif density_basis is not None:
        raise ValueError("Density basis requires a density")
    if budget_minutes is not None and minutes_per_review is None:
        raise ValueError("Review budget requires minutes per review")

    tp = prevalence * sensitivity
    fn = prevalence * (1 - sensitivity)
    fp = (1 - prevalence) * (1 - specificity)
    tn = (1 - prevalence) * specificity
    selected = tp + fp
    rejected = tn + fn
    review_minutes = (
        selected * decision_units * minutes_per_review if minutes_per_review is not None else None
    )
    if review_minutes is not None and not isfinite(review_minutes):
        raise ValueError("Expected review time exceeds the numerical range")
    return Scenario(
        true_positives=tp * decision_units,
        false_positives=fp * decision_units,
        true_negatives=tn * decision_units,
        false_negatives=fn * decision_units,
        positive_predictive_value=tp / selected if selected else None,
        negative_predictive_value=tn / rejected if rejected else None,
        balanced_accuracy=(sensitivity + specificity) / 2,
        expected_reviews=selected * decision_units,
        number_needed_to_review=selected / tp if tp else None,
        false_alerts_per_1000=1000 * fp,
        false_alerts_per_km2=fp * units_per_km2 if units_per_km2 is not None else None,
        expected_review_minutes=review_minutes,
        expected_minutes_over_budget=(
            max(0.0, review_minutes - budget_minutes)
            if review_minutes is not None and budget_minutes is not None
            else None
        ),
    )


def required_specificity(
    *, prevalence: float, sensitivity: float, target_precision: float
) -> float | None:
    """Return the minimum specificity for positive target precision, or None if infeasible."""
    _validate("prevalence", prevalence, 1)
    _validate("sensitivity", sensitivity, 1)
    _validate("target precision", target_precision, 1)
    if target_precision == 0:
        raise ValueError("Target precision must be positive")
    tp = prevalence * sensitivity
    if not tp:
        return None
    if prevalence == 1:
        return 0.0
    allowed_fp = tp * (1 - target_precision) / target_precision
    return max(0.0, 1 - allowed_fp / (1 - prevalence))


def demonstration() -> str:
    """Generate fixed hypothetical comparisons without reading files or loading models."""
    lines = [
        NOTICE,
        "",
        "10,000 fictional, disjoint decisions across 100 km². Review takes 2 or 5 minutes.",
        "",
        "| Prev. | Sens. | Spec. | BA | PPV | Misses | Alerts | False/km² | Min. |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for prevalence in (0.5, 0.1, 0.05, 0.01, 0.005, 0.001, 0.0001):
        for sensitivity, specificity in ((0.9, 0.95), (0.7, 0.999)):
            result = evaluate(
                prevalence=prevalence,
                sensitivity=sensitivity,
                specificity=specificity,
                decision_units=10_000,
                units_per_km2=100,
                area_km2=100,
                density_basis="Fictional disjoint decisions across complete coverage",
            )
            assert result.positive_predictive_value is not None
            assert result.false_alerts_per_km2 is not None
            lines.append(
                f"| {prevalence:.2%} | {sensitivity:.1%} | {specificity:.1%} | "
                f"{result.balanced_accuracy:.2%} | {result.positive_predictive_value:.2%} | "
                f"{result.false_negatives:.1f} | {result.expected_reviews:.1f} | "
                f"{result.false_alerts_per_km2:.3f} | "
                f"{2 * result.expected_reviews:.1f}–{5 * result.expected_reviews:.1f} |"
            )
    lines.extend(
        [
            "",
            "Compare review minutes against a 60-minute or 240-minute budget.",
            "At fixed rates, doubling the decision density doubles false alerts per km².",
            "These are means under stipulated rates. A budget exceedance probability requires",
            "a separate model of dependence and review times.",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    print(demonstration())
