# Yaki-Ika — Technical Setup Guide

Quick-start reference for developers and power users. Assumes familiarity with CLI tools, package managers, environment variables, and Python virtual environments.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.11+ | Required |
| Node.js | 18+ | For the web review UI only |
| FFmpeg | Latest | Must include `libass`. Verify: `ffmpeg -filters \| grep subtitles` |
| yt-dlp | Latest | `pip install yt-dlp` or standalone binary |
| NVIDIA GPU + CUDA | Optional | Strongly recommended. Enables `float16` Whisper inference and `h264_nvenc` encoding. CPU fallback works but is significantly slower. |

### System dependency install cheatsheet

**Windows (winget):**

```bash
winget install Python.Python.3.12
winget install Gyan.FFmpeg
pip install yt-dlp
```

**macOS (Homebrew):**

```bash
brew install python@3.12 ffmpeg yt-dlp
```

**Ubuntu/Debian:**

```bash
sudo apt update && sudo apt install -y python3.12 python3.12-venv ffmpeg
pip install yt-dlp
```

---

## Installation

```bash
# 1. Clone the repo
git clone https://github.com/Sandman-Ren/yaki-ika.git
cd yaki-ika

# 2. Install uv (Python package manager) — skip if already installed
# Windows:
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# macOS/Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh

# 3. Sync dependencies (creates .venv, installs all packages + CLI entry point)
uv sync

# 4. Configure API keys
cp .env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY:
#   ANTHROPIC_API_KEY=sk-ant-api03-...
#   OPENAI_API_KEY=sk-...          (optional, only if using --translation-provider openai)

# 5. Verify
uv run yaki-ika --help
```

### Optional: OCR dependencies

For extracting burned-in subtitles from existing videos (PaddleOCR):

```bash
uv sync --extra ocr
```

> On CPU-only systems, edit `pyproject.toml` and replace `paddlepaddle-gpu` with `paddlepaddle` before running the above.

### Optional: Rebuild glossaries

Only needed if you want to regenerate glossaries from newer Leanny game data:

```bash
# From the workspace root (parent of the yaki-ika repo):
git clone https://github.com/Leanny/splat3.git deps/splat3

# Back in the repo:
cd yaki-ika
uv run python scripts/build_glossary.py zh-CN   # also: en, zh-TW
```

Pre-built glossaries for all three languages are already included in `data/glossary/`.

---

## CLI Usage

### Basic translation

```bash
# Translate a YouTube video to Simplified Chinese (default)
uv run yaki-ika "https://www.youtube.com/watch?v=VIDEO_ID"

# Translate a local video to English
uv run yaki-ika ./video.mp4 -l en

# Translate and burn subtitles into the video
uv run yaki-ika "https://..." --burn

# Burn bilingual subtitles (JP on top, translation below)
uv run yaki-ika "https://..." --burn --burn-subtitle bilingual

# Add as a toggleable soft-sub track (no re-encoding, fast)
uv run yaki-ika "https://..." --soft-subs
```

### Full CLI reference

```
uv run yaki-ika <source> [options]

Positional:
  source                         YouTube URL or local video file path

Options:
  -o, --output-dir DIR           Output directory (default: ./output)
  -l, --lang {en,zh-CN,zh-TW}   Target language (default: zh-CN)
  --model-size SIZE              Whisper model (default: large-v3-turbo)
  --translation-model MODEL      LLM model (default: claude-sonnet-4-20250514)
  --translation-provider PROV    anthropic | openai (default: anthropic)
  --burn                         Burn subtitles into video (libass + h264_nvenc/libx264)
  --burn-subtitle TYPE           translated | ja | bilingual | /path/to/file.srt
  --soft-subs                    Mux SRT as toggleable track (overrides --burn)
  --cpu                          Force CPU encoding (skip h264_nvenc)
  --no-intermediates             Delete .wav and .terms.json after completion
```

### Output structure

```
output/
└── <video_title>/
    ├── <video_title>.mp4                    # Source video
    ├── <video_title>.wav                    # Extracted audio (intermediate)
    ├── <video_title>.ja.srt                 # Japanese transcript (Whisper)
    ├── <video_title>.zh.srt                 # Translated subtitles
    ├── <video_title>.bilingual.zh.srt       # Bilingual JP + translation
    ├── <video_title>.terms.zh.json          # Matched glossary terms (intermediate)
    └── <video_title>.subtitled.mp4          # Burned/soft-subbed video (if requested)
```

Language suffix mapping: `zh-CN` / `zh-TW` → `.zh`, `en` → `.en`.

---

## Pipeline Stages

The CLI runs these stages sequentially:

