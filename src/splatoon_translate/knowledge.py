"""Domain knowledge loader: reads glossary and formats as prompt-ready reference lists."""

import json
import logging
from pathlib import Path

from . import config

logger = logging.getLogger(__name__)

# Domain areas: group raw categories into higher-level prompt sections.
# Each maps to (display_name, [raw_categories]).
DOMAIN_AREAS: list[tuple[str, list[str]]] = [
    ("打工 Salmon Run", [
        "CoopStageName", "CoopEnemy", "CoopGrade", "CoopSkinName", "salmon_run",
    ]),
    ("武器 Weapons", [
        "WeaponName_Main", "WeaponName_Sub", "WeaponName_Special",
        "WeaponTypeName", "weapon_abbrev",
    ]),
    ("场地与模式 Stages & Modes", [
        "VSStageName", "MatchMode", "mode_abbrev",
    ]),
    ("技能 Abilities & Gear Powers", [
        "GearPowerName", "ability_abbrev",
    ]),
    ("策略与报点 Strategy & Callouts", [
        "strategy", "callout",
    ]),
    ("角色与社区 Characters & Community", [
        "character", "slang", "general", "commentary_pattern",
    ]),
    ("游戏术语 In-Game Glossary", [
        "Glossary",
    ]),
]

# Categories where the official translation MUST be used verbatim.
MANDATORY_CATEGORIES: set[str] = {
    "WeaponName_Main", "WeaponName_Sub", "WeaponName_Special", "WeaponTypeName",
    "VSStageName", "CoopStageName", "CoopEnemy", "CoopGrade", "CoopSkinName",
    "GearPowerName", "MatchMode", "character",
    "weapon_abbrev", "ability_abbrev", "mode_abbrev",
}

# Cosmetic categories excluded by default (rarely relevant, saves ~15K tokens).
COSMETIC_CATEGORIES: set[str] = {
    "GearName_Head", "GearName_Clothes", "GearName_Shoes",
    "GearBrandName", "BadgeMsg",
}

KNOWLEDGE_HEADER = """\
SPLATOON 3 REFERENCE DATA
Use these official translations for all game entities.
The source text comes from automatic speech recognition (ASR) which may contain \
transcription errors — misspellings, wrong kanji, dropped characters, split compound words.
Cross-reference against these lists to identify the intended game term even when \
the transcription is imperfect.
"""


def load_domain_knowledge(
    target_lang: str = "zh-CN",
    include_cosmetics: bool = False,
) -> str:
    """Load and format complete Splatoon 3 domain knowledge for the prompt.

    Reads the pre-built glossary array and formats entries as compact markdown
    tables grouped by domain area. Appends game context and disambiguation.

    Args:
        target_lang: Target language code.
        include_cosmetics: Include cosmetic gear categories (adds ~15K tokens).

    Returns:
        Formatted domain knowledge string ready for prompt injection.
    """
    glossary_path = config.GLOSSARY_DIR / f"glossary.{target_lang}.json"
    if not glossary_path.exists():
        logger.warning("Glossary not found at %s — domain knowledge will be empty", glossary_path)
        return ""

    with open(glossary_path, encoding="utf-8") as f:
        entries: list[dict] = json.load(f)

    # Group entries by category.
    by_category: dict[str, list[dict]] = {}
    for e in entries:
        cat = e.get("category", "general")
        if not include_cosmetics and cat in COSMETIC_CATEGORIES:
            continue
        by_category.setdefault(cat, []).append(e)

    lang_cfg = config.get_lang_config(target_lang)
    target_language = lang_cfg["name"]

    # Build sections by domain area.
    sections: list[str] = [KNOWLEDGE_HEADER]
    total_entries = 0

    for area_name, area_cats in DOMAIN_AREAS:
        area_entries: list[dict] = []
        for cat in area_cats:
            area_entries.extend(by_category.pop(cat, []))
        if not area_entries:
            continue

        rows = []
        for e in area_entries:
            target = e.get("target", e.get("en", ""))
            rows.append(f"| {e['jp']} | {target} |")

        total_entries += len(area_entries)
        sections.append(
            f"## {area_name}\n"
            f"| 日本語 | {target_language} |\n"
            f"|--------|-------------------|\n"
            + "\n".join(rows)
        )

    # Append any remaining categories not covered by domain areas.
    for cat, cat_entries in by_category.items():
        if not cat_entries:
            continue
        rows = []
        for e in cat_entries:
            target = e.get("target", e.get("en", ""))
            rows.append(f"| {e['jp']} | {target} |")
        total_entries += len(cat_entries)
        sections.append(
            f"## {cat}\n"
            f"| 日本語 | {target_language} |\n"
            f"|--------|-------------------|\n"
            + "\n".join(rows)
        )

    # Append game context and disambiguation.
    game_context = load_game_context()
    if game_context:
        sections.append(game_context)

    logger.info("Domain knowledge: %d entries across reference tables", total_entries)
    return "\n\n".join(sections)


def load_game_context() -> str:
    """Load game_world_context.json and format as a prompt section."""
    ctx_path = config.CONTEXT_DIR / "game_world_context.json"
    if not ctx_path.exists():
        return ""

    with open(ctx_path, encoding="utf-8") as f:
        ctx = json.load(f)

    parts: list[str] = []

    # Game overview.
    overview = ctx.get("game_overview", "")
    if overview:
        parts.append(
            f"GAME CONTEXT:\n{overview}\n"
            "Key modes: Turf War (casual 4v4 inking), Anarchy Battle "
            "(competitive ranked with Splat Zones/Tower Control/Rainmaker/Clam Blitz), "
            "Salmon Run (4-player PvE co-op), Splatfest (team events).\n"
            'In this game, players get "splatted" (not killed) and "respawn". '
            'The action of covering ground is "inking" or "painting".'
        )

    # Disambiguation terms.
    ambiguous = ctx.get("translation_tone_guide", {}).get("ambiguous_terms", {})
    if ambiguous:
        lines = ["DISAMBIGUATION (these terms have Splatoon-specific meanings):"]
        for term, explanation in ambiguous.items():
            lines.append(f"- {term}: {explanation}")
        parts.append("\n".join(lines))

    return "\n\n".join(parts)
