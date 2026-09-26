"""Deterministic frame sampling for evidence videos.

Streams a working copy with OpenCV and records compact per-frame data
(number, timestamp, perceptual hash, luma statistics, histogram). No images
are stored; anomaly frames are handled in later phases.
"""

import cv2
import numpy as np

from app.core.config import settings
from app.core.exceptions import AnalysisError
from app.forensic.perceptual import perceptual_hash

_HISTOGRAM_BINS = 16


def _frame_timestamp(frame_index: int, fps: float) -> float:
    return frame_index / fps if fps > 0 else 0.0


def _frame_stats(gray: np.ndarray) -> tuple[float, float]:
    mean, stddev = cv2.meanStdDev(gray)
    return float(mean[0][0]), float(stddev[0][0])


def _luma_histogram(gray: np.ndarray) -> list[float]:
    hist = cv2.calcHist([gray], [0], None, [_HISTOGRAM_BINS], [0, 256]).reshape(-1)
    total = hist.sum()
    if total <= 0:
        return [0.0] * _HISTOGRAM_BINS
    return [round(float(count) / float(total), 6) for count in hist]


def _sample_frame(gray: np.ndarray, frame_index: int, fps: float) -> dict:
    mean, std = _frame_stats(gray)
    return {
        "frame_number": frame_index + 1,
        "timestamp": round(_frame_timestamp(frame_index, fps), 6),
        "phash": perceptual_hash(gray),
        "mean": round(mean, 4),
        "std": round(std, 4),
        "histogram": _luma_histogram(gray),
    }


def iter_sampled_frames(path: str, sampling_rate: int):
    """Yield (frame_index, gray_frame, fps) at the requested sampling rate.

    Streaming: only the sampled frames are held in memory. Frame indexes are
    zero-based positions in the original stream.
    """
    if sampling_rate not in settings.frame_sampling_rates:
        allowed = ", ".join(str(rate) for rate in settings.frame_sampling_rates)
        raise AnalysisError(f"Unsupported sampling rate {sampling_rate}. Allowed: {allowed}")

    capture = cv2.VideoCapture(path)
    if not capture.isOpened():
        raise AnalysisError("Could not open the video for frame sampling")

    fps = capture.get(cv2.CAP_PROP_FPS)
    interval = max(1, round(fps / sampling_rate)) if fps > 0 else 1

    frame_index = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if frame_index % interval == 0:
            yield frame_index, cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), fps
        frame_index += 1
    capture.release()


def extract_frames(path: str, sampling_rate: int) -> dict:
    """Sample frames from a video at the requested rate (frames per second).

    Returns a summary plus one compact record per sampled frame. Frames are
    chosen deterministically from the start of the stream.
    """
    if sampling_rate not in settings.frame_sampling_rates:
        allowed = ", ".join(str(rate) for rate in settings.frame_sampling_rates)
        raise AnalysisError(f"Unsupported sampling rate {sampling_rate}. Allowed: {allowed}")

    capture = cv2.VideoCapture(path)
    if not capture.isOpened():
        raise AnalysisError("Could not open the video for frame sampling")

    fps = capture.get(cv2.CAP_PROP_FPS)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    capture.release()

    frames: list[dict] = []
    for frame_index, gray, source_fps in iter_sampled_frames(path, sampling_rate):
        frames.append(_sample_frame(gray, frame_index, source_fps))

    if not frames:
        raise AnalysisError("No frames could be read from the video")

    return {
        "sampling_rate": sampling_rate,
        "source": {
            "width": width,
            "height": height,
            "fps": round(fps, 4),
            "total_frames": total_frames,
        },
        "frames_sampled": len(frames),
        "frames": frames,
    }
