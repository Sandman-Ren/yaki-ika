"""LLM-based translation with structured output, translation memory, and game world context."""

import json
import logging
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel
from tqdm import tqdm

from . import config
from .transcribe import TranscriptSegment

logger = logging.getLogger(__name__)


# ── Pydantic models for structured output ─────────────────────────────────


class TranslatedSegmentOutput(BaseModel):
    """A single translated segment returned by the LLM."""
    id: int
    translation: str


class TranslationBatchOutput(BaseModel):
    """Batch of translated segments returned by the LLM."""
    segments: list[TranslatedSegmentOutput]


# ── Translation Memory ────────────────────────────────────────────────────


class TranslationMemory:
    """Sliding window of recent translated pairs for cross-batch consistency.

    Provides the last N translated pairs as prompt context so the LLM can
    maintain consistent naming and style across batch boundaries.
    """

    def __init__(self, window_size: int = 5):
        self._window_size = window_size
        self._pairs: list[tuple[str, str]] = []  # (source, translation)

    def add(self, source: str, translation: str) -> None:
        """Record a translated pair."""
        self._pairs.append((source, translation))
        if len(self._pairs) > self._window_size:
            self._pairs = self._pairs[-self._window_size:]

    def add_batch(self, segments: list["TranslatedSegment"]) -> None:
        """Record all segments from a completed batch."""
        for seg in segments:
            self.add(seg.original, seg.translated)

    def format_for_prompt(self) -> str:
        """Format recent pairs as a prompt section, or empty string if none."""
        if not self._pairs:
            return ""
        lines = []
        for source, translation in self._pairs:
            lines.append(f"  JP: {source}")
            lines.append(f"  →  {translation}")
        return (
            "RECENT TRANSLATIONS (for consistency — use the same names and terms):\n"
            + "\n".join(lines)
        )


# ── Prompt templates ──────────────────────────────────────────────────────


SYSTEM_PROMPT = """\
You are an expert Splatoon 3 subtitle translator (Japanese to {target_language}).
You have deep knowledge of Splatoon 3 gameplay, competitive terminology,
and localization conventions.

{game_context_section}
{glossary_section}
{ambiguous_terms_section}
{memory_section}

SUBTITLE RULES:
- Maximum {max_chars} characters per line, 2 lines maximum per subtitle
- Each segment includes its display duration — use this to gauge how much text viewers can read
- Convey the COMPLETE meaning within the character budget — condense and rephrase naturally, but NEVER truncate or drop clauses
- Omit filler words and redundant politeness markers (えーと, まあ, ですね, etc.)
- Preserve the speaker's tone and energy level — excited speech should feel excited
{language_specific_rules}

TRANSLATION RULES:
- If a glossary term appears in the source, you MUST use the specified translation
- Adapt informal Japanese naturally to natural {target_language}
- For ambiguous passages, ALWAYS favor the gaming/Splatoon context interpretation
- Keep weapon names, ability names, and stage names in their official {target_language} localized form
- Weapon class names differ between JP and EN: スピナー=Splatling, シェルター=Brella, ワイパー=Splatana, マニューバー=Dualies
- 確N or N確 = N-shot kill (e.g. 確1 = one-shot kill, 3確 = three-shot kill)
- Preserve exclamation energy: ナイス!=Nice!, やばい=context-dependent (amazing/terrible), 来た!=Let's go!

Return ONLY the JSON object with translated segments. Do not add commentary or notes."""

LANGUAGE_RULES = {
    "en": (
        "- Use contractions (don't, won't, it's) for natural speech\n"
        "- Prefer active voice for brevity\n"
        "- Use established English Splatoon community terms (splat, ink, turf)"
    ),
    "zh-CN": (
        "- 使用自然口语化的简体中文\n"
        "- 保持游戏社区常用的表达方式（如「大招」而非「特殊武器」）\n"
        "- Use simplified Chinese characters only\n"
        "- 武器、场地、模式名使用官方中文翻译"
    ),
    "zh-TW": (
        "- 使用自然口語化的繁體中文\n"
        "- 保持遊戲社群常用的表達方式\n"
        "- Use traditional Chinese characters only\n"
        "- 武器、場地、模式名使用官方中文翻譯"
    ),
}

