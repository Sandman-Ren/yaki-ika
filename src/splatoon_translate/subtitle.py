"""SRT subtitle generation with line wrapping."""

import logging
from pathlib import Path

from . import config
from .config import get_lang_config
from .translate import TranslatedSegment

logger = logging.getLogger(__name__)


def _format_timestamp(seconds: float) -> str:
    """Convert float seconds to SRT timestamp HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _wrap_line(text: str, max_chars: int | None = None, target_lang: str | None = None) -> str:
    """Wrap subtitle text to fit within character limits.

    Splits into at most 2 lines at the nearest word boundary.
    For CJK text, can split at any character boundary.
    """
    if max_chars is None:
        cfg = get_lang_config(target_lang)
        max_chars = cfg["max_chars_per_line"]
    if len(text) <= max_chars:
        return text

    # Find the best split point near the middle.
    mid = len(text) // 2
    # Search outward from the middle for a space.
    best = -1
    for offset in range(mid):
        for pos in (mid + offset, mid - offset):
            if 0 < pos < len(text) and text[pos] == " ":
                best = pos
                break
        if best != -1:
            break

    if best == -1:
        # No space found; hard-wrap at max_chars.
        return text[:max_chars] + "\n" + text[max_chars:]

    line1 = text[:best]
    line2 = text[best + 1:]

    # If either line is still too long, truncate rather than add a 3rd line.
    if len(line1) > max_chars:
        logger.warning("Hard-truncating subtitle line from %d to %d chars: '%s'", len(line1), max_chars, line1)
        line1 = line1[:max_chars]
    if len(line2) > max_chars:
        logger.warning("Hard-truncating subtitle line from %d to %d chars: '%s'", len(line2), max_chars, line2)
        line2 = line2[:max_chars]

    return line1 + "\n" + line2


def segments_to_srt(segments: list[TranslatedSegment], output_path: Path, target_lang: str | None = None) -> Path:
    """Write translated segments as an SRT file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for seg in segments:
            start = _format_timestamp(seg.start)
            end = _format_timestamp(seg.end)
            text = _wrap_line(seg.translated, target_lang=target_lang)
            f.write(f"{seg.index}\n{start} --> {end}\n{text}\n\n")
    return output_path


def segments_to_bilingual_srt(
    segments: list[TranslatedSegment], output_path: Path, target_lang: str | None = None
) -> Path:
    """Write segments as a bilingual SRT (JP on top, translated below) for review."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for seg in segments:
            start = _format_timestamp(seg.start)
            end = _format_timestamp(seg.end)
            translated_text = _wrap_line(seg.translated, target_lang=target_lang)
            f.write(f"{seg.index}\n{start} --> {end}\n{seg.original}\n{translated_text}\n\n")
    return output_path


def transcript_to_srt(segments, output_path: Path) -> Path:
    """Write raw TranscriptSegments (JP only) as SRT."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            start = _format_timestamp(seg.start)
            end = _format_timestamp(seg.end)
            f.write(f"{i}\n{start} --> {end}\n{seg.text}\n\n")
    return output_path
