from pathlib import Path

import pytest

from app.core.exceptions import AnalysisError
from app.forensic.frames import extract_frames


def test_extract_frames_sampling_count(video_factory):
    """A 10s video sampled at 1fps yields ~10 frame entries."""
    video = video_factory(duration=10, fps=10)
    result = extract_frames(str(video), 1)

    assert result["sampling_rate"] == 1
    assert 8 <= result["frames_sampled"] <= 12
    assert result["source"]["fps"] == pytest.approx(10.0, abs=0.1)
    assert result["source"]["width"] == 320
    assert result["source"]["height"] == 240


def test_extract_frames_sampling_rate_two(video_factory):
    video = video_factory(duration=5, fps=10)
    result = extract_frames(str(video), 2)

    assert result["sampling_rate"] == 2
    assert 8 <= result["frames_sampled"] <= 12


def test_extract_frames_timestamp_math(video_factory):
    """Timestamps are monotonic and derived from the source frame rate."""
    video = video_factory(duration=10, fps=10)
    result = extract_frames(str(video), 1)

    timestamps = [frame["timestamp"] for frame in result["frames"]]
    assert timestamps == sorted(timestamps)
    assert timestamps[0] == pytest.approx(0.0, abs=1e-3)
    step = timestamps[1] - timestamps[0]
    assert step == pytest.approx(1.0, abs=0.05)
    for frame in result["frames"]:
        assert frame["frame_number"] >= 1
        expected = round((frame["frame_number"] - 1) / result["source"]["fps"], 3)
        assert frame["timestamp"] == pytest.approx(expected, abs=0.05)


def test_extract_frames_per_frame_fields(video_factory):
    video = video_factory(duration=2, fps=10)
    result = extract_frames(str(video), 1)

    for frame in result["frames"]:
        assert len(frame["phash"]) == 16
        assert int(frame["phash"], 16) >= 0
        assert 0.0 <= frame["mean"] <= 255.0
        assert frame["std"] >= 0.0
        assert len(frame["histogram"]) == 16
        assert sum(frame["histogram"]) == pytest.approx(1.0, abs=0.01)


def test_extract_frames_phash_deterministic(video_factory):
    video = video_factory(duration=2, fps=10)
    first = extract_frames(str(video), 1)
    second = extract_frames(str(video), 1)

    assert first["frames"] == second["frames"]


def test_extract_frames_phash_differs_across_scene(video_factory):
    """A black frame and a testsrc frame should not share a perceptual hash."""
    black = video_factory(duration=1, fps=5, pattern="color=black")
    bright = video_factory(duration=1, fps=5, pattern="testsrc")

    black_result = extract_frames(str(black), 1)
    bright_result = extract_frames(str(bright), 1)

    assert black_result["frames"][0]["phash"] != bright_result["frames"][0]["phash"]


def test_extract_frames_rejects_unsupported_rate(video_factory):
    video = video_factory(duration=1, fps=10)
    with pytest.raises(AnalysisError, match="Unsupported sampling rate"):
        extract_frames(str(video), 7)


def test_extract_frames_missing_file(tmp_path: Path):
    with pytest.raises(AnalysisError, match="Could not open"):
        extract_frames(str(tmp_path / "missing.mp4"), 1)


def test_extract_frames_corrupt_file(tmp_path: Path):
    corrupt = tmp_path / "corrupt.mp4"
    corrupt.write_bytes(b"this is not a real video file")
    with pytest.raises(AnalysisError):
        extract_frames(str(corrupt), 1)
