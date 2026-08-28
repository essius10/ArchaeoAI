import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from archaeoai.modelling import DevelopmentResult, build_estimator, select_primary


def _result(model: str, representation: str, score: float) -> DevelopmentResult:
    return DevelopmentResult(model, representation, 1024, score, 0.5)


def test_only_logistic_pipeline_uses_training_fitted_scaler() -> None:
    logistic = build_estimator("logistic_regression")
    forest = build_estimator("random_forest")

    assert isinstance(logistic, Pipeline)
    assert isinstance(logistic.named_steps["scaler"], StandardScaler)
    assert isinstance(forest, RandomForestClassifier)
    assert forest.n_estimators == 300
    assert forest.max_depth == 8
    assert forest.min_samples_leaf == 5


def test_selection_uses_effective_tie_then_logistic_then_fewer_channels() -> None:
    results = [
        _result("random_forest", "all_four", 0.80),
        _result("logistic_regression", "all_four", 0.79),
        _result("logistic_regression", "slope", 0.785),
    ]

    selected = select_primary(results)
    assert selected.model == "logistic_regression"
    assert selected.representation == "slope"


def test_difference_of_exactly_point_zero_two_is_not_an_effective_tie() -> None:
    selected = select_primary(
        [
            _result("random_forest", "all_four", 0.80),
            _result("logistic_regression", "slope", 0.78),
        ]
    )
    assert selected.model == "random_forest"


def test_unknown_model_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        build_estimator("svm")


def test_model_fit_is_deterministic_for_fixed_seed() -> None:
    features = np.arange(80, dtype=np.float32).reshape(20, 4)
    labels = np.array([0, 1] * 10)
    first = build_estimator("random_forest").fit(features, labels).predict_proba(features)
    second = build_estimator("random_forest").fit(features, labels).predict_proba(features)
    assert np.array_equal(first, second)
