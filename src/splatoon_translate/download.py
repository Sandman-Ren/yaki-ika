"""Video download via yt-dlp."""

import subprocess
from pathlib import Path


def download_video(url: str, output_dir: Path) -> Path:
    """Download video using yt-dlp. Returns path to the downloaded file."""
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(title)s.%(ext)s")

    result = subprocess.run(
        [
            "yt-dlp",
            "-f", "bv*[height<=1080]+ba/best",
            "--merge-output-format", "mp4",
            "--print", "after_move:filepath",
            "-o", output_template,
            "--encoding", "utf-8",
            url,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    filepath = result.stdout.strip().splitlines()[-1]
    return Path(filepath)


def download_auto_subs(url: str, output_dir: Path, lang: str = "ja") -> Path | None:
    """Download auto-generated subtitles if available. Returns path or None."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(output_dir / "%(title)s.%(ext)s")

    result = subprocess.run(
        [
            "yt-dlp",
            "--write-auto-subs",
            "--sub-lang", lang,
            "--sub-format", "srt",
            "--skip-download",
            "-o", output_template,
            url,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None

    # Find the .srt file that was written.
    srt_files = list(output_dir.glob(f"*.{lang}.srt"))
    return srt_files[0] if srt_files else None
