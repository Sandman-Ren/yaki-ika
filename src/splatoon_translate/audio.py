"""Audio extraction and voice activity detection."""

import subprocess
from pathlib import Path


def extract_audio(video_path: Path, output_dir: Path | None = None) -> Path:
    """Extract 16kHz mono WAV from video for Whisper transcription."""
    video_path = video_path.resolve()
    output_dir = (output_dir or video_path.parent).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / (video_path.stem + ".wav")

    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {result.stderr}")
    return audio_path
