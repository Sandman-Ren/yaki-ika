"""Pipeline orchestrator and CLI entry point."""

import argparse
import json
import time
from pathlib import Path

from . import config
from .config import get_lang_config
from .download import download_video
from .audio import extract_audio
from .transcribe import transcribe, TranscriptSegment
from .glossary import load_glossary
from .terms import match_glossary
from .translate import translate_segments, TranslatedSegment
from .subtitle import segments_to_srt, segments_to_bilingual_srt, transcript_to_srt
from .embed import burn_subtitles, add_soft_subtitles


def run_pipeline(
    source: str,
    output_dir: Path,
    target_lang: str | None = None,
    model_size: str | None = None,
    translation_model: str | None = None,
    translation_provider: str | None = None,
    burn: bool = True,
    soft_subs: bool = False,
    gpu: bool = True,
    keep_intermediates: bool = True,
) -> Path:
    """Run the full transcribe -> translate -> subtitle pipeline.

    Args:
        source: URL or local video file path.
        output_dir: Directory for all outputs.
        target_lang: Target language code ("zh-CN", "en", "zh-TW").
        model_size: Whisper model size (default: large-v3-turbo).
        translation_model: LLM model name.
        translation_provider: "anthropic" or "openai".
        burn: Burn subtitles into video.
        soft_subs: Add as toggleable subtitle track.
        gpu: Use GPU encoding for FFmpeg.
        keep_intermediates: Keep intermediate files (audio, transcripts, etc.).

    Returns:
        Path to the final output file.
    """
    target_lang = target_lang or config.TARGET_LANGUAGE
    lang_cfg = get_lang_config(target_lang)
    lang_name = lang_cfg["name"]
    # Short language code for filenames (e.g. "zh-CN" -> "zh", "en" -> "en").
    lang_suffix = target_lang.split("-")[0]

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # ── Step 1: Download or locate video ───────────────────────────────────
    source_path = Path(source)
    if source_path.exists():
        video_path = source_path
        stem = video_path.stem
        print(f"[1/7] Using local file: {video_path}")
    else:
        print(f"[1/7] Downloading video...")
        video_path = download_video(source, output_dir)
        stem = video_path.stem
        print(f"       -> {video_path.name}")

    # ── Step 2: Extract audio ──────────────────────────────────────────────
    print(f"[2/7] Extracting audio...")
    t0 = time.time()
    audio_path = extract_audio(video_path, output_dir)
    print(f"       -> {audio_path.name} ({time.time() - t0:.1f}s)")

    # ── Step 3: Transcribe ─────────────────────────────────────────────────
    print(f"[3/7] Transcribing Japanese audio...")
    t0 = time.time()
    segments = transcribe(audio_path, model_size=model_size)
    print(f"       -> {len(segments)} segments ({time.time() - t0:.1f}s)")

    # Save JP transcript.
    jp_srt = output_dir / f"{stem}.ja.srt"
    transcript_to_srt(segments, jp_srt)

    # ── Step 4: Term extraction + glossary matching ────────────────────────
    print(f"[4/7] Matching glossary terms ({lang_name})...")
    glossary = load_glossary(target_lang=target_lang)
    matched = match_glossary(segments, glossary, target_lang=target_lang)
    print(f"       -> {len(matched)} terms matched")

    if keep_intermediates:
        terms_path = output_dir / f"{stem}.terms.{lang_suffix}.json"
        with open(terms_path, "w", encoding="utf-8") as f:
            json.dump(matched, f, ensure_ascii=False, indent=2)

    # ── Step 5: Translate ──────────────────────────────────────────────────
    print(f"[5/7] Translating to {lang_name}...")
    t0 = time.time()
    translated = translate_segments(
        segments, matched,
        model=translation_model,
        provider=translation_provider,
        target_lang=target_lang,
    )
    print(f"       -> {len(translated)} segments translated ({time.time() - t0:.1f}s)")

    # ── Step 6: Generate SRT ───────────────────────────────────────────────
    print(f"[6/7] Generating subtitles...")
    translated_srt = output_dir / f"{stem}.{lang_suffix}.srt"
    segments_to_srt(translated, translated_srt, target_lang=target_lang)

    bilingual_srt = output_dir / f"{stem}.bilingual.{lang_suffix}.srt"
    segments_to_bilingual_srt(translated, bilingual_srt)
    print(f"       -> {translated_srt.name}, {bilingual_srt.name}")

    # ── Step 7: Embed subtitles ────────────────────────────────────────────
    final_output = translated_srt  # default: just the SRT

    if burn:
        print(f"[7/7] Burning subtitles into video...")
        t0 = time.time()
        output_mp4 = output_dir / f"{stem}.subtitled.mp4"
        burn_subtitles(video_path, translated_srt, output_mp4, target_lang=target_lang, gpu=gpu)
        final_output = output_mp4
        print(f"       -> {output_mp4.name} ({time.time() - t0:.1f}s)")
    elif soft_subs:
        print(f"[7/7] Adding soft subtitles...")
        output_mp4 = output_dir / f"{stem}.subtitled.mp4"
        add_soft_subtitles(video_path, translated_srt, output_mp4)
        final_output = output_mp4
        print(f"       -> {output_mp4.name}")
    else:
        print(f"[7/7] Skipping video embedding (SRT only)")

    # ── Cleanup ────────────────────────────────────────────────────────────
    if not keep_intermediates:
        audio_path.unlink(missing_ok=True)

    print(f"\nDone! Output: {final_output}")
    return final_output


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Splatoon 3 JP auto-subtitle translation pipeline",
    )
    parser.add_argument(
        "source",
        help="YouTube URL or local video file path",
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=Path,
        default=Path("./output"),
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "-l", "--lang",
        default=None,
        choices=list(config.LANGUAGE_CONFIGS.keys()),
        help=f"Target language (default: {config.TARGET_LANGUAGE})",
    )
    parser.add_argument(
        "--model-size",
        default=None,
        help=f"Whisper model size (default: {config.ASR_MODEL_SIZE})",
    )
    parser.add_argument(
        "--translation-model",
        default=None,
        help=f"LLM model name (default: {config.TRANSLATION_MODEL})",
    )
    parser.add_argument(
        "--translation-provider",
        choices=["anthropic", "openai"],
        default=None,
        help=f"LLM provider (default: {config.TRANSLATION_PROVIDER})",
    )
    parser.add_argument(
        "--no-burn",
        action="store_true",
        help="Skip burning subtitles into video (SRT only)",
    )
    parser.add_argument(
        "--soft-subs",
        action="store_true",
        help="Add as toggleable subtitle track instead of burn-in",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Use CPU for FFmpeg encoding (no GPU)",
    )
    parser.add_argument(
        "--no-intermediates",
        action="store_true",
        help="Don't keep intermediate files",
    )

    args = parser.parse_args()

    run_pipeline(
        source=args.source,
        output_dir=args.output_dir,
        target_lang=args.lang,
        model_size=args.model_size,
        translation_model=args.translation_model,
        translation_provider=args.translation_provider,
        burn=not args.no_burn and not args.soft_subs,
        soft_subs=args.soft_subs,
        gpu=not args.cpu,
        keep_intermediates=not args.no_intermediates,
    )


if __name__ == "__main__":
    main()
