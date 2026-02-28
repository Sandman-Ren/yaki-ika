#!/usr/bin/env python3
"""CLI for managing the reference translation store.

Usage:
    uv run python scripts/gather_references.py add <source> --ref-lang zh-CN [options]
    uv run python scripts/gather_references.py list [--lang zh-CN] [--platform PLATFORM]
    uv run python scripts/gather_references.py search <query> [--lang zh-CN]

The 'add' command supports multiple source types:
  - Local OCR JSON file (from extract_subtitles.py)
  - Local SRT file
  - Video URL (downloads, tries soft-sub extraction, falls back to OCR)
"""

import argparse
import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

# Add src to path so we can import the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from splatoon_translate.references import (
    create_collection_from_ocr_json,
    create_collection_from_srt,
    list_references,
    load_reference,
    save_reference,
    search_references,
)

logger = logging.getLogger(__name__)

# Map URL domains to platform names for auto-detection.
_PLATFORM_DOMAINS = {
    "bilibili.com": "bilibili",
    "b23.tv": "bilibili",
    "youtube.com": "youtube",
    "youtu.be": "youtube",
    "nicovideo.jp": "niconico",
}


def _is_url(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://")


def _detect_platform(url: str) -> str:
    """Auto-detect platform from URL domain."""
    from urllib.parse import urlparse
    hostname = urlparse(url).hostname or ""
    for domain, platform in _PLATFORM_DOMAINS.items():
        if hostname == domain or hostname.endswith("." + domain):
            return platform
    return "unknown"


def _try_extract_soft_subs(url: str, output_dir: Path, lang: str) -> Path | None:
    """Try to download soft subtitles via yt-dlp. Returns SRT path or None."""
    output_template = str(output_dir / "%(title)s.%(ext)s")
    result = subprocess.run(
        [
            "yt-dlp",
            "--write-subs",
            "--sub-lang", lang,
            "--sub-format", "srt",
            "--skip-download",
            "-o", output_template,
            url,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        return None

    srt_files = list(output_dir.glob(f"*.{lang}.srt"))
    return srt_files[0] if srt_files else None


def _get_video_title(url: str) -> str:
    """Get video title via yt-dlp."""
    result = subprocess.run(
        ["yt-dlp", "--print", "title", "--skip-download", url],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return ""


def cmd_add(args):
    """Handle the 'add' subcommand."""
    source = args.source
    ref_lang = args.ref_lang
    original_url = args.original_url or ""
    platform = args.platform
    if not platform and _is_url(source):
        platform = _detect_platform(source)
    elif not platform:
        platform = "local"
    video_title = args.title or ""

    if _is_url(source):
        # Source is a URL — try soft subs first, then OCR fallback
        if not video_title:
            video_title = _get_video_title(source)
            print(f"Video title: {video_title}")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Map ref_lang to yt-dlp subtitle language codes
            sub_lang_map = {"zh-CN": "zh-Hans", "zh-TW": "zh-Hant", "zh": "zh"}
            sub_lang = sub_lang_map.get(ref_lang, ref_lang)

            print(f"Trying soft subtitle extraction ({sub_lang})...")
            srt_path = _try_extract_soft_subs(source, tmpdir, sub_lang)

            if srt_path:
                print(f"Found soft subtitles: {srt_path.name}")
                collection = create_collection_from_srt(
                    srt_path,
                    source_url=source,
                    original_video_url=original_url,
                    reference_language=ref_lang,
                    platform=platform,
                    source_type="soft_sub",
                    video_title=video_title,
                )
            else:
                print("No soft subtitles found. Falling back to OCR...")
                from splatoon_translate.download import download_video
                from splatoon_translate.ocr import extract_subtitles, subtitles_to_json

                video_path = download_video(source, tmpdir)
                print(f"Downloaded: {video_path.name}")

                subs = extract_subtitles(
                    video_path,
                    lang="ch" if ref_lang in ("zh-CN", "zh") else "chinese_cht",
                    use_gpu=not args.cpu,
                )

                if not subs:
                    print("No subtitles found via OCR.")
                    sys.exit(1)

                # Save OCR JSON to temp, then create collection from it
                ocr_json = subtitles_to_json(subs, tmpdir / "ocr_output.json")
                collection = create_collection_from_ocr_json(
                    ocr_json,
                    source_url=source,
                    original_video_url=original_url,
                    reference_language=ref_lang,
                    platform=platform,
                    video_title=video_title,
                )

    else:
        # Source is a local file
        source_path = Path(source)
        if not source_path.exists():
            print(f"Error: File not found: {source_path}", file=sys.stderr)
            sys.exit(1)

        if source_path.suffix == ".json":
            collection = create_collection_from_ocr_json(
                source_path,
                source_url="",
                original_video_url=original_url,
                reference_language=ref_lang,
                platform=platform,
                video_title=video_title or source_path.stem,
            )
        elif source_path.suffix == ".srt":
            collection = create_collection_from_srt(
                source_path,
                source_url="",
                original_video_url=original_url,
                reference_language=ref_lang,
                platform=platform,
                source_type="srt_import" if platform != "self" else "reviewed_output",
                video_title=video_title or source_path.stem,
            )
        else:
            print(f"Error: Unsupported file format: {source_path.suffix}", file=sys.stderr)
            print("  Supported: .json (OCR output), .srt (subtitle file)", file=sys.stderr)
            sys.exit(1)

    filepath = save_reference(collection)
    print(f"\nSaved reference: {collection.reference_id}")
    print(f"  File: {filepath}")
    print(f"  Segments: {len(collection.segments)}")
    print(f"  Language: {ref_lang}")
    print(f"  Platform: {platform}")


def cmd_list(args):
    """Handle the 'list' subcommand."""
    refs = list_references(language=args.lang, platform=args.platform)

    if not refs:
        print("No references found.")
        return

    print(f"{'ID':<10} {'Lang':<8} {'Platform':<12} {'Segments':<10} {'Title'}")
    print("-" * 80)
    for r in refs:
        ref_id = r.get("reference_id", "?")
        lang = r.get("language", "?")
        platform = r.get("platform", "?")
        count = r.get("segment_count", 0)
        title = r.get("video_title", "")[:40]
        print(f"{ref_id:<10} {lang:<8} {platform:<12} {count:<10} {title}")


def cmd_search(args):
    """Handle the 'search' subcommand."""
    results = search_references(args.query, language=args.lang)

    if not results:
        print(f"No references matching '{args.query}'.")
        return

    print(f"Found {len(results)} result(s):")
    for r in results:
        ref_id = r.get("reference_id", "?")
        title = r.get("video_title", "")
        url = r.get("source_url", "")
        print(f"  [{ref_id}] {title}")
        if url:
            print(f"           {url}")


def main():
    parser = argparse.ArgumentParser(
        description="Manage reference translation store",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # add
    add_parser = subparsers.add_parser("add", help="Add a reference translation")
    add_parser.add_argument("source", help="Video URL, OCR JSON file, or SRT file")
    add_parser.add_argument("--ref-lang", default="zh-CN", help="Reference language (default: zh-CN)")
    add_parser.add_argument("--original-url", help="URL of the original JP video")
    add_parser.add_argument("--platform", help="Source platform (auto-detected from URL, or 'local' for files)")
    add_parser.add_argument("--title", help="Video title (auto-detected from URL)")
    add_parser.add_argument("--cpu", action="store_true", help="Force CPU mode for OCR")
    add_parser.set_defaults(func=cmd_add)

    # list
    list_parser = subparsers.add_parser("list", help="List reference translations")
    list_parser.add_argument("--lang", help="Filter by language")
    list_parser.add_argument("--platform", help="Filter by platform")
    list_parser.set_defaults(func=cmd_list)

    # search
    search_parser = subparsers.add_parser("search", help="Search reference translations")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--lang", help="Filter by language")
    search_parser.set_defaults(func=cmd_search)

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    args.func(args)


if __name__ == "__main__":
    main()
