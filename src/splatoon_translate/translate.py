"""LLM-based translation with RAG glossary injection."""

from dataclasses import dataclass
import re

from . import config
from .transcribe import TranscriptSegment

SYSTEM_PROMPT = """\
You are an expert Splatoon 3 subtitle translator (Japanese to {target_language}).
You have deep knowledge of Splatoon 3 gameplay, competitive terminology,
and localization conventions.

{glossary_section}

SUBTITLE RULES:
- Maximum {max_chars} characters per line, 2 lines maximum per subtitle
- Prioritize brevity and readability over literal accuracy
- Omit filler words and redundant politeness markers
- Preserve the speaker's tone and register
{language_specific_rules}

TRANSLATION RULES:
- If a glossary term appears in the source, you MUST use the specified translation
- Adapt informal Japanese naturally to natural {target_language}
- For ambiguous passages, favor the gaming/Splatoon context interpretation
- Keep weapon names, ability names, and stage names in their official {target_language} localized form

OUTPUT FORMAT:
Return ONLY the translated segments in this exact format, one per segment:
[N] TRANSLATED TEXT

Where N is the segment number. Do not include timestamps or Japanese text.
Do not add commentary or notes."""

LANGUAGE_RULES = {
    "en": "- Use contractions (don't, won't, it's) for natural speech\n- Prefer active voice for brevity",
    "zh-CN": "- 使用自然口语化的简体中文\n- 保持游戏社区常用的表达方式\n- Use simplified Chinese characters only",
    "zh-TW": "- 使用自然口語化的繁體中文\n- 保持遊戲社群常用的表達方式\n- Use traditional Chinese characters only",
}

GLOSSARY_TEMPLATE = """\
GLOSSARY (MANDATORY — use these translations exactly):
| Japanese | {target_language} |
|----------|---------|
{rows}"""


@dataclass
class TranslatedSegment:
    """A translated subtitle segment."""
    index: int
    start: float
    end: float
    original: str
    translated: str


def _build_glossary_section(matched_glossary: list[dict], target_language: str = "Simplified Chinese") -> str:
    """Format matched glossary entries into a markdown table for the prompt."""
    if not matched_glossary:
        return ""
    rows = "\n".join(
        f"| {e['jp']} | {e.get('target', e.get('en', ''))} |"
        for e in matched_glossary
    )
    return GLOSSARY_TEMPLATE.format(rows=rows, target_language=target_language)


def _build_user_message(segments: list[TranscriptSegment]) -> str:
    """Format transcript segments into the numbered format for the LLM."""
    return _build_user_message_indexed(segments, 1)


def _build_user_message_indexed(segments: list[TranscriptSegment], start_index: int) -> str:
    """Format transcript segments with explicit index numbering."""
    lines = []
    for i, seg in enumerate(segments, start_index):
        lines.append(f"[{i}] {seg.text}")
    return "Translate the following Japanese transcript segments to English:\n\n" + "\n".join(lines)


def _parse_response(
    response_text: str,
    segments: list[TranscriptSegment],
    start_index: int = 1,
) -> list[TranslatedSegment]:
    """Parse the LLM response back into TranslatedSegment objects."""
    # Match lines like [1] translated text
    pattern = re.compile(r"\[(\d+)\]\s*(.+)")
    translations: dict[int, str] = {}

    for line in response_text.strip().splitlines():
        line = line.strip()
        m = pattern.match(line)
        if m:
            idx = int(m.group(1))
            text = m.group(2).strip()
            translations[idx] = text

    results = []
    for i, seg in enumerate(segments, start_index):
        translated = translations.get(i, seg.text)  # fallback to original if missing
        results.append(TranslatedSegment(
            index=i,
            start=seg.start,
            end=seg.end,
            original=seg.text,
            translated=translated,
        ))
    return results


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
    """
    model = model or config.TRANSLATION_MODEL
    provider = provider or config.TRANSLATION_PROVIDER
    target_lang = target_lang or config.TARGET_LANGUAGE

    lang_cfg = config.get_lang_config(target_lang)
    target_language = lang_cfg["name"]
    max_chars = lang_cfg["max_chars_per_line"]
    lang_rules = LANGUAGE_RULES.get(target_lang, "")

    glossary_section = _build_glossary_section(matched_glossary, target_language)
    system = SYSTEM_PROMPT.format(
        glossary_section=glossary_section,
        target_language=target_language,
        max_chars=max_chars,
        language_specific_rules=lang_rules,
    )

    all_results: list[TranslatedSegment] = []

    for batch_start in range(0, len(segments), batch_size):
        batch = segments[batch_start : batch_start + batch_size]
        # Use global indices so numbering is consistent across batches.
        user_msg = _build_user_message_indexed(batch, batch_start + 1)

        if provider == "anthropic":
            response_text = _call_anthropic(system, user_msg, model)
        elif provider == "openai":
            response_text = _call_openai(system, user_msg, model)
        else:
            raise ValueError(f"Unknown provider: {provider}")

        batch_results = _parse_response(response_text, batch, start_index=batch_start + 1)
        all_results.extend(batch_results)

    return all_results


def _call_anthropic(system: str, user_msg: str, model: str) -> str:
    """Call the Anthropic API."""
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text


def _call_openai(system: str, user_msg: str, model: str) -> str:
    """Call the OpenAI API."""
    import openai

    client = openai.OpenAI(api_key=config.OPENAI_API_KEY)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg},
        ],
        max_tokens=8192,
    )
    return response.choices[0].message.content
