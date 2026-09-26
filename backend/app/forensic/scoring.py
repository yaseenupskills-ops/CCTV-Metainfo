"""Deterministic, explainable anomaly indicator scoring.

The Anomaly Indicator Score (0-100) summarises how many independent technical
indicators are present. It is NOT a probability of tampering — every factor is
a factual observation (metadata inconsistency, duration deviation, frame
discontinuity, encoding difference, clustered frame differences) whose weight
and reason are always reported alongside the total.

Category bands:
    low       0-20
    moderate  21-50
    high      51-75
    very high 76-100
"""

from dataclasses import dataclass, field
from enum import StrEnum

from app.core.enums import Severity

_METADATA_INCONSISTENCY_MAX = 15
_DURATION_DIFFERENCE_MAX = 20
_FRAME_DISCONTINUITY_MAX = 25
_ENCODING_DIFFERENCE_MAX = 15
_UNNATURAL_CLUSTER_MAX = 15
_SINGLE_SCENE_CHANGES_MAX = 5

_DISCONTINUITY_DIFF_THRESHOLD = 0.9
_DISCONTINUITY_POINTS_PER_EVENT = 5
_CLUSTER_WINDOW_SECONDS = 2.0
_CLUSTER_MIN_EVENTS = 3
_DURATION_DEVIATION_POINTS = 20
_DURATION_MISMATCH_TOLERANCE = 0.10


class AnomalyCategory(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    VERY_HIGH = "very_high"


def category_from_score(score: int) -> AnomalyCategory:
    """Map a score (0-100) to its named category band."""
    if score >= 76:
        return AnomalyCategory.VERY_HIGH
    if score >= 51:
        return AnomalyCategory.HIGH
    if score >= 21:
        return AnomalyCategory.MODERATE
    return AnomalyCategory.LOW


@dataclass(frozen=True)
class ScoringFactor:
    """One weighted, explained contribution to the indicator score."""

    name: str
    label: str
    max_points: int
    points: int
    reason: str


@dataclass(frozen=True)
class AnomalyIndicatorScore:
    """Total indicator score with every contributing factor and its reason."""

    score: int
    category: AnomalyCategory
    factors: list[ScoringFactor] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "category": self.category.value,
            "factors": [
                {
                    "name": factor.name,
                    "label": factor.label,
                    "max_points": factor.max_points,
                    "points": factor.points,
                    "reason": factor.reason,
                }
                for factor in self.factors
            ],
        }


@dataclass(frozen=True)
class ScoringInputs:
    """Observations the scoring engine turns into weighted factors.

    `duration_deviation` is the normalized |original - suspected| / original
    ratio from a comparison (0.0 when no comparison exists). `discontinuities`
    counts frame-difference events with a near-total diff (>= 0.9), i.e. an
    abrupt frame replacement. `event_timestamps` are the scene-change event
    timestamps used to detect unnatural clusters.
    """

    metadata_inconsistent: bool = False
    duration_deviation: float = 0.0
    encoding_differs: bool = False
    discontinuities: int = 0
    event_timestamps: tuple[float, ...] = ()


def severity_from_diff_score(diff_score: float) -> Severity:
    """Map a combined frame-difference score (0-1) to a severity level.

    Used to label *Potential anomaly* events. This is not a tampering verdict.
    """
    if diff_score >= 0.75:
        return Severity.HIGH
    if diff_score >= 0.5:
        return Severity.MEDIUM
    return Severity.LOW


def _metadata_inconsistency_factor(inconsistent: bool) -> ScoringFactor:
    if inconsistent:
        return ScoringFactor(
            name="metadata_inconsistency",
            label="Metadata inconsistency",
            max_points=_METADATA_INCONSISTENCY_MAX,
            points=_METADATA_INCONSISTENCY_MAX,
            reason="Declared frame count does not match duration × frame rate",
        )
    return ScoringFactor(
        name="metadata_inconsistency",
        label="Metadata inconsistency",
        max_points=_METADATA_INCONSISTENCY_MAX,
        points=0,
        reason="No internal metadata contradiction detected",
    )


