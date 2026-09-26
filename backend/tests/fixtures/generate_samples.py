"""Sample-video generation helpers for tests.

Uses FFmpeg (lavfi testsrc) to create tiny, deterministic videos. All videos
are skipped cleanly when FFmpeg is unavailable.
"""

import subprocess
from pathlib import Path

from app.core.exceptions import AnalysisError
from app.forensic.media import resolve_ffmpeg


def generate_video(
    destination: Path,
    *,
    source: str,
) -> Path:
    """Generate a small MP4 video at `destination` from a lavfi source and return its path."""
    ffmpeg = resolve_ffmpeg()
    result = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            source,
            "-pix_fmt",
            "yuv420p",
            str(destination),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not destination.exists():
        raise AnalysisError("Could not generate sample video")
    return destination


def video_factory(tmp_path_factory):
    """Return a function that generates a video of the requested length."""

    def _make(
        *,
        duration: float,
        fps: int = 10,
        size: str = "320x240",
        pattern: str = "testsrc",
    ) -> Path:
        source = f"{pattern}=duration={duration}:size={size}:rate={fps}"
        if pattern.startswith("color"):
            source = f"color={pattern[6:]}:size={size}:rate={fps}:duration={duration}"
        path = (
            tmp_path_factory.mktemp("samples")
            / f"{pattern.split(':')[0]}_{duration}s_{fps}fps_{size.replace(':', 'x')}.mp4"
        )
        return generate_video(path, source=source)

    return _make


def scene_change_video_factory(tmp_path_factory):
    """Return a function that generates a video with an abrupt scene change.

    Concatenates two solid-color clips (default: 2s black then 2s white) so
    every sampled frame pair across the cut shows a maximal difference while
    frames within each half are identical.
    """

    def _make(
        *,
        first_color: str = "black",
        second_color: str = "white",
        duration_per_half: float = 2.0,
        fps: int = 10,
        size: str = "320x240",
    ) -> Path:
        ffmpeg = resolve_ffmpeg()
        path = (
            tmp_path_factory.mktemp("samples")
            / f"scene_{first_color}_{second_color}_{duration_per_half}s.mp4"
        )
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color={first_color}:size={size}:rate={fps}:duration={duration_per_half}",
                "-f",
                "lavfi",
                "-i",
                f"color={second_color}:size={size}:rate={fps}:duration={duration_per_half}",
                "-filter_complex",
                "[0:v][1:v]concat=n=2:v=1:a=0",
                "-pix_fmt",
                "yuv420p",
                str(path),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not path.exists():
            raise AnalysisError("Could not generate scene-change sample video")
        return path

    return _make


def sample_video_family(tmp_path_factory):
    """Generate a related family of sample videos from one base clip.

    Returns a dict of ``Path`` values derived from a common 4s testsrc clip so
    comparison/scoring tests can exercise real "original vs suspected" cases:

    - ``base``:                 normal 4s clip (320x240, 10 fps)
    - ``trimmed``:              first 2 seconds of ``base``
    - ``reencoded``:            same content, re-encoded with a different CRF
    - ``different_resolution``: same duration, 640x480
    - ``different_fps``:        same duration, 5 fps
    - ``metadata_modified``:    ``base`` with extra container metadata
    - ``joined``:               two ``base`` clips concatenated (8s)
    """
    ffmpeg = resolve_ffmpeg()
    samples = tmp_path_factory.mktemp("samples")
    base = samples / "base.mp4"
    generate_video(
        base,
        source="testsrc=duration=4:size=320x240:rate=10",
    )

    def _run(args: list[str], destination: Path) -> Path:
        result = subprocess.run(args, capture_output=True, text=True)
        if result.returncode != 0 or not destination.exists():
            raise AnalysisError(f"Could not generate sample: {destination.name}")
        return destination

    trimmed = _run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(base),
            "-t",
            "2",
            "-c",
            "copy",
            str(samples / "trimmed.mp4"),
        ],
        samples / "trimmed.mp4",
    )

    reencoded = _run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(base),
            "-c:v",
            "libx264",
            "-crf",
            "32",
            "-pix_fmt",
            "yuv420p",
            str(samples / "reencoded.mp4"),
        ],
        samples / "reencoded.mp4",
    )

    different_resolution = _run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=4:size=640x480:rate=10",
            "-pix_fmt",
            "yuv420p",
            str(samples / "different_resolution.mp4"),
        ],
        samples / "different_resolution.mp4",
    )

    different_fps = _run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=4:size=320x240:rate=5",
            "-pix_fmt",
            "yuv420p",
            str(samples / "different_fps.mp4"),
        ],
        samples / "different_fps.mp4",
    )

    metadata_modified = _run(
        [
            ffmpeg,
            "-y",
            "-i",
            str(base),
            "-c",
            "copy",
            "-metadata",
            "title=Modified evidence copy",
            "-metadata",
            "comment=Injected metadata for testing",
            str(samples / "metadata_modified.mp4"),
        ],
        samples / "metadata_modified.mp4",
    )

    joined = _run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=4:size=320x240:rate=10",
            "-f",
            "lavfi",
            "-i",
            "testsrc=duration=4:size=320x240:rate=10",
            "-filter_complex",
            "[0:v][1:v]concat=n=2:v=1:a=0",
            "-pix_fmt",
            "yuv420p",
            str(samples / "joined.mp4"),
        ],
        samples / "joined.mp4",
    )

    return {
        "base": base,
        "trimmed": trimmed,
        "reencoded": reencoded,
        "different_resolution": different_resolution,
        "different_fps": different_fps,
        "metadata_modified": metadata_modified,
        "joined": joined,
    }
