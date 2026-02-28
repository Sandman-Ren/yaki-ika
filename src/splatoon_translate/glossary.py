"""Glossary building and loading from Leanny's datamined JSONs + community jargon."""

import json
import re
from pathlib import Path

from .config import SPLAT3_LANG_DIR, GLOSSARY_DIR, JARGON_DIR, get_lang_config

# Categories containing gameplay-relevant terms worth including in the glossary.
PRIORITY_CATEGORIES = [
    "CommonMsg/Weapon/WeaponName_Main",
    "CommonMsg/Weapon/WeaponName_Sub",
    "CommonMsg/Weapon/WeaponName_Special",
    "CommonMsg/Weapon/WeaponTypeName",
    "CommonMsg/VS/VSStageName",
    "CommonMsg/Coop/CoopStageName",
    "CommonMsg/Coop/CoopEnemy",
    "CommonMsg/Coop/CoopGrade",
    "CommonMsg/Coop/CoopSkinName",
    "CommonMsg/Gear/GearPowerName",
    "CommonMsg/Gear/GearBrandName",
    "CommonMsg/Gear/GearName_Head",
    "CommonMsg/Gear/GearName_Clothes",
    "CommonMsg/Gear/GearName_Shoes",
    "CommonMsg/MatchMode",
    "CommonMsg/Glossary",
    "CommonMsg/Badge/BadgeMsg",
    "CommonMsg/MusicName",
]

# Patterns to strip from values before storing.
_STRIP_PATTERNS = [
    re.compile(r"\[size=\d+%\]"),
    re.compile(r'\[ruby="[^"]*"\]'),
    re.compile(r"\[/ruby\]"),
]

# Entries matching these patterns are placeholders / non-translatable.
_SKIP_PATTERNS = [
    re.compile(r"\[group="),
]


def _clean(text: str) -> str:
    """Strip formatting tags ([size=...], [ruby=...]) from a localization string."""
    for pat in _STRIP_PATTERNS:
        text = pat.sub("", text)
    return text.strip()


def _should_skip(jp: str, target: str) -> bool:
    """Return True if the entry is a placeholder or not useful for translation."""
    if not jp or not target or jp == "-" or target == "-":
        return True
    for pat in _SKIP_PATTERNS:
        if pat.search(jp) or pat.search(target):
            return True
    # Skip if target is identical to JP (untranslated entry).
    if jp == target:
        return True
    return False


def build_glossary(
    target_lang: str = "zh-CN",
    jpja_path: Path | None = None,
    target_path: Path | None = None,
    jargon_path: Path | None = None,
    output_dir: Path | None = None,
    categories: list[str] | None = None,
) -> list[dict]:
    """Build the glossary from Leanny's datamined JSONs and community jargon.

    Args:
        target_lang: Target language code ("zh-CN", "en", "zh-TW").

    Returns the glossary as a list of {jp, target, category} dicts.
    Also writes glossary.json and glossary_lookup.json to output_dir.
    """
    lang_cfg = get_lang_config(target_lang)
    jpja_path = jpja_path or SPLAT3_LANG_DIR / "JPja.json"
    target_path = target_path or SPLAT3_LANG_DIR / lang_cfg["leanny_file"]
    jargon_path = jargon_path or JARGON_DIR / f"community_jargon.{target_lang}.json"
    # Fall back to base jargon file if language-specific one doesn't exist.
    if not jargon_path.exists():
        jargon_path = JARGON_DIR / "community_jargon.json"
    output_dir = output_dir or GLOSSARY_DIR
    categories = categories or PRIORITY_CATEGORIES

    with open(jpja_path, encoding="utf-8") as f:
        jpja = json.load(f)
    with open(target_path, encoding="utf-8") as f:
        target_data = json.load(f)

    # Align entries by shared keys within each priority category.
    seen: set[tuple[str, str]] = set()
    entries: list[dict] = []

    for cat in categories:
        jp_cat = jpja.get(cat, {})
        tgt_cat = target_data.get(cat, {})
        for key in jp_cat:
            if key not in tgt_cat:
                continue
            jp_val = _clean(jp_cat[key])
            tgt_val = _clean(tgt_cat[key])
            if _should_skip(jp_val, tgt_val):
                continue
            pair = (jp_val, tgt_val)
            if pair in seen:
                continue
            seen.add(pair)
            entries.append({
                "jp": jp_val,
                "target": tgt_val,
                "category": cat.split("/")[-1],
            })

    # Merge community jargon (takes precedence on conflicts).
    if jargon_path.exists():
        with open(jargon_path, encoding="utf-8") as f:
            jargon = json.load(f)
        jargon_jp_set = {e["jp"] for e in jargon}
        entries = [e for e in entries if e["jp"] not in jargon_jp_set]
        # Normalize jargon entries: "en"/"target" key -> "target".
        for j in jargon:
            if "en" in j and "target" not in j:
                j["target"] = j.pop("en")
            if "target" not in j:
                continue
            entries.append(j)

    # Write outputs.
    output_dir.mkdir(parents=True, exist_ok=True)

    glossary_path = output_dir / f"glossary.{target_lang}.json"
    with open(glossary_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    # Lookup dict keyed by JP term for O(1) matching.
    lookup = {e["jp"]: e for e in entries}
    lookup_path = output_dir / f"glossary_lookup.{target_lang}.json"
    with open(lookup_path, "w", encoding="utf-8") as f:
        json.dump(lookup, f, ensure_ascii=False, indent=2)

    return entries


def load_glossary(
    target_lang: str = "zh-CN",
    glossary_path: Path | None = None,
) -> dict[str, dict]:
    """Load the pre-built glossary lookup dict (keyed by JP term).

    Returns an empty dict if the glossary file doesn't exist (the pipeline
    will still work, just without game-term injection).
    """
    glossary_path = glossary_path or GLOSSARY_DIR / f"glossary_lookup.{target_lang}.json"
    if not glossary_path.exists():
        print(f"  Warning: glossary not found at {glossary_path}")
        print(f"           Run 'python scripts/build_glossary.py {target_lang}' to build it.")
        return {}
    with open(glossary_path, encoding="utf-8") as f:
        return json.load(f)
