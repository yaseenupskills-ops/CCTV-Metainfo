"""The `summary` field on AnalysisRead.

`AnalysisRead` is what a list endpoint returns, and it carries no `result`: the
full result embeds every detected event with its per-frame metrics, so shipping
it per row was never viable. The consequence was that the analyses table in the
UI had nothing to show and rendered a dash in the result column for every run.

`summary` is the compact stand-in, derived on the server so the list stays small
while still saying what the analysis found.
"""

import uuid
from typing import Any

import pytest

from app.core.enums import AnalysisStatus, AnalysisType
from app.schemas.analysis import AnalysisDetail, AnalysisRead
from app.services.analysis_summary import build_analysis_summary


class FakeAnalysis:
    """Minimal stand-in for the ORM row; the helper reads structurally."""

    def __init__(
        self,
        *,
        analysis_type: AnalysisType,
        result: dict[str, Any] | None,
        status: AnalysisStatus = AnalysisStatus.COMPLETED,
    ) -> None:
        self.id = uuid.uuid4()
        self.evidence_id = uuid.uuid4()
        self.analysis_type = analysis_type
        self.status = status
        self.params = {"sampling_rate": 1}
        self.started_at = None
        self.completed_at = None
        self.error_message = None
        self.result = result


# --- build_analysis_summary ----------------------------------------------


def test_scene_change_summarizes_event_count():
    fake = FakeAnalysis(
        analysis_type=AnalysisType.SCENE_CHANGE,
        result={"events": [{"timestamp": 1.0}, {"timestamp": 4.5}, {"timestamp": 9.0}]},
    )
    assert build_analysis_summary(fake) == {"events": 3}


def test_scene_change_with_no_events_is_zero_not_none():
    """A finished run that found nothing is a real result, not a missing one."""
    fake = FakeAnalysis(analysis_type=AnalysisType.SCENE_CHANGE, result={"events": []})
    assert build_analysis_summary(fake) == {"events": 0}


def test_frame_sampling_summarizes_frames():
    fake = FakeAnalysis(
        analysis_type=AnalysisType.FRAME_SAMPLING, result={"frames_sampled": 240}
    )
    assert build_analysis_summary(fake) == {"frames_sampled": 240}


@pytest.mark.parametrize("status", [AnalysisStatus.QUEUED, AnalysisStatus.PROCESSING])
def test_no_summary_before_a_result_exists(status: AnalysisStatus):
    fake = FakeAnalysis(analysis_type=AnalysisType.SCENE_CHANGE, result=None, status=status)
    assert build_analysis_summary(fake) is None


def test_no_summary_for_a_failed_analysis():
    fake = FakeAnalysis(
        analysis_type=AnalysisType.SCENE_CHANGE,
        result=None,
        status=AnalysisStatus.FAILED,
    )
    assert build_analysis_summary(fake) is None


def test_summary_omits_the_bulky_event_payload():
    """The whole point: the summary must not carry per-event metrics."""
    events = [
        {
            "timestamp": float(i),
            "diff_score": 0.42,
            "metrics": {"a": [1.0] * 500, "b": [2.0] * 500},
        }
        for i in range(50)
    ]
    fake = FakeAnalysis(analysis_type=AnalysisType.SCENE_CHANGE, result={"events": events})

    summary = build_analysis_summary(fake)

    assert summary == {"events": 50}
    assert "metrics" not in str(summary)


# --- the schema derives it from the row ----------------------------------


def test_analysis_read_derives_summary_from_a_row():
    fake = FakeAnalysis(
        analysis_type=AnalysisType.SCENE_CHANGE,
        result={"events": [{"timestamp": 1.0}, {"timestamp": 2.0}]},
    )
    read = AnalysisRead.model_validate(fake)
    assert read.summary == {"events": 2}


def test_analysis_read_summary_defaults_to_none_without_a_result():
    fake = FakeAnalysis(analysis_type=AnalysisType.SCENE_CHANGE, result=None)
    assert AnalysisRead.model_validate(fake).summary is None


def test_analysis_detail_also_carries_the_summary_alongside_the_result():
    """Detail keeps the full result and gains the summary for free."""
    fake = FakeAnalysis(
        analysis_type=AnalysisType.SCENE_CHANGE,
        result={"events": [{"timestamp": 1.0}]},
    )
    detail = AnalysisDetail.model_validate(fake)

    assert detail.summary == {"events": 1}
    assert detail.result is not None
    assert len(detail.result["events"]) == 1


def test_explicit_summary_in_a_mapping_is_preserved():
    """A caller supplying the fields directly is not second-guessed."""
    read = AnalysisRead.model_validate(
        {
            "id": uuid.uuid4(),
            "evidence_id": uuid.uuid4(),
            "analysis_type": AnalysisType.SCENE_CHANGE,
            "status": AnalysisStatus.COMPLETED,
            "params": {},
            "started_at": None,
            "completed_at": None,
            "error_message": None,
            "summary": {"events": 99},
        }
    )
    assert read.summary == {"events": 99}


def test_summary_round_trips_through_json():
    fake = FakeAnalysis(
        analysis_type=AnalysisType.FRAME_SAMPLING, result={"frames_sampled": 12}
    )
    dumped = AnalysisRead.model_validate(fake).model_dump(mode="json")
    assert dumped["summary"] == {"frames_sampled": 12}
