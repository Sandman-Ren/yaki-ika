#!/usr/bin/env python3
"""Standalone script to build the glossary from Leanny's data + community jargon."""

import sys
from pathlib import Path

# Add src to path so we can import the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from splatoon_translate.glossary import build_glossary


def main():
    lang = sys.argv[1] if len(sys.argv) > 1 else "zh-CN"
    entries = build_glossary(target_lang=lang)
    categories = {}
    for e in entries:
        cat = e["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print(f"Built glossary ({lang}): {len(entries)} entries")
    print("By category:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
