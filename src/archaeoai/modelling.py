"""Pre-registered Phase 2D-A baseline estimators and development metrics."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

MODEL_ORDER = ("dummy", "logistic_regression", "random_forest")
REPRESENTATION_ORDER = (
    "normalized_elevation",
    "slope",
    "hillshade",
    "local_relief",
    "all_four",
)
MODEL_SEED = 20260829


@dataclass(frozen=True, slots=True)
class DevelopmentResult:
    model: str
    representation: str
    feature_count: int
    balanced_accuracy: float
    roc_auc: float


def build_estimator(model: str) -> ClassifierMixin:
    if model == "dummy":
        return DummyClassifier(strategy="prior")
    if model == "logistic_regression":
        return Pipeline(
            [
                ("scaler", StandardScaler()),
                (
                    "classifier",
                    LogisticRegression(
                        C=1.0,
                        penalty="l2",
                        solver="lbfgs",
                        max_iter=2000,
                        random_state=MODEL_SEED,
                    ),
                ),
            ]
        )
    if model == "random_forest":
        return RandomForestClassifier(
            n_estimators=300,
            max_depth=8,
            min_samples_leaf=5,
            max_features="sqrt",
            n_jobs=1,
            random_state=MODEL_SEED,
        )
    raise ValueError("unsupported baseline model")


def evaluate_development(
    model: str,
    representation: str,
    train_features: np.ndarray,
    train_labels: np.ndarray,
    development_features: np.ndarray,
    development_labels: np.ndarray,
) -> tuple[DevelopmentResult, ClassifierMixin]:
    estimator = build_estimator(model)
    estimator.fit(train_features, train_labels)
    probabilities = estimator.predict_proba(development_features)[:, 1]
    predictions = (probabilities >= 0.5).astype(np.int8)
    result = DevelopmentResult(
        model=model,
        representation=representation,
        feature_count=train_features.shape[1],
        balanced_accuracy=float(balanced_accuracy_score(development_labels, predictions)),
        roc_auc=float(roc_auc_score(development_labels, probabilities)),
    )
    return result, estimator


def select_primary(results: list[DevelopmentResult]) -> DevelopmentResult:
    """Apply the frozen balanced-accuracy and effective-tie rule."""
    if not results:
        raise ValueError("development results cannot be empty")
    best_score = max(result.balanced_accuracy for result in results)
    tied = [result for result in results if best_score - result.balanced_accuracy < 0.02]
    logistic = [result for result in tied if result.model == "logistic_regression"]
    if logistic:
        tied = logistic
    minimum_channels = min(4 if result.representation == "all_four" else 1 for result in tied)
    tied = [
        result
        for result in tied
        if (4 if result.representation == "all_four" else 1) == minimum_channels
    ]
    return min(
        tied,
        key=lambda result: (
            MODEL_ORDER.index(result.model),
            REPRESENTATION_ORDER.index(result.representation),
        ),
    )
