"""Reference translation storage — load, save, list, search.

Stores reference translations from any source (community fan-subs, soft
subtitles, reviewed pipeline output, etc.) for comparison and evaluation
against LLM-generated translations.
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .config import REFERENCES_DIR

logger = logging.getLogger(__name__)

INDEX_FILE = REFERENCES_DIR / "index.json"


@dataclass
class ReferenceSegment:
    index: int
    start: float
    end: float
    text: str
    confidence: float = 1.0


@dataclass
class ReferenceCollection:
    metadata: dict
    segments: list[ReferenceSegment]
    reference_id: str = ""

    def __post_init__(self):
        if not self.reference_id:
            self.reference_id = str(uuid.uuid4())[:8]


def _load_index() -> dict:
    """Load the master index file."""
    if not INDEX_FILE.exists():
        INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
        _save_index({"collections": []})
    with open(INDEX_FILE, encoding="utf-8") as f:
        return json.load(f)


def _save_index(index: dict) -> None:
    """Write the master index file."""
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


def save_reference(collection: ReferenceCollection, output_dir: Path | None = None) -> Path:
    """Save a reference collection to disk and update the master index.

    Args:
        collection: The reference collection to save.
        output_dir: Override output directory (defaults to REFERENCES_DIR/<platform>/).

    Returns:
        Path to the saved JSON file.
    """
    platform = collection.metadata.get("source_platform", "unknown")
    if output_dir is None:
        output_dir = REFERENCES_DIR / platform
    output_dir.mkdir(parents=True, exist_ok=True)

    ref_id = collection.reference_id
    filename = f"{ref_id}.json"
    filepath = output_dir / filename

    data = {
        "metadata": collection.metadata,
        "segments": [
            {
                "index": seg.index,
                "start": round(seg.start, 3),
                "end": round(seg.end, 3),
                "text": seg.text,
                "confidence": round(seg.confidence, 4),
            }
            for seg in collection.segments
        ],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # Update master index
    index = _load_index()
    # Remove existing entry for this ID if present
    index["collections"] = [c for c in index["collections"] if c.get("reference_id") != ref_id]
    index["collections"].append({
        "reference_id": ref_id,
        "platform": platform,
        "language": collection.metadata.get("reference_language", ""),
        "source_url": collection.metadata.get("source_url", ""),
        "original_video_url": collection.metadata.get("original_video_url", ""),
        "video_title": collection.metadata.get("video_title", ""),
        "segment_count": len(collection.segments),
        "file": str(filepath.relative_to(REFERENCES_DIR)),
        "added_at": datetime.now(timezone.utc).isoformat(),
    })
    _save_index(index)

    logger.info("Saved reference %s: %s (%d segments)", ref_id, filepath, len(collection.segments))
    return filepath


def load_reference(reference_id: str) -> ReferenceCollection:
    """Load a reference collection by its ID.

    Args:
        reference_id: The short ID of the reference collection.

    Returns:
        The loaded ReferenceCollection.

    Raises:
        FileNotFoundError: If the reference ID is not found in the index.
    """
    index = _load_index()
    entry = None
    for c in index["collections"]:
        if c["reference_id"] == reference_id:
            entry = c
            break

    if entry is None:
        raise FileNotFoundError(f"Reference not found: {reference_id}")

    filepath = REFERENCES_DIR / entry["file"]
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    segments = [
        ReferenceSegment(
            index=seg["index"],
            start=seg["start"],
            end=seg["end"],
            text=seg["text"],
            confidence=seg.get("confidence", 1.0),
        )
        for seg in data["segments"]
    ]
    return ReferenceCollection(
        metadata=data["metadata"],
        segments=segments,
        reference_id=reference_id,
    )


def list_references(language: str | None = None, platform: str | None = None) -> list[dict]:
    """List all reference collections, optionally filtered.

    Args:
        language: Filter by reference language (e.g., 'zh-CN').
        platform: Filter by source platform (e.g., 'bilibili', 'youtube').

    Returns:
        List of index entries matching the filters.
    """
    index = _load_index()
    results = index["collections"]
    if language:
        results = [c for c in results if c.get("language") == language]
    if platform:
        results = [c for c in results if c.get("platform") == platform]
    return results


def search_references(query: str, language: str | None = None) -> list[dict]:
    """Search reference collections by text in title or URL.

    Args:
        query: Search string to match against title and URL fields.
        language: Optional language filter.

    Returns:
        List of matching index entries.
    """
    refs = list_references(language=language)
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    return [
        r for r in refs
        if pattern.search(r.get("video_title", ""))
        or pattern.search(r.get("source_url", ""))
        or pattern.search(r.get("original_video_url", ""))
    ]


def create_collection_from_ocr_json(
    ocr_json_path: Path,
    *,
    source_url: str = "",
    original_video_url: str = "",
    reference_language: str = "zh-CN",
    platform: str = "",
    video_title: str = "",
) -> ReferenceCollection:
    """Create a ReferenceCollection from an OCR JSON output file.

    Args:
        ocr_json_path: Path to the OCR JSON file (from ocr.subtitles_to_json).
        source_url: URL of the source video.
        original_video_url: URL of the original JP video.
        reference_language: Language of the reference subtitles.
        platform: Source platform name.
        video_title: Title of the video.

    Returns:
        A new ReferenceCollection ready to be saved.
    """
    with open(ocr_json_path, encoding="utf-8") as f:
        data = json.load(f)

    segments = [
        ReferenceSegment(
            index=seg["index"],
            start=seg["start"],
            end=seg["end"],
            text=seg["text"],
            confidence=seg.get("confidence", 1.0),
        )
        for seg in data["segments"]
    ]

    metadata = {
        "source_url": source_url,
        "source_platform": platform,
        "source_type": "ocr",
        "original_video_url": original_video_url,
        "reference_language": reference_language,
        "extractor": "paddleocr",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "video_title": video_title,
    }

    return ReferenceCollection(metadata=metadata, segments=segments)


def create_collection_from_srt(
    srt_path: Path,
    *,
    source_url: str = "",
    original_video_url: str = "",
    reference_language: str = "zh-CN",
    platform: str = "",
    source_type: str = "soft_sub",
    video_title: str = "",
) -> ReferenceCollection:
    """Create a ReferenceCollection from an SRT file.

    Args:
        srt_path: Path to the SRT subtitle file.
        source_url: URL of the source video.
        original_video_url: URL of the original JP video.
        reference_language: Language of the reference subtitles.
        platform: Source platform name.
        source_type: How the subtitles were obtained.
        video_title: Title of the video.

    Returns:
        A new ReferenceCollection ready to be saved.
    """
    segments = _parse_srt(srt_path)

    metadata = {
        "source_url": source_url,
        "source_platform": platform,
        "source_type": source_type,
        "original_video_url": original_video_url,
        "reference_language": reference_language,
        "extractor": "srt_import",
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "video_title": video_title,
    }

    return ReferenceCollection(metadata=metadata, segments=segments)


def _parse_srt(srt_path: Path) -> list[ReferenceSegment]:
    """Parse an SRT file into ReferenceSegments."""
    content = srt_path.read_text(encoding="utf-8")
    segments = []
    blocks = re.split(r"\n\n+", content.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        # Line 1: index
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue

        # Line 2: timestamps
        ts_match = re.match(
            r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})",
            lines[1].strip(),
        )
        if not ts_match:
            continue

        start = _srt_ts_to_seconds(ts_match.group(1))
        end = _srt_ts_to_seconds(ts_match.group(2))

        # Lines 3+: text
        text = "\n".join(lines[2:]).strip()

        segments.append(ReferenceSegment(
            index=index,
            start=start,
            end=end,
            text=text,
        ))

    return segments


def _srt_ts_to_seconds(ts: str) -> float:
    """Convert SRT timestamp 'HH:MM:SS,mmm' to float seconds."""
    ts = ts.replace(",", ".")
    parts = ts.split(":")
    h, m = int(parts[0]), int(parts[1])
    s = float(parts[2])
    return h * 3600 + m * 60 + s
