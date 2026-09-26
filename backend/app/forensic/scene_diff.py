"""Deterministic frame-difference analysis for evidence videos.

Compares consecutive sampled frames using multiple detection methods: mean
absolute difference (MAD), luma histogram difference, structural similarity
(SSIM), and perceptual-hash distance. A configurable threshold marks a frame
pair as a "significant difference" event. Frame differences are reported as
*Potential anomalies* only — they never imply tampering on their own.
"""

import cv2
import numpy as np

from app.core.config import settings
from app.core.exceptions import AnalysisError
from app.forensic.frames import iter_sampled_frames
from app.forensic.perceptual import perceptual_hash, phash_distance

_SSIM_WINDOW = 11
_SSIM_SIGMA = 1.5
_HISTOGRAM_BINS = 16
_K1 = 0.01
_K2 = 0.03


def mean_absolute_difference(prev: np.ndarray, curr: np.ndarray) -> float:
    """Normalized mean absolute pixel difference between two grayscale frames (0-1)."""
    diff = cv2.absdiff(prev, curr)
    return float(diff.mean() / 255.0)


def luma_histogram_difference(prev: np.ndarray, curr: np.ndarray) -> float:
    """Normalized chi-square distance between two luma histograms (0-1)."""
    hist_a: np.ndarray = cv2.calcHist([prev], [0], None, [_HISTOGRAM_BINS], [0, 256]).reshape(-1)
    hist_b: np.ndarray = cv2.calcHist([curr], [0], None, [_HISTOGRAM_BINS], [0, 256]).reshape(-1)
    sum_a = float(hist_a.sum())
    sum_b = float(hist_b.sum())
    hist_a = (hist_a / max(sum_a, 1.0)).astype(np.float64)
    hist_b = (hist_b / max(sum_b, 1.0)).astype(np.float64)
    score = float(0.5 * np.sum((hist_a - hist_b) ** 2 / (hist_a + hist_b + 1e-6)))
    return min(score, 1.0)


def structural_similarity(prev: np.ndarray, curr: np.ndarray) -> float:
    """Local SSIM index (0-1, 1 = identical) over an 11x11 Gaussian window."""
    a = prev.astype(np.float64)
    b = curr.astype(np.float64)
    c1 = (_K1 * 255.0) ** 2
    c2 = (_K2 * 255.0) ** 2

    kernel = cv2.getGaussianKernel(_SSIM_WINDOW, _SSIM_SIGMA)
    window: np.ndarray = kernel @ kernel.T

    mu_a = cv2.filter2D(a, -1, window)
    mu_b = cv2.filter2D(b, -1, window)
    mu_a_sq, mu_b_sq = mu_a**2, mu_b**2
    mu_a_mu_b = mu_a * mu_b

    aa: np.ndarray = a * a
    bb: np.ndarray = b * b
    ab: np.ndarray = a * b
    sigma_a_sq = cv2.filter2D(aa, -1, window) - mu_a_sq
    sigma_b_sq = cv2.filter2D(bb, -1, window) - mu_b_sq
    sigma_ab = cv2.filter2D(ab, -1, window) - mu_a_mu_b

    numerator = (2.0 * mu_a_mu_b + c1) * (2.0 * sigma_ab + c2)
    denominator = (mu_a_sq + mu_b_sq + c1) * (sigma_a_sq + sigma_b_sq + c2)
    ssim_map = numerator / np.maximum(denominator, 1e-8)
    return float(np.clip(ssim_map.mean(), 0.0, 1.0))


def compute_frame_difference(prev: np.ndarray, curr: np.ndarray) -> dict:
    """Compute all diff metrics between two grayscale frames.

    Returns each raw metric plus a combined `diff_score` (the strongest signal,
    0-1) used for thresholding.
    """
    hash_a = perceptual_hash(prev)
    hash_b = perceptual_hash(curr)
    ssim = structural_similarity(prev, curr)

    metrics = {
        "mad": round(mean_absolute_difference(prev, curr), 4),
        "histogram_diff": round(luma_histogram_difference(prev, curr), 4),
        "ssim": round(ssim, 4),
        "phash_distance": round(phash_distance(hash_a, hash_b), 4),
    }
    # SSIM is a similarity score; convert to a difference measure.
    ssim_diff = 1.0 - ssim
    diff_score = max(
        metrics["mad"],
        metrics["histogram_diff"],
        ssim_diff,
        metrics["phash_distance"],
    )
    return {**metrics, "diff_score": round(diff_score, 4)}


def detect_scene_changes(path: str, sampling_rate: int, threshold: float | None = None) -> dict:
    """Detect significant frame differences between consecutive sampled frames.

    Returns the comparison summary plus one event per frame pair whose combined
    diff score exceeds `threshold` (defaults to the configured value). Each
    event is labeled a "Potential anomaly" with a severity derived from the
    diff score.
    """
    if threshold is None:
        threshold = settings.scene_diff_threshold
    if not 0.0 < threshold <= 1.0:
        raise AnalysisError("Threshold must be between 0 and 1")

    from app.forensic.scoring import severity_from_diff_score

    frames = list(iter_sampled_frames(path, sampling_rate))
    if len(frames) < 2:
        raise AnalysisError("Not enough sampled frames to compare")

    events: list[dict] = []
    for (prev_index, prev_gray, fps), (curr_index, curr_gray, _) in zip(
        frames, frames[1:], strict=False
    ):
        diff = compute_frame_difference(prev_gray, curr_gray)
        if diff["diff_score"] >= threshold:
            events.append(
                {
                    "timestamp": round(curr_index / fps, 6),
                    "prev_frame": prev_index + 1,
                    "current_frame": curr_index + 1,
                    "diff_score": diff["diff_score"],
                    "detection_method": "frame_difference",
                    "severity": severity_from_diff_score(diff["diff_score"]).value,
                    "metrics": diff,
                }
            )

    return {
        "sampling_rate": sampling_rate,
        "threshold": threshold,
        "frames_compared": len(frames) - 1,
        "events": events,
    }