GLOSSARY_TEMPLATE = """\
GLOSSARY (MANDATORY — use these translations exactly):
| Japanese | {target_language} |
|----------|---------|
{rows}"""

GAME_CONTEXT_TEMPLATE = """\
GAME CONTEXT:
{overview}
Key modes: Turf War (casual 4v4 inking), Anarchy Battle (competitive ranked with Splat Zones/Tower Control/Rainmaker/Clam Blitz), Salmon Run (4-player PvE co-op), Splatfest (team events).
In this game, players get "splatted" (not killed) and "respawn". The action of covering ground is "inking" or "painting"."""

AMBIGUOUS_TERMS_TEMPLATE = """\
DISAMBIGUATION (these terms have Splatoon-specific meanings):
{terms}"""


# ── Data class (unchanged interface) ──────────────────────────────────────


@dataclass
class TranslatedSegment:
    """A translated subtitle segment."""
    index: int
    start: float
    end: float
    original: str
    translated: str


# ── Prompt builders ───────────────────────────────────────────────────────


def _load_game_context() -> dict | None:
    """Load game world context from data/context/game_world_context.json."""
    ctx_path = config.CONTEXT_DIR / "game_world_context.json"
    if not ctx_path.exists():
        return None
    with open(ctx_path, encoding="utf-8") as f:
        return json.load(f)


def _build_game_context_section() -> str:
    """Build a compact game context section for the system prompt."""
    ctx = _load_game_context()
    if not ctx:
        return ""
    return GAME_CONTEXT_TEMPLATE.format(overview=ctx.get("game_overview", ""))


def _build_ambiguous_terms_section(target_lang: str) -> str:
    """Build disambiguation section from game context for ambiguous terms."""
    ctx = _load_game_context()
    if not ctx:
        return ""
    ambiguous = ctx.get("translation_tone_guide", {}).get("ambiguous_terms", {})
    if not ambiguous:
        return ""
    lines = []
    for term, explanation in ambiguous.items():
        lines.append(f"- {term}: {explanation}")
    return AMBIGUOUS_TERMS_TEMPLATE.format(terms="\n".join(lines))


def _build_glossary_section(matched_glossary: list[dict], target_language: str = "Simplified Chinese") -> str:
    """Format matched glossary entries into a markdown table for the prompt."""
    if not matched_glossary:
        return ""
    rows = []
    for e in matched_glossary:
        target = e.get("target", e.get("en", ""))
        row = f"| {e['jp']} | {target} |"
        rows.append(row)
    return GLOSSARY_TEMPLATE.format(rows="\n".join(rows), target_language=target_language)


def _build_system_prompt(
    target_language: str,
    max_chars: int,
    lang_rules: str,
    glossary_section: str,
    game_context_section: str,
    ambiguous_terms_section: str,
    memory: TranslationMemory,
) -> str:
    """Build the complete system prompt with current translation memory."""
    return SYSTEM_PROMPT.format(
        glossary_section=glossary_section,
        game_context_section=game_context_section,
        ambiguous_terms_section=ambiguous_terms_section,
        memory_section=memory.format_for_prompt(),
        target_language=target_language,
        max_chars=max_chars,
        language_specific_rules=lang_rules,
    )


def _build_user_message_json(segments: list[TranscriptSegment], start_index: int) -> str:
    """Format transcript segments as a JSON array for the LLM."""
    items = []
    for i, seg in enumerate(segments, start_index):
        items.append({
            "id": i,
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "duration_seconds": round(seg.end - seg.start, 2),
            "source": seg.text,
        })
    payload = json.dumps(items, ensure_ascii=False, indent=2)
    return f"Translate the following Japanese transcript segments:\n\n{payload}"


# ── LLM callers ───────────────────────────────────────────────────────────

MAX_RETRIES = 2


