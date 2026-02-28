# Yaki-Ika

Automated Japanese subtitle translation pipeline for Splatoon 3 videos.

Splatoon 3 (JP) video -> Japanese transcription -> domain-aware translation -> subtitled video

## Features

- **Japanese ASR** via [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (large-v3-turbo) with VAD filtering
- **Splatoon 3 glossary** built from [Leanny's datamined data](https://github.com/Leanny/splat3) (~1,700 bilingual term entries) plus hand-curated community jargon
- **MeCab term extraction** with 3 matching strategies (exact, n-gram, substring) to inject correct game terminology into translation prompts
- **LLM translation** via Anthropic Claude or OpenAI with batched segment processing and glossary-augmented prompts
- **Multi-language support**: Simplified Chinese (`zh-CN`), Traditional Chinese (`zh-TW`), English (`en`)
- **Subtitle generation**: SRT output with language-aware line wrapping, bilingual review SRT (JP + target), and FFmpeg burn-in with GPU acceleration

## Pipeline

```
YouTube URL / local video
  -> yt-dlp download
  -> FFmpeg audio extraction (16kHz mono WAV)
  -> faster-whisper transcription (Silero VAD + beam_size=1)
  -> MeCab morphological analysis + glossary matching
  -> LLM translation (batched, glossary-injected)
  -> SRT generation (translated + bilingual)
  -> FFmpeg subtitle burn-in (h264_nvenc GPU / libx264 CPU fallback)
```

## Requirements

- Python 3.11+
- CUDA GPU (recommended for Whisper and FFmpeg encoding)
- FFmpeg with libass support
- yt-dlp (for YouTube downloads)
- Anthropic API key or OpenAI API key

## Setup

```bash
# Clone the repo
git clone https://github.com/Sandman-Ren/yaki-ika.git
cd yaki-ika

# Install uv (https://docs.astral.sh/uv/getting-started/installation/)
# Then sync dependencies (creates .venv, installs everything)
uv sync

# Set up API key
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY or OPENAI_API_KEY

# Build the glossary (requires Leanny's splat3 data in ../deps/splat3)
uv run python scripts/build_glossary.py zh-CN
```

## Usage

```bash
# Translate a YouTube video (default: Simplified Chinese, with burn-in)
uv run yaki-ika https://www.youtube.com/watch?v=VIDEO_ID -o ./output

# Translate to English, SRT only (no video burn-in)
uv run yaki-ika video.mp4 -l en --no-burn -o ./output

# Use CPU encoding instead of GPU
uv run yaki-ika video.mp4 --cpu -o ./output
```

### CLI Options

| Flag | Description |
|------|-------------|
| `-o, --output-dir` | Output directory (default: `./output`) |
| `-l, --lang` | Target language: `zh-CN`, `zh-TW`, `en` (default: `zh-CN`) |
| `--model-size` | Whisper model size (default: `large-v3-turbo`) |
| `--translation-model` | LLM model name |
| `--translation-provider` | `anthropic` or `openai` |
| `--no-burn` | Skip video burn-in, output SRT only |
| `--soft-subs` | Add as toggleable subtitle track |
| `--cpu` | Use CPU for FFmpeg encoding |
| `--no-intermediates` | Don't keep intermediate files |

## Output Files

For a video named `video.mp4` with target language `zh-CN`:

| File | Description |
|------|-------------|
| `video.ja.srt` | Japanese transcript |
| `video.zh.srt` | Chinese subtitles |
| `video.bilingual.zh.srt` | Bilingual (JP + CN) for review |
| `video.terms.zh.json` | Matched glossary terms |
| `video.subtitled.mp4` | Video with burned-in subtitles |

## Project Structure

```
src/splatoon_translate/
  config.py      # Paths, model defaults, language configs
  download.py    # yt-dlp wrapper
  audio.py       # FFmpeg audio extraction
  transcribe.py  # faster-whisper ASR
  glossary.py    # Leanny data + jargon -> bilingual glossary
  terms.py       # MeCab tokenization + glossary matching
  translate.py   # LLM translation with batching & RAG
  subtitle.py    # SRT generation with line wrapping
  embed.py       # FFmpeg subtitle burn-in
  pipeline.py    # CLI orchestrator

data/jargon/     # Hand-curated community terminology
scripts/         # Standalone utilities
```

## License

MIT

---

# Yaki-Ika

Splatoon 3 日语视频自动字幕翻译工具。

Splatoon 3 日语视频 -> 日语转录 -> 游戏术语感知翻译 -> 字幕视频

## 功能特性

- **日语语音识别**: 使用 [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (large-v3-turbo) 配合 VAD 语音活动检测
- **Splatoon 3 术语表**: 基于 [Leanny 数据挖掘数据](https://github.com/Leanny/splat3) 构建约 1,700 条双语术语，加上手工整理的社区用语
- **MeCab 术语提取**: 三种匹配策略（精确匹配、n-gram、子串），将正确的游戏术语注入翻译提示词
- **LLM 翻译**: 支持 Anthropic Claude 和 OpenAI，分批处理字幕段落，术语表增强提示
- **多语言支持**: 简体中文 (`zh-CN`)、繁体中文 (`zh-TW`)、英语 (`en`)
- **字幕生成**: SRT 输出支持语言自适应换行、双语审校 SRT（日语+目标语言），以及 FFmpeg GPU 加速烧录

## 处理流程

```
YouTube 链接 / 本地视频
  -> yt-dlp 下载
  -> FFmpeg 音频提取 (16kHz 单声道 WAV)
  -> faster-whisper 语音转录 (Silero VAD + beam_size=1)
  -> MeCab 形态素解析 + 术语表匹配
  -> LLM 翻译 (分批处理, 术语表注入)
  -> SRT 字幕生成 (翻译版 + 双语版)
  -> FFmpeg 字幕烧录 (h264_nvenc GPU / libx264 CPU 回退)
```

## 环境要求

- Python 3.11+
- CUDA GPU（推荐，用于 Whisper 和 FFmpeg 编码）
- 支持 libass 的 FFmpeg
- yt-dlp（用于下载 YouTube 视频）
- Anthropic API 密钥或 OpenAI API 密钥

## 安装

```bash
git clone https://github.com/Sandman-Ren/yaki-ika.git
cd yaki-ika

# 安装 uv (https://docs.astral.sh/uv/getting-started/installation/)
# 同步依赖（自动创建 .venv，安装所有依赖）
uv sync

cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY 或 OPENAI_API_KEY

# 构建术语表（需要 Leanny 的 splat3 数据位于 ../deps/splat3）
uv run python scripts/build_glossary.py zh-CN
```

## 使用方法

```bash
# 翻译 YouTube 视频（默认简体中文，烧录字幕）
uv run yaki-ika https://www.youtube.com/watch?v=VIDEO_ID -o ./output

# 翻译为英语，仅输出 SRT（不烧录视频）
uv run yaki-ika video.mp4 -l en --no-burn -o ./output

# 使用 CPU 编码
uv run yaki-ika video.mp4 --cpu -o ./output
```

## 输出文件

以视频 `video.mp4`、目标语言 `zh-CN` 为例：

| 文件 | 说明 |
|------|------|
| `video.ja.srt` | 日语转录 |
| `video.zh.srt` | 中文字幕 |
| `video.bilingual.zh.srt` | 双语字幕（日+中），用于审校 |
| `video.terms.zh.json` | 匹配到的术语 |
| `video.subtitled.mp4` | 烧录字幕的视频 |

## 许可证

MIT
