"""Unit tests for the explainable anomaly indicator scoring engine."""

import pytest

from app.core.enums import Severity
from app.forensic.scoring import (
    AnomalyCategory,
    ScoringInputs,
    category_from_score,
    score_anomaly_indicators,
    severity_from_diff_score,
)


def test_zero_score_with_no_indicators():
    score = score_anomaly_indicators(ScoringInputs())
    assert score.score == 0
    assert score.category is AnomalyCategory.LOW
    assert len(score.factors) == 6
    assert all(factor.points == 0 for factor in score.factors)


def test_metadata_inconsistency_isolated():
    score = score_anomaly_indicators(ScoringInputs(metadata_inconsistent=True))
    factor = _factor(score, "metadata_inconsistency")
    assert factor.points == 15
    assert score.score == 15


def test_duration_difference_proportional():
    half = score_anomaly_indicators(ScoringInputs(duration_deviation=0.5))
    assert _factor(half, "duration_difference").points == 10

    full = score_anomaly_indicators(ScoringInputs(duration_deviation=1.0))
    assert _factor(full, "duration_difference").points == 20

    tiny = score_anomaly_indicators(ScoringInputs(duration_deviation=0.001))
    assert _factor(tiny, "duration_difference").points == 0


def test_frame_discontinuity_scales_and_caps():
    one = score_anomaly_indicators(ScoringInputs(discontinuities=1))
    assert _factor(one, "frame_discontinuity").points == 5

    capped = score_anomaly_indicators(ScoringInputs(discontinuities=10))
    assert _factor(capped, "frame_discontinuity").points == 25


def test_encoding_difference_isolated():
    score = score_anomaly_indicators(ScoringInputs(encoding_differs=True))
    assert _factor(score, "encoding_difference").points == 15


def test_unnatural_cluster_detected_within_window():
    clustered = score_anomaly_indicators(ScoringInputs(event_timestamps=(1.0, 1.5, 2.0, 60.0)))
    assert _factor(clustered, "unnatural_frame_diff_cluster").points == 15


def test_no_cluster_when_events_are_sparse():
    sparse = score_anomaly_indicators(ScoringInputs(event_timestamps=(1.0, 2.1, 4.2)))
    assert _factor(sparse, "unnatural_frame_diff_cluster").points == 0


def test_single_scene_changes_max_points():
    score = score_anomaly_indicators(ScoringInputs(event_timestamps=(5.0,)))
    assert _factor(score, "single_scene_changes").points == 5


def test_combined_score_uses_all_factors():
    inputs = ScoringInputs(
        metadata_inconsistent=True,
        duration_deviation=1.0,
        encoding_differs=True,
        discontinuities=5,
        event_timestamps=(1.0, 1.5, 2.0),
    )
    score = score_anomaly_indicators(inputs)
    # 15 + 20 + 25 + 15 + 15 + 5
    assert score.score == 95
    assert score.category is AnomalyCategory.VERY_HIGH


def test_legitimate_single_cut_is_low():
    score = score_anomaly_indicators(ScoringInputs(event_timestamps=(2.0,)))
    assert score.score == 5
    assert score.category is AnomalyCategory.LOW


def test_scores_are_deterministic():
    inputs = ScoringInputs(discontinuities=2, event_timestamps=(1.0, 1.5, 2.0, 4.0))
    first = score_anomaly_indicators(inputs)
    second = score_anomaly_indicators(inputs)
    assert first.to_dict() == second.to_dict()


def test_to_dict_shape():
    score = score_anomaly_indicators(ScoringInputs(event_timestamps=(2.0,)))
    payload = score.to_dict()
    assert set(payload) == {"score", "category", "factors"}
    factor = payload["factors"][0]
    assert set(factor) == {"name", "label", "max_points", "points", "reason"}


@pytest.mark.parametrize(
    ("score_value", "expected"),
    [
        (0, AnomalyCategory.LOW),
        (20, AnomalyCategory.LOW),
        (21, AnomalyCategory.MODERATE),
        (50, AnomalyCategory.MODERATE),
        (51, AnomalyCategory.HIGH),
        (75, AnomalyCategory.HIGH),
        (76, AnomalyCategory.VERY_HIGH),
        (95, AnomalyCategory.VERY_HIGH),
    ],
)
def test_category_boundaries(score_value, expected):
    assert category_from_score(score_value) is expected


@pytest.mark.parametrize(
    ("diff_score", "expected"),
    [
        (0.2, Severity.LOW),
        (0.6, Severity.MEDIUM),
        (0.9, Severity.HIGH),
    ],
)
def test_severity_from_diff_score_unchanged(diff_score, expected):
    assert severity_from_diff_score(diff_score) is expected


def _factor(score, name):
    return next(factor for factor in score.factors if factor.name == name)