def _call_anthropic(system: str, user_msg: str, model: str) -> TranslationBatchOutput:
    """Call the Anthropic API with structured output via tool use.

    Uses forced tool_choice to guarantee structured JSON output.
    This works on all Claude model versions.
    """
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    tool = {
        "name": "submit_translations",
        "description": "Submit the batch of translated subtitle segments.",
        "input_schema": TranslationBatchOutput.model_json_schema(),
    }

    for attempt in range(1 + MAX_RETRIES):
        response = client.messages.create(
            model=model,
            max_tokens=8192,
            system=system,
            tools=[tool],
            tool_choice={"type": "tool", "name": "submit_translations"},
            messages=[{"role": "user", "content": user_msg}],
        )

        # Check for max_tokens truncation
        if response.stop_reason == "max_tokens":
            if attempt < MAX_RETRIES:
                logger.warning("Anthropic response truncated (max_tokens), retrying (%d/%d)", attempt + 1, MAX_RETRIES)
                continue
            logger.error("Anthropic response truncated after %d retries", MAX_RETRIES)

        # Extract the tool_use block and parse as Pydantic model
        for block in response.content:
            if block.type == "tool_use":
                return TranslationBatchOutput.model_validate(block.input)

        raise RuntimeError("No tool_use block in Anthropic response")


def _call_openai(system: str, user_msg: str, model: str) -> TranslationBatchOutput:
    """Call the OpenAI API with structured output."""
    import openai

    client = openai.OpenAI(api_key=config.OPENAI_API_KEY)

    for attempt in range(1 + MAX_RETRIES):
        response = client.chat.completions.parse(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=8192,
            response_format=TranslationBatchOutput,
        )

        choice = response.choices[0]

        # Check for length truncation
        if choice.finish_reason == "length":
            if attempt < MAX_RETRIES:
                logger.warning("OpenAI response truncated (length), retrying (%d/%d)", attempt + 1, MAX_RETRIES)
                continue
            logger.error("OpenAI response truncated after %d retries", MAX_RETRIES)

        if choice.message.parsed:
            return choice.message.parsed

        # Refusal or unparseable
        if choice.message.refusal:
            logger.error("OpenAI refused to translate: %s", choice.message.refusal)
        raise RuntimeError(f"OpenAI returned unparseable response: {choice.message.content}")


# ── Validation ────────────────────────────────────────────────────────────


def _validate_and_retry(
    batch_output: TranslationBatchOutput,
    segments: list[TranscriptSegment],
    start_index: int,
    system: str,
    model: str,
    provider: str,
) -> TranslationBatchOutput:
    """Validate batch output and retry missing/suspicious segments individually."""
    translations = {s.id: s.translation for s in batch_output.segments}
    expected_ids = set(range(start_index, start_index + len(segments)))
    returned_ids = set(translations.keys())

    missing_ids = expected_ids - returned_ids
    suspicious_ids = set()

    # Flag suspiciously short translations
    for i, seg in enumerate(segments, start_index):
        if i in translations and len(seg.text) > 10:
            ratio = len(translations[i]) / len(seg.text)
            if ratio < 0.20:
                suspicious_ids.add(i)
                logger.warning(
                    "Suspiciously short translation for segment %d: '%s' → '%s' (%.0f%% of source length)",
                    i, seg.text, translations[i], ratio * 100,
                )

    retry_ids = missing_ids | suspicious_ids
    if not retry_ids:
        return batch_output

    if missing_ids:
        logger.warning("Missing segments from batch response: %s", sorted(missing_ids))

    # Retry each problem segment individually
    seg_by_index = {i: seg for i, seg in enumerate(segments, start_index)}
    for seg_id in sorted(retry_ids):
        seg = seg_by_index[seg_id]
        logger.info("Retrying segment %d individually: '%s'", seg_id, seg.text[:50])

        user_msg = _build_user_message_json([seg], seg_id)
        try:
            if provider == "anthropic":
                retry_result = _call_anthropic(system, user_msg, model)
            else:
                retry_result = _call_openai(system, user_msg, model)

            if retry_result.segments:
                translations[seg_id] = retry_result.segments[0].translation
        except Exception:
            logger.exception("Retry failed for segment %d", seg_id)

    # Rebuild the batch output with retried translations
    final_segments = []
    for s in batch_output.segments:
        if s.id in translations:
            final_segments.append(TranslatedSegmentOutput(id=s.id, translation=translations[s.id]))

    # Add any that were entirely missing from the original
    existing_ids = {s.id for s in final_segments}
    for seg_id in sorted(missing_ids):
        if seg_id in translations and seg_id not in existing_ids:
            final_segments.append(TranslatedSegmentOutput(id=seg_id, translation=translations[seg_id]))

    final_segments.sort(key=lambda s: s.id)
    return TranslationBatchOutput(segments=final_segments)


