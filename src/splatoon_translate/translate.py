"""LLM-based translation with structured output, translation memory, and domain knowledge."""

import json
import logging
import re
import sys
from dataclasses import dataclass

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
    entities: list[dict[str, str]] | None = None


class TranslationBatchOutput(BaseModel):
    """Batch of translated segments returned by the LLM."""
    segments: list[TranslatedSegmentOutput]


# ── Translation Memory ────────────────────────────────────────────────────


class TranslationMemory:
    """Sliding window of recent translated pairs for cross-batch consistency.

    Provides the last N translated pairs as prompt context so the LLM can
    maintain consistent naming and style across batch boundaries.
    """

    def __init__(self, window_size: int | None = None):
        self._window_size = window_size if window_size is not None else config.TRANSLATION_MEMORY_SIZE
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


# ── Entity Ledger ────────────────────────────────────────────────────────


class EntityLedger:
    """Tracks first-seen translations for entities across ALL batches.

    Unlike the glossary (pre-defined), the ledger captures LLM choices
    for terms not in the glossary — ensuring consistency across the
    entire video. Uses first-write-wins semantics.
    """

    def __init__(self) -> None:
        self._entries: dict[str, str] = {}  # {jp_term: chosen_translation}

    def record(self, jp_term: str, translation: str) -> None:
        """Record a translation if not already seen (first-write-wins)."""
        if jp_term and translation and jp_term not in self._entries:
            self._entries[jp_term] = translation

    def extract_from_batch(self, batch_output: "TranslationBatchOutput") -> None:
        """Extract entities from batch results and record them.

        Reads the optional `entities` field from each translated segment.
        """
        for seg in batch_output.segments:
            if not seg.entities:
                continue
            for entity in seg.entities:
                jp = entity.get("jp", entity.get("source", ""))
                tr = entity.get("translation", entity.get("target", ""))
                if jp and tr:
                    self.record(jp, tr)

    def format_for_prompt(self) -> str:
        """Format ledger as a prompt section, or empty string if empty."""
        if not self._entries:
            return ""
        lines = ["ESTABLISHED TRANSLATIONS (use consistently across all segments):"]
        for jp, tr in self._entries.items():
            lines.append(f"  {jp} → {tr}")
        return "\n".join(lines)


# ── Prompt templates ──────────────────────────────────────────────────────


SYSTEM_PROMPT = """\
You are an expert Splatoon 3 subtitle translator (Japanese to {target_language}).

{domain_knowledge}
{memory_section}
{entity_ledger_section}
{reference_section}

SUBTITLE RULES:
- Maximum {max_chars} characters per line, 2 lines maximum per subtitle
- Each segment includes its display duration — use this to gauge how much text viewers can read
- Convey the COMPLETE meaning within the character budget — condense and rephrase naturally
- Omit filler words and redundant politeness markers (えーと, まあ, ですね, etc.)
- Preserve the speaker's tone and energy level
{language_specific_rules}

TRANSLATION RULES:
- Use the OFFICIAL localized names from the reference data for all game entities \
(weapons, stages, bosses, modes, abilities) — NEVER invent translations for known terms
- The source is ASR output and WILL contain transcription errors — use the reference data \
to recognize misspelled/misheard game terms and translate them correctly
- Adapt informal Japanese naturally to natural {target_language}
- For ambiguous passages, ALWAYS favor the gaming/Splatoon context interpretation
- Preserve player names and channel names in their original form (do not transliterate)
- 確N or N確 = N-shot kill (e.g. 確1 = one-shot kill, 3確 = three-shot kill)
- Preserve exclamation energy: ナイス!=Nice!, やばい=context-dependent

- If you encounter player names, channel names, or recurring terms NOT in the reference data, \
include them in the "entities" field as [{{"jp": "term", "translation": "chosen translation"}}]

Return ONLY the JSON object with translated segments."""

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


