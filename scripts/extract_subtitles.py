#!/usr/bin/env python3
"""Standalone script to extract burned-in subtitles from a video using OCR.

Requires the [ocr] optional dependency group:
    uv sync --extra ocr

Usage:
    uv run --extra ocr python scripts/extract_subtitles.py <video_or_url> [options]

Examples:
    # Extract from a local video file
    uv run --extra ocr python scripts/extract_subtitles.py video.mp4 -o ./output

    # Extract from a video URL (Bilibili, YouTube, etc.)
    uv run --extra ocr python scripts/extract_subtitles.py "https://example.com/video/xxx" -o ./output

    # Traditional Chinese with custom crop region
    uv run --extra ocr python scripts/extract_subtitles.py video.mp4 -l cht --crop 0,80,100,20
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path so we can import the package.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from splatoon_translate.ocr import extract_subtitles, subtitles_to_srt, subtitles_to_json

logger = logging.getLogger(__name__)

LANG_MAP = {"ch": "ch", "cht": "chinese_cht"}


def _parse_crop(crop_str: str) -> tuple[float, float, float, float]:
    """Parse crop string 'x%,y%,w%,h%' into floats."""
    parts = [float(p) for p in crop_str.split(",")]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("Crop must be 4 comma-separated values: x%,y%,w%,h%")
    return (parts[0] / 100, parts[1] / 100, parts[2] / 100, parts[3] / 100)


def _is_url(source: str) -> bool:
    return source.startswith("http://") or source.startswith("https://")


def main():
    parser = argparse.ArgumentParser(
        description="Extract burned-in subtitles from video using OCR",
    )
    parser.add_argument("source", help="Video file path or URL")
    parser.add_argument("-o", "--output-dir", default="./output", help="Output directory (default: ./output)")
    parser.add_argument("-l", "--lang", choices=["ch", "cht"], default="ch", help="OCR language (default: ch)")
    parser.add_argument("--crop", default="0,75,100,25", help="Crop region as 'x%%,y%%,w%%,h%%' (default: 0,75,100,25)")
    parser.add_argument("--sample-interval", type=float, default=0.5, help="Frame sample interval in seconds (default: 0.5)")
    parser.add_argument("--conf-threshold", type=float, default=0.75, help="Min OCR confidence (default: 0.75)")
    parser.add_argument("--format", choices=["srt", "json", "both"], default="both", help="Output format (default: both)")
    parser.add_argument("--cpu", action="store_true", help="Force CPU mode (no GPU)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Resolve source: download if URL
    source = args.source
    if _is_url(source):
        logger.info("Downloading video from %s", source)
        from splatoon_translate.download import download_video
        video_path = download_video(source, output_dir)
        logger.info("Downloaded to %s", video_path)
    else:
        video_path = Path(source)
        if not video_path.exists():
            print(f"Error: Video file not found: {video_path}", file=sys.stderr)
            sys.exit(1)

    crop_region = _parse_crop(args.crop)
    ocr_lang = LANG_MAP[args.lang]

    print(f"Extracting subtitles from: {video_path}")
    print(f"  Language: {args.lang}, Crop: {args.crop}, Interval: {args.sample_interval}s")

    subs = extract_subtitles(
        video_path,
        lang=ocr_lang,
        crop_region=crop_region,
        sample_interval=args.sample_interval,
        conf_threshold=args.conf_threshold,
        use_gpu=not args.cpu,
    )

    if not subs:
        print("No subtitles found.")
        sys.exit(0)

    print(f"Found {len(subs)} subtitle segments")

    stem = video_path.stem
    if args.format in ("srt", "both"):
        srt_path = subtitles_to_srt(subs, output_dir / f"{stem}.ocr.srt")
        print(f"  SRT: {srt_path}")

    if args.format in ("json", "both"):
        json_path = subtitles_to_json(subs, output_dir / f"{stem}.ocr.json")
        print(f"  JSON: {json_path}")

    # Print preview
    print(f"\nPreview (first 5 segments):")
    for sub in subs[:5]:
        print(f"  [{sub.start:.1f}s - {sub.end:.1f}s] ({sub.confidence:.0%}) {sub.text}")
    if len(subs) > 5:
        print(f"  ... and {len(subs) - 5} more")


if __name__ == "__main__":
    main()
