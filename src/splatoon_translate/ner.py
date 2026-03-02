"""NER pre-scan: detect player names, channel names, and unknown game terms.

Sends the full transcript to a fast model (Haiku) in a single API call
to identify entities before the main translation pass. This allows the
translator to preserve names and maintain consistency for unknown terms.
"""

import json
import logging
from dataclasses import dataclass, field

from pydantic import BaseModel

from . import config
from .transcribe import TranscriptSegment

logger = logging.getLogger(__name__)

# Minimum segment count to justify an NER pass.
_MIN_SEGMENTS = 10


# ── Data structures ──────────────────────────────────────────────────────


class DetectedEntityModel(BaseModel):
    """Pydantic model for structured NER output."""
    text: str
    entity_type: str  # "player_name", "channel_name", "unknown_game_term"
    handling: str     # "preserve", "transliterate", "translate"


class NERResultModel(BaseModel):
    """Structured output from the NER pre-scan."""
    names: list[DetectedEntityModel] = []
    unknown_terms: list[DetectedEntityModel] = []


@dataclass
class DetectedEntity:
    """A single detected entity from the NER pre-scan."""
    text: str
    entity_type: str       # "player_name", "channel_name", "unknown_game_term"
    handling: str           # "preserve", "transliterate", "translate"
    suggested_category: str = ""
    frequency: int = 0


@dataclass
class EntityRegistry:
    """Registry of all detected entities from the NER pre-scan."""
    names: list[DetectedEntity] = field(default_factory=list)
    unknown_terms: list[DetectedEntity] = field(default_factory=list)
    entity_frequencies: dict[str, int] = field(default_factory=dict)

    def format_names_section(self) -> str:
        """Format detected names for prompt injection."""
        if not self.names:
            return ""
        lines = ["DETECTED NAMES (do NOT translate — preserve original form):"]
        for entity in self.names:
            freq = f" (appears {entity.frequency}x)" if entity.frequency > 1 else ""
            lines.append(f"  {entity.text} [{entity.entity_type}]{freq}")
        return "\n".join(lines)

    def format_unknown_terms_section(self) -> str:
        """Format unknown game terms for prompt injection."""
        if not self.unknown_terms:
            return ""
        lines = ["UNRECOGNIZED GAME TERMS (translate consistently, report in entities field):"]
        for entity in self.unknown_terms:
            freq = f" (appears {entity.frequency}x)" if entity.frequency > 1 else ""
            lines.append(f"  {entity.text}{freq}")
        return "\n".join(lines)

    def get_name_set(self) -> set[str]:
        """Return the set of all detected name strings."""
        return {e.text for e in self.names}

    @classmethod
    def empty(cls) -> "EntityRegistry":
        """Create an empty registry (when NER is skipped)."""
        return cls()

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "names": [
                {"text": e.text, "entity_type": e.entity_type, "handling": e.handling, "frequency": e.frequency}
                for e in self.names
            ],
            "unknown_terms": [
                {"text": e.text, "entity_type": e.entity_type, "handling": e.handling, "frequency": e.frequency}
                for e in self.unknown_terms
            ],
            "entity_frequencies": self.entity_frequencies,
        }


# ── NER system prompt ────────────────────────────────────────────────────

NER_SYSTEM_PROMPT = """\
You are an expert at analyzing Japanese Splatoon 3 video transcripts.

Your task: identify PLAYER NAMES, CHANNEL NAMES, and UNKNOWN GAME TERMS
in the transcript below.

KNOWN GLOSSARY TERMS (already handled — do NOT include these):
{known_terms_sample}

INSTRUCTIONS:
1. **Player/Channel Names**: Names of players or YouTube channels mentioned
   in the transcript. These are often in katakana, hiragana, or mixed scripts.
   - Default handling: "preserve" (keep original Japanese form)
   - Chinese gaming communities typically keep JP player names as-is
     (e.g. よっしぃ stays よっしぃ, not transliterated to 约西)

2. **Unknown Game Terms**: Splatoon-related terms NOT in the glossary above.
   - These might be community abbreviations, meta terms, or slang
   - Chinese Splatoon community jargon patterns: 对面=1v1, 打开=retake,
     大招=special, 涂地=inking — these are ALREADY known
   - Only flag terms that genuinely appear game-related but aren't in the glossary

Return the results via the submit_entities tool."""


# ── NER function ─────────────────────────────────────────────────────────


def prescan_entities(
    segments: list[TranscriptSegment],
    known_glossary_terms: set[str],
    model: str | None = None,
) -> EntityRegistry:
    """Run NER pre-scan on the full transcript to detect names and unknown terms.

    Args:
        segments: All transcript segments from ASR.
        known_glossary_terms: Set of JP terms already in the glossary.
        model: LLM model to use (defaults to config.NER_MODEL).

    Returns:
        EntityRegistry with detected names and unknown terms.
    """
    if len(segments) < _MIN_SEGMENTS:
        logger.info("Skipping NER pre-scan: only %d segments (minimum %d)", len(segments), _MIN_SEGMENTS)
        return EntityRegistry.empty()

    model = model or config.NER_MODEL

    # Build full transcript text (no timestamps, just text).
    transcript_text = "\n".join(seg.text for seg in segments)

    # Sample of known terms for the prompt (cap at 100 to save tokens).
    known_sample = sorted(known_glossary_terms)[:100]
    known_terms_str = ", ".join(known_sample) if known_sample else "(none)"

    system = NER_SYSTEM_PROMPT.format(known_terms_sample=known_terms_str)
    user_msg = f"Analyze this Splatoon 3 transcript for names and unknown terms:\n\n{transcript_text}"

    # Count term frequencies in transcript.
    term_freq: dict[str, int] = {}
    full_text = " ".join(seg.text for seg in segments)

    try:
        result = _call_ner(system, user_msg, model)
    except Exception:
        logger.exception("NER pre-scan failed, continuing without NER")
        return EntityRegistry.empty()

    # Build registry from structured output.
    registry = EntityRegistry()

    for name_model in result.names:
        freq = full_text.count(name_model.text) if name_model.text else 0
        entity = DetectedEntity(
            text=name_model.text,
            entity_type=name_model.entity_type,
            handling=name_model.handling,
            frequency=freq,
        )
        registry.names.append(entity)
        if name_model.text:
            registry.entity_frequencies[name_model.text] = freq

    for term_model in result.unknown_terms:
        # Skip if it's actually a known glossary term.
        if term_model.text in known_glossary_terms:
            continue
        freq = full_text.count(term_model.text) if term_model.text else 0
        entity = DetectedEntity(
            text=term_model.text,
            entity_type=term_model.entity_type,
            handling=term_model.handling,
            frequency=freq,
        )
        registry.unknown_terms.append(entity)
        if term_model.text:
            registry.entity_frequencies[term_model.text] = freq

    logger.info(
        "NER pre-scan: found %d names, %d unknown terms",
        len(registry.names), len(registry.unknown_terms),
    )
    return registry


def _call_ner(system: str, user_msg: str, model: str) -> NERResultModel:
    """Call Anthropic API for NER with structured output via tool use."""
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    tool = {
        "name": "submit_entities",
        "description": "Submit detected entities from the transcript.",
        "input_schema": NERResultModel.model_json_schema(),
    }

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        tools=[tool],
        tool_choice={"type": "tool", "name": "submit_entities"},
        messages=[{"role": "user", "content": user_msg}],
    )

    for block in response.content:
        if block.type == "tool_use":
            return NERResultModel.model_validate(block.input)

    raise RuntimeError("No tool_use block in NER response")
