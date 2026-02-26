"""FFmpeg subtitle burn-in and soft subtitle embedding."""

import subprocess
import shutil
import tempfile
from pathlib import Path

from . import config
from .config import get_subtitle_style


def _escape_srt_path(srt_path: Path) -> str:
    """Escape SRT path for FFmpeg subtitle filter on Windows.

    FFmpeg subtitle filter interprets colons and backslashes specially.
    """
    s = str(srt_path).replace("\\", "/")
    s = s.replace(":", "\\:")
    return s


def burn_subtitles(
    video_path: Path,
    srt_path: Path,
    output_path: Path,
    style: str | None = None,
    target_lang: str | None = None,
    gpu: bool = True,
) -> Path:
    """Burn subtitles into video using FFmpeg.

    Uses h264_nvenc (GPU) if available and gpu=True, otherwise libx264.
    """
    video_path = Path(video_path).resolve()
    srt_path = Path(srt_path).resolve()
    style = style or get_subtitle_style(target_lang)
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Copy SRT to a temp dir and run FFmpeg from there to avoid Windows
    # path escaping issues (drive letter colons break FFmpeg filter parsing).
    tmp_dir = tempfile.mkdtemp()
    tmp_srt = Path(tmp_dir) / "subs.srt"
    shutil.copy2(srt_path, tmp_srt)

    vf = f"subtitles=subs.srt:force_style='{style}'"

    def _build_cmd(use_gpu: bool) -> list[str]:
        if use_gpu:
            codec_args = ["-c:v", "h264_nvenc", "-cq", "18", "-preset", "p4"]
        else:
            codec_args = ["-c:v", "libx264", "-crf", "18", "-preset", "medium"]
        return [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", vf,
            *codec_args,
            "-c:a", "aac", "-b:a", "192k",
            str(output_path),
        ]

    try:
        cmd = _build_cmd(gpu)
        result = subprocess.run(cmd, capture_output=True, cwd=tmp_dir)
        if result.returncode != 0 and gpu:
            # Fallback to CPU encoding if GPU fails.
            cmd = _build_cmd(False)
            result = subprocess.run(cmd, capture_output=True, cwd=tmp_dir)
        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"FFmpeg failed:\n{stderr}")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return output_path


def add_soft_subtitles(
    video_path: Path,
    srt_path: Path,
    output_path: Path,
    language: str = "eng",
) -> Path:
    """Add subtitle as a toggleable track (no re-encoding, fast)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(srt_path),
            "-c", "copy",
            "-c:s", "mov_text",
            "-metadata:s:s:0", f"language={language}",
            str(output_path),
        ],
        capture_output=True,
        check=True,
    )
    return output_path
