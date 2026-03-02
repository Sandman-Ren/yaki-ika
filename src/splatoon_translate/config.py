"""Centralized configuration: paths, model defaults, env var loading."""

from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()

# ── Paths ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parents[1]
DATA_DIR = PROJECT_ROOT / "data"
GLOSSARY_DIR = DATA_DIR / "glossary"
JARGON_DIR = DATA_DIR / "jargon"
CORRECTIONS_DIR = DATA_DIR / "corrections"
CONTEXT_DIR = DATA_DIR / "context"
REFERENCES_DIR = DATA_DIR / "references"

DEPS_DIR = WORKSPACE_ROOT / "deps"
SPLAT3_LANG_DIR = DEPS_DIR / "splat3" / "data" / "language"

# ── ASR Defaults ───────────────────────────────────────────────────────────
ASR_MODEL_SIZE = os.getenv("ASR_MODEL_SIZE", "large-v3-turbo")
ASR_DEVICE = os.getenv("ASR_DEVICE", "cuda")
ASR_COMPUTE_TYPE = os.getenv("ASR_COMPUTE_TYPE", "float16")
ASR_LANGUAGE = "ja"
ASR_BEAM_SIZE = 1  # lowest hallucination rate per research

# ── Translation Defaults ──────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
TRANSLATION_MODEL = os.getenv("TRANSLATION_MODEL", "claude-sonnet-4-20250514")
TRANSLATION_PROVIDER = os.getenv("TRANSLATION_PROVIDER", "anthropic")
TARGET_LANGUAGE = os.getenv("TARGET_LANGUAGE", "zh-CN")
TRANSLATION_MEMORY_SIZE = int(os.getenv("TRANSLATION_MEMORY_SIZE", "20"))

# ── Quality Scoring ──────────────────────────────────────────────────────
QUALITY_FLAG_THRESHOLD = float(os.getenv("QUALITY_FLAG_THRESHOLD", "0.6"))

# ── Target Language Configs ───────────────────────────────────────────────
# Maps target language codes to display names and Leanny localization file names.
LANGUAGE_CONFIGS = {
    "en": {
        "name": "English",
        "leanny_file": "USen.json",
        "max_chars_per_line": 42,
        "font": "Arial",
    },
    "zh-CN": {
        "name": "Simplified Chinese",
        "leanny_file": "CNzh.json",
        "max_chars_per_line": 22,
        "font": "Microsoft YaHei",
    },
    "zh-TW": {
        "name": "Traditional Chinese",
        "leanny_file": "TWzh.json",
        "max_chars_per_line": 22,
        "font": "Microsoft JhengHei",
    },
}

# ── Subtitle Defaults ─────────────────────────────────────────────────────
MAX_LINES = 2


def get_lang_config(lang: str | None = None) -> dict:
    """Get configuration for a target language."""
    lang = lang or TARGET_LANGUAGE
    return LANGUAGE_CONFIGS.get(lang, LANGUAGE_CONFIGS["zh-CN"])


def get_subtitle_style(lang: str | None = None) -> str:
    """Get FFmpeg ASS subtitle style for a target language."""
    cfg = get_lang_config(lang)
    return (
        f"FontName={cfg['font']},FontSize=24,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "BackColour=&HA0000000,BorderStyle=1,"
        "Outline=2,Shadow=1,Alignment=2,MarginV=40"
    )
