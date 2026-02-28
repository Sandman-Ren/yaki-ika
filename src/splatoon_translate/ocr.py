"""Video subtitle OCR extraction using PaddleOCR.

Standalone module — not imported by the main pipeline.
Requires the [ocr] optional dependency group: uv sync --extra ocr
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class OcrSubtitle:
    index: int
    start: float  # seconds
    end: float
    text: str
    confidence: float


def _init_ocr(lang: str = "ch", use_gpu: bool = True):
    """Initialize PaddleOCR engine."""
    from paddleocr import PaddleOCR

    return PaddleOCR(
        lang=lang,
        use_angle_cls=True,
        use_gpu=use_gpu,
        show_log=False,
    )


def _crop_frame(frame: np.ndarray, crop_region: tuple[float, float, float, float]) -> np.ndarray:
    """Crop a frame to the specified region (x%, y%, w%, h%)."""
    h, w = frame.shape[:2]
    x_pct, y_pct, w_pct, h_pct = crop_region
    x1 = int(w * x_pct)
    y1 = int(h * y_pct)
    x2 = int(w * (x_pct + w_pct))
    y2 = int(h * (y_pct + h_pct))
    return frame[y1:y2, x1:x2]


def _frames_similar(frame_a: np.ndarray, frame_b: np.ndarray, threshold: float = 0.98) -> bool:
    """Check if two cropped frames are near-identical using normalized pixel difference."""
    if frame_a.shape != frame_b.shape:
        return False
    diff = cv2.absdiff(frame_a, frame_b)
    similarity = 1.0 - (np.mean(diff) / 255.0)
    return similarity >= threshold


def _run_ocr(ocr_engine, frame: np.ndarray, conf_threshold: float) -> tuple[str, float]:
    """Run OCR on a single frame crop. Returns (text, avg_confidence)."""
    results = ocr_engine.ocr(frame, cls=True)
    if not results or not results[0]:
        return "", 0.0

    lines = []
    confidences = []
    for line in results[0]:
        text = line[1][0]
        conf = line[1][1]
        if conf >= conf_threshold:
            lines.append(text)
            confidences.append(conf)

    if not lines:
        return "", 0.0

    return "".join(lines), sum(confidences) / len(confidences)


def _texts_similar(a: str, b: str, threshold: float) -> bool:
    """Check if two OCR text strings are similar enough to be the same subtitle."""
    if not a or not b:
        return False
    return SequenceMatcher(None, a, b).ratio() >= threshold


def extract_subtitles(
    video_path: Path,
    *,
    lang: str = "ch",
    crop_region: tuple[float, float, float, float] = (0.0, 0.75, 1.0, 0.25),
    sample_interval: float = 0.5,
    conf_threshold: float = 0.75,
    sim_threshold: float = 0.85,
    use_gpu: bool = True,
) -> list[OcrSubtitle]:
    """Extract burned-in subtitles from a video using OCR.

    Args:
        video_path: Path to the video file.
        lang: PaddleOCR language code ('ch' for simplified, 'chinese_cht' for traditional).
        crop_region: Region to crop as (x%, y%, w%, h%) — defaults to bottom 25%.
        sample_interval: Seconds between sampled frames.
        conf_threshold: Minimum OCR confidence to accept a text line.
        sim_threshold: SequenceMatcher ratio to group consecutive frames as one subtitle.
        use_gpu: Whether to use GPU acceleration.

    Returns:
        List of OcrSubtitle with deduplicated text and timing.
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    logger.info("Initializing PaddleOCR (lang=%s, gpu=%s)", lang, use_gpu)
    ocr_engine = _init_ocr(lang=lang, use_gpu=use_gpu)

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    frame_step = int(fps * sample_interval)

    logger.info(
        "Video: %.1fs, %.0f fps, sampling every %.1fs (%d frame step)",
        duration, fps, sample_interval, frame_step,
    )

    # Phase 1: Sample frames and run OCR
    raw_entries: list[tuple[float, str, float]] = []  # (timestamp, text, confidence)
    prev_crop = None
    frame_idx = 0

    while True:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            break

        timestamp = frame_idx / fps
        crop = _crop_frame(frame, crop_region)

        # Skip OCR if frame is near-identical to previous
        if prev_crop is not None and _frames_similar(prev_crop, crop):
            frame_idx += frame_step
            continue

        prev_crop = crop.copy()
        text, conf = _run_ocr(ocr_engine, crop, conf_threshold)

        if text.strip():
            raw_entries.append((timestamp, text.strip(), conf))
            logger.debug("%.1fs: %s (conf=%.2f)", timestamp, text.strip(), conf)

        frame_idx += frame_step

    cap.release()
    logger.info("OCR pass complete: %d raw text entries from %d frames", len(raw_entries), frame_idx // frame_step)

    if not raw_entries:
        return []

    # Phase 2: Group consecutive similar texts into subtitle segments
    subtitles: list[OcrSubtitle] = []
    group_start = raw_entries[0][0]
    group_text = raw_entries[0][1]
    group_confs = [raw_entries[0][2]]

    for i in range(1, len(raw_entries)):
        ts, text, conf = raw_entries[i]
        if _texts_similar(group_text, text, sim_threshold):
            # Extend current group — keep the longest text variant
            group_confs.append(conf)
            if len(text) > len(group_text):
                group_text = text
        else:
            # Finalize previous group
            subtitles.append(OcrSubtitle(
                index=len(subtitles) + 1,
                start=group_start,
                end=raw_entries[i - 1][0] + sample_interval,
                text=group_text,
                confidence=sum(group_confs) / len(group_confs),
            ))
            group_start = ts
            group_text = text
            group_confs = [conf]

    # Finalize last group
    subtitles.append(OcrSubtitle(
        index=len(subtitles) + 1,
        start=group_start,
        end=raw_entries[-1][0] + sample_interval,
        text=group_text,
        confidence=sum(group_confs) / len(group_confs),
    ))

    logger.info("Deduplicated to %d subtitle segments", len(subtitles))
    return subtitles


def _format_srt_timestamp(seconds: float) -> str:
    """Convert float seconds to SRT timestamp HH:MM:SS,mmm."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def subtitles_to_srt(subs: list[OcrSubtitle], path: Path) -> Path:
    """Write OCR subtitles as an SRT file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for sub in subs:
            start = _format_srt_timestamp(sub.start)
            end = _format_srt_timestamp(sub.end)
            f.write(f"{sub.index}\n{start} --> {end}\n{sub.text}\n\n")
    logger.info("Wrote SRT: %s (%d entries)", path, len(subs))
    return path


def subtitles_to_json(subs: list[OcrSubtitle], path: Path) -> Path:
    """Write OCR subtitles as a JSON file."""
    import json

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "segments": [
            {
                "index": sub.index,
                "start": round(sub.start, 3),
                "end": round(sub.end, 3),
                "text": sub.text,
                "confidence": round(sub.confidence, 4),
            }
            for sub in subs
        ]
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info("Wrote JSON: %s (%d entries)", path, len(subs))
    return path
