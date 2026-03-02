"""Content fidelity scoring for translated segments.

Provides automated quality checks after translation:
- Length ratio (source vs. translation)
- Glossary adherence (mandatory terms present in output)
- Entity preservation (NER-detected names preserved)
"""

import logging
from dataclasses import dataclass, field

from . import config
from .translate import TranslatedSegment, EXACT_TRANSLATION_CATEGORIES

logger = logging.getLogger(__name__)

# Language-specific length ratio bounds: (min_ratio, max_ratio).
# ratio = len(translation) / len(source)
_LENGTH_BOUNDS: dict[str, tuple[float, float]] = {
    "zh-CN": (0.10, 2.0),   # Chinese is more concise than Japanese
    "zh-TW": (0.10, 2.0),
    "en": (0.15, 2.5),      # English is typically longer
}
_DEFAULT_LENGTH_BOUNDS = (0.10, 2.5)


@dataclass
class SegmentQualityScore:
    """Quality score for a single translated segment."""
    index: int
    length_ratio: float
    length_flag: bool
    glossary_adherence: float
    missing_glossary_terms: list[str]
    entity_preserved: float
    missing_entities: list[str]
    overall_score: float


@dataclass
class QualityReport:
    """Aggregate quality report for all translated segments."""
    segment_scores: list[SegmentQualityScore] = field(default_factory=list)
    average_score: float = 0.0
    flagged_segments: list[int] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dict."""
        return {
            "average_score": round(self.average_score, 4),
            "flagged_count": len(self.flagged_segments),
            "total_segments": len(self.segment_scores),
            "flagged_segments": self.flagged_segments,
            "summary": self.summary,
            "scores": [
                {
                    "index": s.index,
                    "length_ratio": round(s.length_ratio, 4),
                    "length_flag": s.length_flag,
                    "glossary_adherence": round(s.glossary_adherence, 4),
                    "missing_glossary_terms": s.missing_glossary_terms,
                    "entity_preserved": round(s.entity_preserved, 4),
                    "missing_entities": s.missing_entities,
                    "overall_score": round(s.overall_score, 4),
                }
                for s in self.segment_scores
            ],
        }


def score_translations(
    translated_segments: list[TranslatedSegment],
    matched_glossary: list[dict],
    entity_names: set[str] | None = None,
    target_lang: str | None = None,
) -> QualityReport:
    """Score translated segments for content fidelity.

    Checks:
    1. Length ratio — flag if outside language-specific bounds.
    2. Glossary adherence — for mandatory-category terms in source,
       check if the target translation appears in the output.
    3. Entity preservation — check if NER-detected names in source
       are preserved in the translation.

    Weighted composite: 20% length + 50% glossary + 30% entity.
    """
    target_lang = target_lang or config.TARGET_LANGUAGE
    threshold = config.QUALITY_FLAG_THRESHOLD
    min_ratio, max_ratio = _LENGTH_BOUNDS.get(target_lang, _DEFAULT_LENGTH_BOUNDS)

    # Build lookup: jp_term -> target_translation for mandatory categories.
    mandatory_terms: dict[str, str] = {}
    for entry in matched_glossary:
        cat = entry.get("category", "")
        if cat in EXACT_TRANSLATION_CATEGORIES:
            jp = entry.get("jp", "")
            target = entry.get("target", entry.get("en", ""))
            if jp and target:
                mandatory_terms[jp] = target

    entity_names = entity_names or set()
    scores: list[SegmentQualityScore] = []

    for seg in translated_segments:
        source = seg.original
        translation = seg.translated

        # 1. Length ratio check.
        source_len = len(source.strip())
        trans_len = len(translation.strip())
        if source_len > 0:
            ratio = trans_len / source_len
        else:
            ratio = 1.0
        length_flag = ratio < min_ratio or ratio > max_ratio
        length_score = 0.0 if length_flag else 1.0

        # 2. Glossary adherence.
        applicable_terms: list[str] = []
        missing_glossary: list[str] = []
        for jp_term, target_trans in mandatory_terms.items():
            if jp_term in source:
                applicable_terms.append(jp_term)
                # Check if the target translation appears in the output.
                # Handle terms with slashes (e.g. "开路/突破") — check any part.
                parts = [p.strip() for p in target_trans.split("/")]
                if not any(part in translation for part in parts):
                    missing_glossary.append(jp_term)

        if applicable_terms:
            glossary_score = 1.0 - (len(missing_glossary) / len(applicable_terms))
        else:
            glossary_score = 1.0  # No applicable terms = perfect score.

        # 3. Entity preservation.
        applicable_entities: list[str] = []
        missing_ents: list[str] = []
        for name in entity_names:
            if name in source:
                applicable_entities.append(name)
                if name not in translation:
                    missing_ents.append(name)

        if applicable_entities:
            entity_score = 1.0 - (len(missing_ents) / len(applicable_entities))
        else:
            entity_score = 1.0

        # Weighted composite.
        overall = 0.20 * length_score + 0.50 * glossary_score + 0.30 * entity_score

        scores.append(SegmentQualityScore(
            index=seg.index,
            length_ratio=ratio,
            length_flag=length_flag,
            glossary_adherence=glossary_score,
            missing_glossary_terms=missing_glossary,
            entity_preserved=entity_score,
            missing_entities=missing_ents,
            overall_score=overall,
        ))

    # Build report.
    flagged = [s.index for s in scores if s.overall_score < threshold]
    avg = sum(s.overall_score for s in scores) / len(scores) if scores else 1.0

    summary_parts = [f"Average quality: {avg:.2f}"]
    if flagged:
        summary_parts.append(f"{len(flagged)}/{len(scores)} segments flagged (below {threshold})")
    else:
        summary_parts.append("No segments flagged")

    return QualityReport(
        segment_scores=scores,
        average_score=avg,
        flagged_segments=flagged,
        summary=". ".join(summary_parts),
    )
