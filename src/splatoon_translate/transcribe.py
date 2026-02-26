"""Japanese speech-to-text transcription."""

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


def transcribe(
    audio_path: Path,
    model_size: str | None = None,
    device: str | None = None,
    compute_type: str | None = None,
    language: str | None = None,
) -> list[TranscriptSegment]:
    """Transcribe audio using faster-whisper.

    Returns a list of TranscriptSegment with timestamps.
    """
    from faster_whisper import WhisperModel

    model_size = model_size or config.ASR_MODEL_SIZE
    device = device or config.ASR_DEVICE
    compute_type = compute_type or config.ASR_COMPUTE_TYPE
    language = language or config.ASR_LANGUAGE

    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    segments_iter, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=config.ASR_BEAM_SIZE,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        word_timestamps=True,
    )

    segments = []
    for seg in segments_iter:
        # Skip segments that are likely hallucinations.
        if seg.no_speech_prob > 0.6:
            continue
        words = []
        if seg.words:
            words = [{"start": w.start, "end": w.end, "word": w.word} for w in seg.words]
        segments.append(TranscriptSegment(
            start=seg.start,
            end=seg.end,
            text=seg.text.strip(),
            words=words,
        ))

    return segments
