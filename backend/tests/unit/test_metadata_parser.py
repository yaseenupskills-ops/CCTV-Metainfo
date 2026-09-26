from datetime import UTC, datetime

import pytest

from app.services.metadata_service import (
    normalize_metadata,
    parse_creation_time,
    parse_frame_rate,
)
from app.services.structure_service import parse_structure

PROBE_MP4 = {
    "streams": [
        {
            "index": 0,
            "codec_name": "h264",
            "codec_type": "video",
            "width": 1920,
            "height": 1080,
            "pix_fmt": "yuv420p",
            "r_frame_rate": "30000/1001",
            "avg_frame_rate": "30000/1001",
            "nb_frames": "300",
            "duration": "10.000000",
            "tags": {"encoder": "Lavc60.3.100 libx264"},
        },
        {
            "index": 1,
            "codec_name": "aac",
            "codec_type": "audio",
        },
    ],
    "format": {
        "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
        "duration": "10.000000",
        "bit_rate": "2628000",
        "tags": {
            "creation_time": "2024-01-15T10:00:00.000000Z",
            "encoder": "Lavf60.3.100",
        },
    },
}


def test_normalize_metadata_maps_all_fields():
    result = normalize_metadata(PROBE_MP4)
    assert result["container_format"] == "mov,mp4,m4a,3gp,3g2,mj2"
    assert result["duration"] == 10.0
    assert result["width"] == 1920
    assert result["height"] == 1080
    assert result["frame_rate"] == pytest.approx(29.97, rel=1e-2)
    assert result["frame_count"] == 300
    assert result["video_codec"] == "h264"
    assert result["audio_codec"] == "aac"
    assert result["bitrate"] == 2628000
    assert result["pixel_format"] == "yuv420p"
    assert result["stream_count"] == 2
    assert result["creation_time"] == datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
    assert result["encoder"] == "Lavc60.3.100 libx264"


def test_normalize_metadata_no_video_stream():
    probe = {"streams": [{"index": 0, "codec_name": "aac", "codec_type": "audio"}], "format": {}}
    result = normalize_metadata(probe)
    assert result["width"] is None
    assert result["height"] is None
    assert result["video_codec"] is None
    assert result["frame_rate"] is None
    assert result["audio_codec"] == "aac"


def test_normalize_metadata_handles_missing_numeric_values():
    probe = {"streams": [{"codec_type": "video", "nb_frames": "N/A"}], "format": {}}
    result = normalize_metadata(probe)
    assert result["frame_count"] is None
    assert result["duration"] is None
    assert result["bitrate"] is None


def test_parse_frame_rate():
    assert parse_frame_rate({"r_frame_rate": "30000/1001"}) == pytest.approx(29.97, rel=1e-2)
    assert parse_frame_rate({"r_frame_rate": "25/1"}) == 25.0
    assert parse_frame_rate({"r_frame_rate": "0/0"}) is None
    assert parse_frame_rate({}) is None
    assert parse_frame_rate({"r_frame_rate": "garbage"}) is None


def test_parse_creation_time():
    assert parse_creation_time(
        {"format": {"tags": {"creation_time": "2024-01-15T10:00:00.000000Z"}}}
    ) == datetime(2024, 1, 15, 10, 0, tzinfo=UTC)
    assert parse_creation_time({"format": {"tags": {"creation_time": "not-a-date"}}}) is None
    assert parse_creation_time({"format": {}}) is None
    assert parse_creation_time({}) is None


FRAMES = {
    "frames": [
        {"key_frame": 1, "pts_time": "0.000000", "pict_type": "I"},
        {"key_frame": 0, "pts_time": "0.100000", "pict_type": "B"},
        {"key_frame": 1, "pts_time": "1.000000", "pict_type": "I"},
        {"key_frame": 0, "pts_time": "1.100000", "pict_type": "B"},
        {"key_frame": "1", "pts_time": "2.000000", "pict_type": "I"},
    ]
}


def test_parse_structure_counts_keyframes():
    result = parse_structure(FRAMES)
    assert result["frame_count_probed"] == 5
    assert result["keyframe_count"] == 3
    assert result["first_keyframe_time"] == 0.0
    assert [k["pict_type"] for k in result["keyframes"]] == ["I", "I", "I"]


def test_parse_structure_avg_keyframe_interval():
    result = parse_structure(FRAMES)
    assert result["avg_keyframe_interval"] == pytest.approx(1.0)


def test_parse_structure_empty_and_single():
    assert parse_structure({"frames": []})["keyframe_count"] == 0
    single = parse_structure({"frames": [{"key_frame": 1, "pts_time": "0.5", "pict_type": "I"}]})
    assert single["keyframe_count"] == 1
    assert single["avg_keyframe_interval"] is None