def _duration_difference_factor(deviation: float) -> ScoringFactor:
    if deviation > 0:
        points = min(_DURATION_DIFFERENCE_MAX, round(_DURATION_DEVIATION_POINTS * deviation))
        return ScoringFactor(
            name="duration_difference",
            label="Duration difference",
            max_points=_DURATION_DIFFERENCE_MAX,
            points=points,
            reason=f"Duration deviates by {deviation:.1%} from the reference",
        )
    return ScoringFactor(
        name="duration_difference",
        label="Duration difference",
        max_points=_DURATION_DIFFERENCE_MAX,
        points=0,
        reason="Duration matches the reference",
    )


def _frame_discontinuity_factor(count: int) -> ScoringFactor:
    if count > 0:
        points = min(_FRAME_DISCONTINUITY_MAX, count * _DISCONTINUITY_POINTS_PER_EVENT)
        return ScoringFactor(
            name="frame_discontinuity",
            label="Frame discontinuity",
            max_points=_FRAME_DISCONTINUITY_MAX,
            points=points,
            reason=f"{count} abrupt frame replacement(s) detected",
        )
    return ScoringFactor(
        name="frame_discontinuity",
        label="Frame discontinuity",
        max_points=_FRAME_DISCONTINUITY_MAX,
        points=0,
        reason="No abrupt frame discontinuities detected",
    )


def _encoding_difference_factor(differs: bool) -> ScoringFactor:
    if differs:
        return ScoringFactor(
            name="encoding_difference",
            label="Encoding difference",
            max_points=_ENCODING_DIFFERENCE_MAX,
            points=_ENCODING_DIFFERENCE_MAX,
            reason="Encoding properties (codec / pixel format) differ from the reference",
        )
    return ScoringFactor(
        name="encoding_difference",
        label="Encoding difference",
        max_points=_ENCODING_DIFFERENCE_MAX,
        points=0,
        reason="Encoding matches the reference",
    )


def _has_cluster(timestamps: tuple[float, ...]) -> bool:
    ordered = sorted(timestamps)
    for index, start in enumerate(ordered):
        within_window = sum(
            1 for timestamp in ordered[index:] if timestamp <= start + _CLUSTER_WINDOW_SECONDS
        )
        if within_window >= _CLUSTER_MIN_EVENTS:
            return True
    return False


def _unnatural_cluster_factor(timestamps: tuple[float, ...]) -> ScoringFactor:
    if _has_cluster(timestamps):
        return ScoringFactor(
            name="unnatural_frame_diff_cluster",
            label="Unnatural frame-diff cluster",
            max_points=_UNNATURAL_CLUSTER_MAX,
            points=_UNNATURAL_CLUSTER_MAX,
            reason=(
                f"At least {_CLUSTER_MIN_EVENTS} frame-difference events occur "
                f"within a {_CLUSTER_WINDOW_SECONDS:g}s window"
            ),
        )
    return ScoringFactor(
        name="unnatural_frame_diff_cluster",
        label="Unnatural frame-diff cluster",
        max_points=_UNNATURAL_CLUSTER_MAX,
        points=0,
        reason="No clustered frame-difference events detected",
    )


def _single_scene_changes_factor(event_count: int) -> ScoringFactor:
    if event_count > 0:
        return ScoringFactor(
            name="single_scene_changes",
            label="Single scene changes",
            max_points=_SINGLE_SCENE_CHANGES_MAX,
            points=_SINGLE_SCENE_CHANGES_MAX,
            reason=f"{event_count} frame-difference event(s) recorded",
        )
    return ScoringFactor(
        name="single_scene_changes",
        label="Single scene changes",
        max_points=_SINGLE_SCENE_CHANGES_MAX,
        points=0,
        reason="No frame-difference events recorded",
    )


def score_anomaly_indicators(inputs: ScoringInputs) -> AnomalyIndicatorScore:
    """Compute the explainable indicator score from the given observations.

    Every factor is reported regardless of its points so the breakdown always
    explains why the score is what it is.
    """
    factors = [
        _metadata_inconsistency_factor(inputs.metadata_inconsistent),
        _duration_difference_factor(inputs.duration_deviation),
        _frame_discontinuity_factor(inputs.discontinuities),
        _encoding_difference_factor(inputs.encoding_differs),
        _unnatural_cluster_factor(inputs.event_timestamps),
        _single_scene_changes_factor(len(inputs.event_timestamps)),
    ]
    total = sum(factor.points for factor in factors)
    return AnomalyIndicatorScore(
        score=total,
        category=category_from_score(total),
        factors=factors,
    )
