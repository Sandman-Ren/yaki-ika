"""Term extraction via MeCab and glossary matching."""

from pathlib import Path

from .glossary import load_glossary
from .transcribe import TranscriptSegment


def _get_tagger():
    """Lazily create and cache a MeCab tagger."""
    import MeCab
    return MeCab.Tagger()


def extract_tokens(text: str) -> list[str]:
    """Tokenize Japanese text with MeCab. Returns list of surface forms."""
    tagger = _get_tagger()
    node = tagger.parseToNode(text)
    tokens = []
    while node:
        surface = node.surface
        if surface:
            tokens.append(surface)
        node = node.next
    return tokens


def match_glossary(
    segments: list[TranscriptSegment],
    glossary: dict[str, dict] | None = None,
    glossary_path: Path | None = None,
    target_lang: str = "zh-CN",
) -> list[dict]:
    """Match transcript terms against the glossary.

    Uses three strategies:
    1. Exact token match (MeCab surface forms)
    2. N-gram match (2-3 adjacent tokens joined)
    3. Substring match (glossary keys >3 chars found in segment text)

    Returns deduplicated list of matched glossary entries.
    """
    if glossary is None:
        glossary = load_glossary(target_lang=target_lang, glossary_path=glossary_path)

    matched: dict[str, dict] = {}  # keyed by jp term to deduplicate
    full_text = " ".join(seg.text for seg in segments)

    for seg in segments:
        tokens = extract_tokens(seg.text)

        # Strategy 1: exact token match.
        for token in tokens:
            if token in glossary:
                matched[token] = glossary[token]

        # Strategy 2: n-gram match (2-gram, 3-gram).
        for n in (2, 3):
            for i in range(len(tokens) - n + 1):
                ngram = "".join(tokens[i : i + n])
                if ngram in glossary:
                    matched[ngram] = glossary[ngram]

    # Strategy 3: substring match for longer glossary keys.
    for jp_term, entry in glossary.items():
        if len(jp_term) > 3 and jp_term not in matched and jp_term in full_text:
            matched[jp_term] = entry

    return list(matched.values())
