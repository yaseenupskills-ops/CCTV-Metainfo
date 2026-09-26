from pathlib import Path

import numpy as np
import pytest

from app.core.exceptions import AnalysisError
from app.forensic.scene_diff import (
    compute_frame_difference,
    detect_scene_changes,
    luma_histogram_difference,
    mean_absolute_difference,
    structural_similarity,
)


def _gray(fill: int = 0, shape=(240, 320)) -> np.ndarray:
    return np.full(shape, fill, dtype=np.uint8)


def test_mad_identical_frames_is_zero():
    frame = _gray(100)
    assert mean_absolute_difference(frame, frame.copy()) == 0.0


def test_mad_opposite_frames_is_one():
    black, white = _gray(0), _gray(255)
    assert mean_absolute_difference(black, white) == pytest.approx(1.0, abs=1e-3)


def test_histogram_difference_identical_is_zero():
    frame = _gray(80)
    assert luma_histogram_difference(frame, frame.copy()) == 0.0


def test_ssim_identical_is_one():
    frame = _gray(100)
    assert structural_similarity(frame, frame.copy()) == pytest.approx(1.0, abs=1e-3)


def test_compute_frame_difference_identical():
    frame = _gray(120)
    diff = compute_frame_difference(frame, frame.copy())
    assert diff["mad"] == 0.0
    assert diff["histogram_diff"] == 0.0
    assert diff["ssim"] == pytest.approx(1.0, abs=1e-3)
    assert diff["phash_distance"] == 0.0
    assert diff["diff_score"] == 0.0


def test_detect_scene_changes_detects_black_white_cut(scene_change_video_factory):
    video = scene_change_video_factory()
    result = detect_scene_changes(str(video), sampling_rate=1, threshold=0.5)

    assert result["sampling_rate"] == 1
    assert result["threshold"] == 0.5
    assert result["frames_compared"] >= 1
    assert result["events"], "expected at least one event at the scene cut"

    event = result["events"][0]
    assert event["detection_method"] == "frame_difference"
    assert event["current_frame"] > event["prev_frame"]
    assert event["diff_score"] >= 0.5
    assert event["severity"] in {"low", "medium", "high"}
    assert "mad" in event["metrics"]
    assert "ssim" in event["metrics"]


def test_detect_scene_changes_no_events_on_constant_video(video_factory):
    video = video_factory(duration=3, fps=10, pattern="color=gray")
    result = detect_scene_changes(str(video), sampling_rate=1, threshold=0.5)

    assert result["frames_compared"] >= 1
    assert result["events"] == []


def test_detect_scene_changes_default_threshold(scene_change_video_factory):
    video = scene_change_video_factory()
    result = detect_scene_changes(str(video), sampling_rate=1)
    assert result["threshold"] == 0.35


def test_detect_scene_changes_rejects_bad_threshold(video_factory):
    video = video_factory(duration=1, fps=10)
    with pytest.raises(AnalysisError, match="Threshold"):
        detect_scene_changes(str(video), sampling_rate=1, threshold=0.0)


def test_detect_scene_changes_rejects_unsupported_rate(video_factory):
    video = video_factory(duration=1, fps=10)
    with pytest.raises(AnalysisError, match="Unsupported sampling rate"):
        detect_scene_changes(str(video), sampling_rate=7)


def test_detect_scene_changes_missing_file(tmp_path: Path):
    with pytest.raises(AnalysisError, match="Could not open"):
        detect_scene_changes(str(tmp_path / "missing.mp4"), sampling_rate=1)