# ── Main entry point ──────────────────────────────────────────────────────


def translate_segments(
    segments: list[TranscriptSegment],
    matched_glossary: list[dict],
    model: str | None = None,
    provider: str | None = None,
    target_lang: str | None = None,
    batch_size: int = 40,
) -> list[TranslatedSegment]:
    """Translate transcript segments using an LLM with glossary injection.

    Segments are batched to avoid desync on long transcripts.
    Uses structured output (Pydantic) for reliable parsing and
    translation memory for cross-batch consistency.
    """
    model = model or config.TRANSLATION_MODEL
    provider = provider or config.TRANSLATION_PROVIDER
    target_lang = target_lang or config.TARGET_LANGUAGE

    lang_cfg = config.get_lang_config(target_lang)
    target_language = lang_cfg["name"]
    max_chars = lang_cfg["max_chars_per_line"]
    lang_rules = LANGUAGE_RULES.get(target_lang, "")

    glossary_section = _build_glossary_section(matched_glossary, target_language)
    game_context_section = _build_game_context_section()
    ambiguous_terms_section = _build_ambiguous_terms_section(target_lang)

    memory = TranslationMemory(window_size=5)
    all_results: list[TranslatedSegment] = []
    num_batches = math.ceil(len(segments) / batch_size)

    batch_iter = tqdm(
        range(0, len(segments), batch_size),
        total=num_batches,
        desc="Translating",
        unit="batch",
        leave=False,
    )
    for batch_start in batch_iter:
        batch = segments[batch_start : batch_start + batch_size]
        batch_iter.set_postfix(segments=f"{batch_start + len(batch)}/{len(segments)}")
        start_index = batch_start + 1

        # Build system prompt with current memory state
        system = _build_system_prompt(
            target_language=target_language,
            max_chars=max_chars,
            lang_rules=lang_rules,
            glossary_section=glossary_section,
            game_context_section=game_context_section,
            ambiguous_terms_section=ambiguous_terms_section,
            memory=memory,
        )

        user_msg = _build_user_message_json(batch, start_index)

        if provider == "anthropic":
            batch_output = _call_anthropic(system, user_msg, model)
        elif provider == "openai":
            batch_output = _call_openai(system, user_msg, model)
        else:
            raise ValueError(f"Unknown provider: {provider}")

        # Validate and retry missing/suspicious segments
        batch_output = _validate_and_retry(
            batch_output, batch, start_index, system, model, provider,
        )

        # Convert to TranslatedSegment objects
        translations = {s.id: s.translation for s in batch_output.segments}
        batch_results = []
        missing_count = 0
        for i, seg in enumerate(batch, start_index):
            translated = translations.get(i, seg.text)
            if i not in translations:
                missing_count += 1
            batch_results.append(TranslatedSegment(
                index=i,
                start=seg.start,
                end=seg.end,
                original=seg.text,
                translated=translated,
            ))

        if missing_count > 0:
            print(
                f"  [warn] {missing_count}/{len(batch)} segments missing after retry, using original JP as fallback",
                file=sys.stderr,
            )

        all_results.extend(batch_results)

        # Update translation memory for next batch
        memory.add_batch(batch_results)

    return all_results