def _build_system_prompt(
    target_language: str,
    max_chars: int,
    lang_rules: str,
    domain_knowledge: str,
    memory: TranslationMemory,
    entity_ledger: EntityLedger | None = None,
    reference_section: str = "",
) -> str:
    """Build the complete system prompt with domain knowledge and translation memory."""
    return SYSTEM_PROMPT.format(
        domain_knowledge=domain_knowledge,
        memory_section=memory.format_for_prompt(),
        entity_ledger_section=entity_ledger.format_for_prompt() if entity_ledger else "",
        reference_section=reference_section,
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


# ── Reference translation matching ────────────────────────────────────────


def _match_references_to_batch(
    batch_segments: list[TranscriptSegment],
    reference_segments: list,
    max_references: int = 8,
    time_tolerance: float = 2.0,
    min_overlap: float = 0.3,
) -> str:
    """Match reference translations to batch segments by time overlap.

    Returns a formatted prompt section with the best matches.
    """
    if not reference_segments or not batch_segments:
        return ""

    batch_start = batch_segments[0].start - time_tolerance
    batch_end = batch_segments[-1].end + time_tolerance

    # Pre-filter references to those near the batch time window.
    candidate_refs = [
        r for r in reference_segments
        if r.end >= batch_start and r.start <= batch_end
    ]
    if not candidate_refs:
        return ""

    # Find reference segments that overlap with the batch time range.
    matches: list[tuple[float, object, TranscriptSegment]] = []
    for batch_seg in batch_segments:
        seg_start = batch_seg.start
        seg_end = batch_seg.end
        seg_duration = seg_end - seg_start
        if seg_duration <= 0:
            continue

        for ref_seg in candidate_refs:
            ref_start = ref_seg.start
            ref_end = ref_seg.end
            # Check overlap.
            overlap_start = max(seg_start, ref_start)
            overlap_end = min(seg_end, ref_end)
            overlap = max(0, overlap_end - overlap_start)

            if overlap <= 0 and abs(seg_start - ref_start) > time_tolerance:
                continue

            # Score by overlap ratio relative to segment duration.
            score = overlap / seg_duration if seg_duration > 0 else 0
            # Also boost near-matches (within tolerance but no strict overlap).
            if overlap <= 0:
                time_diff = min(abs(seg_start - ref_start), abs(seg_end - ref_end))
                score = max(0, 1.0 - time_diff / time_tolerance) * 0.5

            if score >= min_overlap or (overlap <= 0 and score > 0):
                matches.append((score, ref_seg, batch_seg))

    if not matches:
        return ""

    # Deduplicate: keep best match per reference segment.
    seen_refs: dict[int, tuple[float, object, TranscriptSegment]] = {}
    for score, ref_seg, batch_seg in matches:
        ref_idx = ref_seg.index
        if ref_idx not in seen_refs or score > seen_refs[ref_idx][0]:
            seen_refs[ref_idx] = (score, ref_seg, batch_seg)

    # Sort by score descending, take top N.
    top_matches = sorted(seen_refs.values(), key=lambda x: -x[0])[:max_references]

    lines = ["REFERENCE TRANSLATIONS (community translations for style guidance — adapt naturally):"]
    for score, ref_seg, batch_seg in top_matches:
        lines.append(f"  JP: {batch_seg.text}")
        lines.append(f"  Reference: {ref_seg.text}")
        lines.append("")

    return "\n".join(lines)


# ── Sentence-aware batching ───────────────────────────────────────────────

# Japanese sentence-ending punctuation.
_SENTENCE_END_RE = re.compile(r"[。！？!?]$")
# Minimum pause gap (seconds) to treat as a sentence boundary.
_PAUSE_GAP_THRESHOLD = 1.0


def _detect_sentence_groups(segments: list[TranscriptSegment]) -> list[list[TranscriptSegment]]:
    """Group consecutive segments into sentence units.

    Uses two signals to detect boundaries:
    1. Japanese sentence-ending punctuation on the previous segment
    2. Pause gap > 1s between consecutive segments

    Returns a list of groups, each group being a list of segments
    that form a logical sentence unit.
    """
    if not segments:
        return []

    groups: list[list[TranscriptSegment]] = []
    current_group: list[TranscriptSegment] = [segments[0]]

    for i in range(1, len(segments)):
        prev = segments[i - 1]
        curr = segments[i]

        # Check for sentence boundary.
        has_sentence_end = bool(_SENTENCE_END_RE.search(prev.text.rstrip()))
        has_pause_gap = (curr.start - prev.end) > _PAUSE_GAP_THRESHOLD

        if has_sentence_end or has_pause_gap:
            groups.append(current_group)
            current_group = [curr]
        else:
            current_group.append(curr)

    if current_group:
        groups.append(current_group)

    return groups


def _build_sentence_aware_batches(
    segments: list[TranscriptSegment],
    batch_size: int,
) -> list[list[TranscriptSegment]]:
    """Pack sentence groups into batches without splitting groups.

    Greedy bin-packing: add groups to the current batch until adding
    the next group would exceed batch_size. If a single group exceeds
    batch_size, it gets its own batch. If a group exceeds 2*batch_size,
    force-split it at the largest internal pause gap.
    """
    groups = _detect_sentence_groups(segments)
    batches: list[list[TranscriptSegment]] = []
    current_batch: list[TranscriptSegment] = []

    for group in groups:
        # Safety: force-split oversized groups.
        if len(group) > 2 * batch_size:
            split_groups = _force_split_group(group, batch_size)
        else:
            split_groups = [group]

        for sub_group in split_groups:
            if current_batch and len(current_batch) + len(sub_group) > batch_size:
                batches.append(current_batch)
                current_batch = []
            current_batch.extend(sub_group)

    if current_batch:
        batches.append(current_batch)

    return batches


def _force_split_group(
    group: list[TranscriptSegment],
    batch_size: int,
) -> list[list[TranscriptSegment]]:
    """Force-split an oversized group at the largest internal pause gaps."""
    if len(group) <= batch_size:
        return [group]

    # Find all internal pause gaps.
    gaps: list[tuple[float, int]] = []
    for i in range(1, len(group)):
        gap = group[i].start - group[i - 1].end
        gaps.append((gap, i))

    # Sort by gap size descending, pick split points.
    gaps.sort(key=lambda x: -x[0])
    num_splits = (len(group) - 1) // batch_size  # how many splits needed
    split_indices = sorted(g[1] for g in gaps[:num_splits])

    raw: list[list[TranscriptSegment]] = []
    prev = 0
    for idx in split_indices:
        raw.append(group[prev:idx])
        prev = idx
    raw.append(group[prev:])

    # Recurse on any sub-groups that are still oversized.
    result: list[list[TranscriptSegment]] = []
    for sub in raw:
        if not sub:
            continue
        if len(sub) > batch_size:
            result.extend(_force_split_group(sub, batch_size))
        else:
            result.append(sub)
    return result


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

    # Rebuild the batch output with retried translations (preserving entities)
    original_entities = {s.id: s.entities for s in batch_output.segments}
    final_segments = []
    for s in batch_output.segments:
        if s.id in translations:
            final_segments.append(TranslatedSegmentOutput(
                id=s.id,
                translation=translations[s.id],
                entities=original_entities.get(s.id),
            ))

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
    domain_knowledge: str,
    model: str | None = None,
    provider: str | None = None,
    target_lang: str | None = None,
    batch_size: int = 40,
    reference_segments: list | None = None,
) -> list[TranslatedSegment]:
    """Translate transcript segments using an LLM with domain knowledge injection.

    Segments are batched using sentence-aware grouping to avoid splitting
    sentences across batches. Uses structured output (Pydantic) for reliable
    parsing, translation memory and entity ledger for cross-batch consistency.
    """
    model = model or config.TRANSLATION_MODEL
    provider = provider or config.TRANSLATION_PROVIDER
    target_lang = target_lang or config.TARGET_LANGUAGE

    lang_cfg = config.get_lang_config(target_lang)
    target_language = lang_cfg["name"]
    max_chars = lang_cfg["max_chars_per_line"]
    lang_rules = LANGUAGE_RULES.get(target_lang, "")

    memory = TranslationMemory()
    entity_ledger = EntityLedger()
    all_results: list[TranslatedSegment] = []
    batches = _build_sentence_aware_batches(segments, batch_size)

    batch_iter = tqdm(
        batches,
        total=len(batches),
        desc="Translating",
        unit="batch",
        leave=False,
    )
    segment_offset = 0
    for batch in batch_iter:
        batch_iter.set_postfix(segments=f"{segment_offset + len(batch)}/{len(segments)}")
        start_index = segment_offset + 1

        # Build reference section for this batch.
        batch_reference_section = ""
        if reference_segments:
            batch_reference_section = _match_references_to_batch(batch, reference_segments)

        # Build system prompt with current memory state
        system = _build_system_prompt(
            target_language=target_language,
            max_chars=max_chars,
            lang_rules=lang_rules,
            domain_knowledge=domain_knowledge,
            memory=memory,
            entity_ledger=entity_ledger,
            reference_section=batch_reference_section,
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

        # Extract entities from LLM output for cross-batch consistency
        entity_ledger.extract_from_batch(batch_output)

        segment_offset += len(batch)

    return all_results
