"""Japanese speech-to-text transcription with Splatoon-specific corrections."""

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

from . import config


@dataclass
class TranscriptSegment:
    """A single transcribed segment with timestamps."""
    start: float
    end: float
    text: str
    words: list[dict] = field(default_factory=list)


def _load_corrections() -> dict | None:
    """Load the Whisper correction dictionary."""
    corrections_path = config.CORRECTIONS_DIR / "whisper_corrections.json"
    if not corrections_path.exists():
        return None
    with open(corrections_path, encoding="utf-8") as f:
        return json.load(f)


def _build_initial_prompt() -> str:
    """Build the initial_prompt string from the correction dictionary.

    The initial_prompt guides Whisper's language model toward Splatoon terminology,
    reducing misrecognitions of coined katakana terms.
    Limited to ~200 tokens to stay within Whisper's 244-token prompt window.
    """
    corrections = _load_corrections()
    if not corrections:
        return ""
    terms = corrections.get("initial_prompt_terms", [])
    return "".join(terms)


def _apply_corrections(text: str) -> str:
    """Apply post-transcription corrections to a segment's text.

    Handles three types of corrections:
    1. Compound word rejoining (split katakana compounds)
    2. Kanji-to-katakana corrections (homophonic substitutions)
    3. Hallucination removal (training data artifacts)
    """
    corrections = _load_corrections()
    if not corrections:
        return text

    cfg = corrections.get("correction_config", {})

    for entry in corrections.get("corrections", []):
        wrong = entry["wrong"]
        correct = entry["correct"]
        action = entry.get("action", "replace")
        ctype = entry.get("type", "")
        guard = entry.get("guard")

        if wrong not in text:
            continue

        # Skip guarded corrections — these need broader context to be safe.
        # For now, only apply unguarded corrections automatically.
        if guard and cfg.get("guarded_corrections_require_context", True):
            continue

        if action == "remove":
            text = text.replace(wrong, "")
        elif action == "flag":
            # Keep text but could be flagged in the future
            continue
        else:
            text = text.replace(wrong, correct)

    return text.strip()


def transcribe(
    audio_path: Path,
    model_size: str | None = None,
    device: str | None = None,
    compute_type: str | None = None,
    language: str | None = None,
) -> list[TranscriptSegment]:
    """Transcribe audio using faster-whisper.

    Returns a list of TranscriptSegment with timestamps.
    Uses Splatoon-specific initial_prompt to guide recognition
    and applies post-transcription corrections.
    """
    from faster_whisper import WhisperModel

    model_size = model_size or config.ASR_MODEL_SIZE
    device = device or config.ASR_DEVICE
    compute_type = compute_type or config.ASR_COMPUTE_TYPE
    language = language or config.ASR_LANGUAGE

    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    # Build initial_prompt with Splatoon terminology to guide Whisper.
    initial_prompt = _build_initial_prompt()

    transcribe_kwargs = dict(
        language=language,
        beam_size=config.ASR_BEAM_SIZE,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        word_timestamps=True,
    )
    if initial_prompt:
        transcribe_kwargs["initial_prompt"] = initial_prompt

    segments_iter, info = model.transcribe(str(audio_path), **transcribe_kwargs)

    segments = []
    for seg in segments_iter:
        # Skip segments that are likely hallucinations.
        if seg.no_speech_prob > 0.6:
            continue
        text = seg.text.strip()

        # Apply Splatoon-specific corrections.
        text = _apply_corrections(text)
        if not text:
            continue

        words = []
        if seg.words:
            words = [{"start": w.start, "end": w.end, "word": w.word} for w in seg.words]
        segments.append(TranscriptSegment(
            start=seg.start,
            end=seg.end,
            text=text,
            words=words,
        ))

    return segments
