"""FFmpeg subtitle burn-in and soft subtitle embedding."""

import argparse
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


def _probe_video_bitrate(video_path: Path) -> int | None:
    """Probe the video stream bitrate in bits/sec. Returns None on failure."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=bit_rate", "-of", "csv=p=0",
             str(video_path)],
            capture_output=True, text=True,
        )
        value = result.stdout.strip()
        if value and value != "N/A":
            return int(value)
    except (subprocess.SubprocessError, ValueError):
        pass
    return None


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
    Matches the source video bitrate to avoid file size blowup.
    """
    video_path = Path(video_path).resolve()
    srt_path = Path(srt_path).resolve()
    style = style or get_subtitle_style(target_lang)
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Probe source bitrate to avoid overshooting.
    source_bitrate = _probe_video_bitrate(video_path)
    # Target ~110% of source (small margin for subtitle overlay complexity).
    if source_bitrate:
        target_kbps = str(int(source_bitrate * 1.1 / 1000)) + "k"
        maxrate = str(int(source_bitrate * 1.5 / 1000)) + "k"
    else:
        target_kbps = None
        maxrate = None

    # Copy SRT to a temp dir and run FFmpeg from there to avoid Windows
    # path escaping issues (drive letter colons break FFmpeg filter parsing).
    tmp_dir = tempfile.mkdtemp()
    tmp_srt = Path(tmp_dir) / "subs.srt"
    shutil.copy2(srt_path, tmp_srt)

    vf = f"subtitles=subs.srt:force_style='{style}'"

    def _build_cmd(use_gpu: bool) -> list[str]:
        if use_gpu:
            codec_args = ["-c:v", "h264_nvenc", "-cq", "28", "-preset", "p4"]
            if target_kbps:
                codec_args += ["-b:v", target_kbps, "-maxrate", maxrate, "-bufsize", maxrate]
        else:
            codec_args = ["-c:v", "libx264", "-crf", "23", "-preset", "medium"]
            if target_kbps:
                codec_args += ["-maxrate", maxrate, "-bufsize", maxrate]
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


def main():
    """CLI entry point for standalone subtitle burn-in."""
    parser = argparse.ArgumentParser(
        description="Burn or embed subtitles into a video file",
    )
    parser.add_argument("video", type=Path, help="Input video file")
    parser.add_argument("subtitle", type=Path, help="SRT subtitle file to burn in")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output video path (default: <video>.subtitled.mp4)",
    )
    parser.add_argument(
        "-l", "--lang", default=None,
        choices=list(config.LANGUAGE_CONFIGS.keys()),
        help="Target language for subtitle styling (default: zh-CN)",
    )
    parser.add_argument(
        "--soft", action="store_true",
        help="Add as toggleable subtitle track instead of burning in (no re-encode)",
    )
    parser.add_argument(
        "--cpu", action="store_true",
        help="Use CPU encoding (default: GPU with h264_nvenc)",
    )
    args = parser.parse_args()

    video = Path(args.video)
    subtitle = Path(args.subtitle)
    if not video.exists():
        parser.error(f"Video not found: {video}")
    if not subtitle.exists():
        parser.error(f"Subtitle not found: {subtitle}")

    output = args.output or video.with_stem(f"{video.stem}.subtitled")
    if output.suffix not in (".mp4", ".mkv"):
        output = output.with_suffix(".mp4")

    if args.soft:
        result = add_soft_subtitles(video, subtitle, output)
        print(f"Soft subtitles added: {result}")
    else:
        result = burn_subtitles(video, subtitle, output, target_lang=args.lang, gpu=not args.cpu)
        print(f"Subtitles burned in: {result}")


if __name__ == "__main__":
    main()