| # | Stage | Module | What it does |
|---|-------|--------|-------------|
| 1 | Download | `download.py` | yt-dlp downloads video ≤1080p, merges to MP4. Skipped for local files. |
| 2 | Extract audio | `audio.py` | FFmpeg → 16kHz mono 16-bit PCM WAV |
| 3 | Transcribe | `transcribe.py` | faster-whisper with Silero VAD, beam_size=1, 48 post-correction rules, silence filtering |
| 4 | Term extraction | `terms.py` | MeCab tokenization → 3-strategy glossary matching (exact, n-gram, substring) |
| 5 | Translate | `translate.py` | LLM batches of 40 segments with glossary context, translation memory (5 prior pairs), structured output |
| 6 | Generate SRT | `subtitle.py` | Produces translated + bilingual SRT with line wrapping (42 chars EN, 22 chars CJK) |
| 7 | Embed | `embed.py` | FFmpeg burn-in (libass + h264_nvenc/libx264) or soft-sub mux. Only if `--burn` or `--soft-subs`. |

---

## Configuration

### Environment variables (.env)

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | **Required** (unless using OpenAI provider) |
| `OPENAI_API_KEY` | — | Required only with `--translation-provider openai` |

### Hardcoded defaults (config.py)

| Setting | Value |
|---------|-------|
| ASR model | `large-v3-turbo` |
| ASR device | `cuda` (auto-falls-back to CPU) |
| ASR compute type | `float16` |
| Translation model | `claude-sonnet-4-20250514` |
| Translation provider | `anthropic` |
| Translation batch size | 40 segments |
| Translation memory window | 5 prior pairs |
| Max subtitle lines | 2 |
| Max chars/line (EN) | 42 |
| Max chars/line (CJK) | 22 |

All of these except the API keys are overridable via CLI flags or by editing `config.py` directly.

---

## Web Review UI

A client-side React SPA for reviewing and editing translated subtitles before final export.

### Setup

```bash
cd web
npm install
npm run dev     # → http://localhost:5173
```

### Usage

1. **Import** — Load files from the pipeline output directory:
   - Video file (`.mp4`)
   - Japanese SRT (`.ja.srt`)
   - Translated SRT (`.zh.srt` or `.en.srt`)
   - Terms JSON (`.terms.zh.json`) — optional, enables term highlighting
2. **Review** — Click rows to seek video; click translated text to edit inline; set status per segment (pending / approved / needs-revision / rejected)
3. **Export** — Downloads corrected SRT with your edits applied

### Tech stack

React 19, Vite 7, TypeScript 5.9, Tailwind v4, shadcn/ui, Zustand 5, @vidstack/react, @tanstack/react-virtual, subsrt-ts.

### Current limitations (MVP)

- No waveform timeline
- No keyboard shortcuts
- No IndexedDB persistence (edits lost on page refresh)
- No undo/redo

---

## Utility Scripts

### Reference translations

```bash
# Add reference from URL (auto-detects platform, tries soft-subs then OCR)
uv run python scripts/gather_references.py add "URL" --ref-lang zh-CN

# Add from local SRT
uv run python scripts/gather_references.py add ./subs/translation.srt \
    --ref-lang zh-CN --original-url "https://..."

# List all references
uv run python scripts/gather_references.py list [--lang zh-CN] [--platform bilibili]

# Search references
uv run python scripts/gather_references.py search "splatfest"
```

### OCR subtitle extraction

```bash
uv run --extra ocr python scripts/extract_subtitles.py video.mp4 -o ./output --format both
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ANTHROPIC_API_KEY not set` | Missing `.env` or not running from repo root | Create `.env` from `.env.example`; run `uv run yaki-ika` from the repo root |
| `ffmpeg: command not found` | Not on PATH | Install and verify: `ffmpeg -version` |
| `h264_nvenc not found` | No NVIDIA GPU or missing CUDA drivers | Automatic CPU fallback. Or pass `--cpu` explicitly. |
| Whisper on CPU (very slow) | PyTorch without CUDA support | `python -c "import torch; print(torch.cuda.is_available())"` — if False, install CUDA-enabled PyTorch from pytorch.org |
| MeCab errors | Broken package install | `pip install --force-reinstall mecab-python3 unidic-lite` |
| Download fails | Outdated yt-dlp or geo-restriction | `pip install -U yt-dlp`; for local files, pass the full path |
| `[warn]` in stderr during translation | Segment fallback to JP original | Review `.terms.json` for missing terms; check bilingual SRT |
| Web UI won't start | Missing npm dependencies | `cd web && rm -rf node_modules && npm install` |
