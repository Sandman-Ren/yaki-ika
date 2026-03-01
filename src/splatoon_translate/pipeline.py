"""Pipeline orchestrator and CLI entry point."""

import argparse
import json
import shutil
import time
from pathlib import Path

from tqdm import tqdm

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
    burn: bool = False,
    soft_subs: bool = False,
    burn_subtitle: str = "translated",
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
        burn: Burn subtitles into video (default: off).
        soft_subs: Add as toggleable subtitle track.
        burn_subtitle: Which subtitle to burn/embed: "translated" (default),
            "ja", "bilingual", or a file path to an SRT.
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

    embed = burn or soft_subs
    total_steps = 7 if embed else 6
    step = 0

    progress = tqdm(total=total_steps, desc="Pipeline", unit="step", bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} steps [{elapsed}<{remaining}]")

    # ── Step 1: Download or locate video ───────────────────────────────────
    step += 1
    source_path = Path(source)
    if source_path.exists():
        video_path = source_path
        stem = video_path.stem
        progress.set_description(f"[{step}/{total_steps}] Using local file")
        # Copy to output dir so output is self-contained
        video_in_output = output_dir / video_path.name
        if video_path.resolve() != video_in_output.resolve():
            shutil.copy2(video_path, video_in_output)
    else:
        progress.set_description(f"[{step}/{total_steps}] Downloading video")
        video_path = download_video(source, output_dir)
        stem = video_path.stem
    progress.update(1)

    # ── Step 2: Extract audio ──────────────────────────────────────────────
    step += 1
    progress.set_description(f"[{step}/{total_steps}] Extracting audio")
    t0 = time.time()
    audio_path = extract_audio(video_path, output_dir)
    progress.update(1)

    # ── Step 3: Transcribe ─────────────────────────────────────────────────
    step += 1
    progress.set_description(f"[{step}/{total_steps}] Transcribing")
    t0 = time.time()
    segments = transcribe(audio_path, model_size=model_size)
    progress.update(1)

    # Save JP transcript.
    jp_srt = output_dir / f"{stem}.ja.srt"
    transcript_to_srt(segments, jp_srt)

    # ── Step 4: Term extraction + glossary matching ────────────────────────
    step += 1
    progress.set_description(f"[{step}/{total_steps}] Matching glossary terms")
    glossary = load_glossary(target_lang=target_lang)
    matched = match_glossary(segments, glossary, target_lang=target_lang)
    progress.update(1)

    if keep_intermediates:
        terms_path = output_dir / f"{stem}.terms.{lang_suffix}.json"
        with open(terms_path, "w", encoding="utf-8") as f:
            json.dump(matched, f, ensure_ascii=False, indent=2)

    # ── Step 5: Translate ──────────────────────────────────────────────────
    step += 1
    progress.set_description(f"[{step}/{total_steps}] Translating to {lang_name}")
    t0 = time.time()
    translated = translate_segments(
        segments, matched,
        model=translation_model,
        provider=translation_provider,
        target_lang=target_lang,
    )
    progress.update(1)

    # ── Step 6: Generate SRT ───────────────────────────────────────────────
    step += 1
    progress.set_description(f"[{step}/{total_steps}] Generating subtitles")
    translated_srt = output_dir / f"{stem}.{lang_suffix}.srt"
    segments_to_srt(translated, translated_srt, target_lang=target_lang)

    bilingual_srt = output_dir / f"{stem}.bilingual.{lang_suffix}.srt"
    segments_to_bilingual_srt(translated, bilingual_srt)
    progress.update(1)

    # ── Step 7 (optional): Embed subtitles ─────────────────────────────────
    final_output = translated_srt

    if embed:
        # Resolve which SRT to embed based on burn_subtitle option.
        if burn_subtitle == "translated":
            embed_srt = translated_srt
            sub_suffix = ""
        elif burn_subtitle == "ja":
            embed_srt = jp_srt
            sub_suffix = ".ja"
        elif burn_subtitle == "bilingual":
            embed_srt = bilingual_srt
            sub_suffix = f".bilingual.{lang_suffix}"
        else:
            embed_srt = Path(burn_subtitle)
            sub_suffix = f".{embed_srt.stem}"

        output_mp4 = output_dir / f"{stem}.subtitled{sub_suffix}.mp4"
        step += 1

        if burn:
            progress.set_description(f"[{step}/{total_steps}] Burning subtitles")
            burn_subtitles(video_path, embed_srt, output_mp4, target_lang=target_lang, gpu=gpu)
        else:
            progress.set_description(f"[{step}/{total_steps}] Adding soft subtitles")
            add_soft_subtitles(video_path, embed_srt, output_mp4)
        final_output = output_mp4
        progress.update(1)

    progress.set_description("Done")
    progress.close()

    # ── Cleanup ────────────────────────────────────────────────────────────
    if not keep_intermediates:
        audio_path.unlink(missing_ok=True)

    # Print summary.
    print(f"\nOutput: {final_output}")
    print(f"  Japanese transcript: {jp_srt.name}")
    print(f"  Translated subtitles: {translated_srt.name}")
    print(f"  Bilingual subtitles: {bilingual_srt.name}")
    if embed:
        print(f"  Video: {final_output.name}")
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
        "--burn",
        action="store_true",
        help="Burn subtitles into the output video",
    )
    parser.add_argument(
        "--burn-subtitle",
        default="translated",
        metavar="TYPE",
        help="Which subtitle to burn: translated (default), ja, bilingual, or a path to an SRT file",
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
        burn=args.burn and not args.soft_subs,
        soft_subs=args.soft_subs,
        burn_subtitle=args.burn_subtitle,
        gpu=not args.cpu,
        keep_intermediates=not args.no_intermediates,
    )


if __name__ == "__main__":
    main()
