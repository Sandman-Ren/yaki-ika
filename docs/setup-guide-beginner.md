# Yaki-Ika — Beginner Setup Guide

This guide walks you through setting up and using Yaki-Ika from scratch. No programming experience required — just follow each step carefully.

**What is Yaki-Ika?** It's a tool that takes Japanese Splatoon 3 videos and automatically translates the subtitles into English, Simplified Chinese, or Traditional Chinese. It can also burn those translated subtitles directly onto the video.

---

## Table of Contents

1. [What You'll Need](#1-what-youll-need)
2. [Install the Required Tools](#2-install-the-required-tools)
3. [Download and Set Up Yaki-Ika](#3-download-and-set-up-yaki-ika)
4. [Get Your API Key](#4-get-your-api-key)
5. [Translate Your First Video](#5-translate-your-first-video)
6. [Find Your Output Files](#6-find-your-output-files)
7. [Review Translations in the Web UI (Optional)](#7-review-translations-in-the-web-ui-optional)
8. [Common Tasks](#8-common-tasks)
9. [Something Went Wrong?](#9-something-went-wrong)

---

## 1. What You'll Need

Before starting, make sure you have:

- **A computer** running Windows 10/11, macOS, or Linux
- **An internet connection** for downloading tools and translating
- **An Anthropic API key** (we'll walk through getting one in [Step 4](#4-get-your-api-key)) — this costs money per translation, but a typical 10-minute video costs about $0.05–0.15 USD
- **About 5 GB of free disk space** for the tools and Whisper AI model (downloaded automatically on first run)

**Recommended but not required:**
- An NVIDIA graphics card (GPU) — makes transcription and video encoding much faster. Without one, everything still works, just slower.

---

## 2. Install the Required Tools

You need to install four things before Yaki-Ika can work. Follow the instructions for your operating system.

### 2a. Install Python

Python is the programming language Yaki-Ika is written in.

**Windows:**
1. Open your web browser and go to https://www.python.org/downloads/
2. Click the big yellow **"Download Python 3.12.x"** button
3. Run the downloaded installer
4. **Important:** Check the box that says **"Add Python to PATH"** at the bottom of the installer window
5. Click **"Install Now"**

**macOS:**
1. Open **Terminal** (search for it in Spotlight with Cmd+Space)
2. If you don't have Homebrew, install it by pasting this and pressing Enter:
   ```
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
3. Then install Python:
   ```
   brew install python@3.12
   ```

**To verify it worked**, open a terminal (Command Prompt on Windows, Terminal on macOS/Linux) and type:

```
python --version
```

You should see something like `Python 3.12.x`. If you see an error, try `python3 --version` instead.

### 2b. Install FFmpeg

FFmpeg is a video processing tool that Yaki-Ika uses behind the scenes.

**Windows:**
1. Open Command Prompt (search for "cmd" in the Start menu)
2. Type this and press Enter:
   ```
   winget install Gyan.FFmpeg
   ```
3. Close and reopen Command Prompt

**macOS:**
```
brew install ffmpeg
```

**To verify:** Type `ffmpeg -version` in your terminal. You should see version information.

### 2c. Install yt-dlp

yt-dlp is a tool for downloading videos from YouTube and other sites.

Open your terminal and type:

```
pip install yt-dlp
```

> On macOS/Linux, you may need `pip3 install yt-dlp` instead.

**To verify:** Type `yt-dlp --version` in your terminal.

### 2d. Install uv

`uv` is a fast Python package manager that Yaki-Ika uses.

**Windows** — open Command Prompt and paste:

```
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**macOS/Linux** — open Terminal and paste:

```
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen your terminal after installing.

**To verify:** Type `uv --version` in your terminal.

---

## 3. Download and Set Up Yaki-Ika

### 3a. Download the project

Open your terminal and navigate to where you want to put the project. Then run:

```
git clone https://github.com/Sandman-Ren/yaki-ika.git
```

> If you don't have `git`, you can download the project as a ZIP from GitHub instead: go to https://github.com/Sandman-Ren/yaki-ika, click the green **"Code"** button, then **"Download ZIP"**, and extract it.

### 3b. Go into the project folder

```
cd yaki-ika
```

### 3c. Install all dependencies

This command sets everything up — it creates an isolated environment and installs all the packages Yaki-Ika needs:

```
uv sync
```

This may take a minute or two. You'll see progress messages as packages are downloaded.

### 3d. Verify the installation

```
uv run yaki-ika --help
```

You should see a help message showing available options. If you see this, everything is installed correctly.

---

## 4. Get Your API Key

Yaki-Ika uses Anthropic's Claude AI to translate subtitles. You need an API key to use it.

### 4a. Create an Anthropic account

1. Go to https://console.anthropic.com/
2. Click **"Sign Up"** and create an account
3. Add a payment method (translation costs about $0.05–0.15 per 10-minute video)

### 4b. Generate an API key

1. Once logged in, go to https://console.anthropic.com/settings/keys
2. Click **"Create Key"**
3. Give it a name like "yaki-ika"
4. **Copy the key** — it starts with `sk-ant-api03-`. You won't be able to see it again after closing the page!

### 4c. Save the key in the project

1. In the `yaki-ika` project folder, find the file called `.env.example`
2. Make a copy of it and rename the copy to `.env` (just `.env`, nothing else)

   **Windows (Command Prompt):**
   ```
   copy .env.example .env
   ```

   **macOS/Linux:**
   ```
   cp .env.example .env
   ```

3. Open `.env` in any text editor (Notepad, TextEdit, VS Code — anything works)
4. You'll see:
   ```
   ANTHROPIC_API_KEY=
   OPENAI_API_KEY=
   ```
5. Paste your API key after the `=` sign on the first line:
   ```
   ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
   OPENAI_API_KEY=
   ```
6. Save the file

> You can leave `OPENAI_API_KEY` empty unless you specifically want to use OpenAI instead of Claude.

---

## 5. Translate Your First Video

You're ready to go! Open your terminal, make sure you're in the `yaki-ika` folder, and run:

### From a YouTube URL

```
uv run yaki-ika "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
```

Replace `YOUR_VIDEO_ID` with the actual YouTube video ID or paste the full URL.

### From a local video file

```
uv run yaki-ika "C:\Users\you\Videos\splatoon_clip.mp4"
```

Use the full path to your video file.

### Choose your language

By default, subtitles are translated to **Simplified Chinese**. To change the language:

```
# English
uv run yaki-ika "https://..." -l en

# Traditional Chinese
uv run yaki-ika "https://..." -l zh-TW

# Simplified Chinese (default)
uv run yaki-ika "https://..." -l zh-CN
```

### Burn subtitles onto the video

If you want the translated subtitles permanently visible on the video:

```
uv run yaki-ika "https://..." --burn
```

For bilingual subtitles (Japanese on top, translation below):

```
uv run yaki-ika "https://..." --burn --burn-subtitle bilingual
```

For subtitles as a toggleable track you can turn on/off in your video player:

```
uv run yaki-ika "https://..." --soft-subs
```

### What happens when you run it

The tool will show progress as it works through these steps:

1. **Downloading** the video (if from a URL)
2. **Extracting audio** from the video
3. **Transcribing** the Japanese speech to text (this is the slowest step — the first run also downloads the Whisper AI model, which is about 1.5 GB)
4. **Finding game terms** in the transcript for accurate translation
5. **Translating** the subtitles using Claude AI
6. **Generating subtitle files**
7. **Burning subtitles** into the video (only if you used `--burn` or `--soft-subs`)

A typical 10-minute video takes about 3–5 minutes with a GPU, or 10–15 minutes without one.

---

## 6. Find Your Output Files

After the pipeline finishes, look in the `output/` folder inside the project directory. You'll find a subfolder named after the video:

```
output/
└── My Splatoon Video/
    ├── My Splatoon Video.mp4              ← The downloaded video
    ├── My Splatoon Video.ja.srt           ← Japanese transcript
    ├── My Splatoon Video.zh.srt           ← Translated subtitles
    ├── My Splatoon Video.bilingual.zh.srt ← Both languages side by side
    └── My Splatoon Video.subtitled.mp4    ← Video with burned subtitles (if you used --burn)
```

### How to use the subtitle files

- **`.srt` files** are standard subtitle files. You can:
  - Open them in any text editor to read the translations
  - Load them in video players like VLC (drag and drop the `.srt` onto the video)
  - Upload them to YouTube or other platforms
- **`.subtitled.mp4`** is the final video with subtitles already visible — ready to share

---

## 7. Review Translations in the Web UI (Optional)

Yaki-Ika includes a web-based review tool where you can watch the video, read the translations side-by-side, and make corrections before exporting.

### 7a. Install Node.js (one-time setup)

The web UI needs Node.js. Download and install it from https://nodejs.org/ — choose the **LTS** version.

### 7b. Set up the web UI

```
cd web
npm install
```

### 7c. Start the review UI

```
npm run dev
```

This opens a local website at **http://localhost:5173** — open that URL in your browser.

### 7d. Load your files

1. Click **Import** in the toolbar
2. Load these files from your output folder:
   - The video file (`.mp4`)
   - The Japanese subtitle file (`.ja.srt`)
   - The translated subtitle file (`.zh.srt` or `.en.srt`)
   - Optionally, the terms file (`.terms.zh.json`) for glossary highlighting

### 7e. Review and edit

- **Click any subtitle row** to jump the video to that moment
- **Click the translated text** to edit it
- **Set a status** for each subtitle: approved, needs revision, or rejected
- Use the **search bar** to find specific text
- Use the **filter** to show only subtitles that need attention

### 7f. Export your corrections

Click **Export** to download a new SRT file with all your edits applied.

### 7g. Stop the web UI

When you're done, go back to your terminal and press `Ctrl+C` to stop the web server.

---

## 8. Common Tasks

### Translate another video

Just run the command again with a different URL or file:

```
uv run yaki-ika "https://www.youtube.com/watch?v=ANOTHER_VIDEO"
```

### Update Yaki-Ika

To get the latest version:

```
cd yaki-ika
git pull
uv sync
```

### Update yt-dlp

If video downloads stop working, yt-dlp may need an update:

```
pip install -U yt-dlp
```

### Clean up intermediate files

If you don't need the `.wav` audio file and `.terms.json` after translation:

```
uv run yaki-ika "https://..." --no-intermediates
```

### Force CPU mode

If you're having issues with GPU encoding:

```
uv run yaki-ika "https://..." --cpu
```

---

## 9. Something Went Wrong?

### "ANTHROPIC_API_KEY not set"

Your `.env` file is missing or not in the right place.

**Fix:** Make sure the `.env` file exists in the `yaki-ika` folder (not inside a subfolder), and that it contains your API key. Also make sure you're running the command from inside the `yaki-ika` folder.

### "ffmpeg: command not found" or "'ffmpeg' is not recognized"

FFmpeg isn't installed or isn't on your system PATH.

**Fix:** Reinstall FFmpeg following [Step 2b](#2b-install-ffmpeg). On Windows, you may need to restart your terminal (or your computer) after installing.

### "yt-dlp: command not found"

**Fix:** Run `pip install yt-dlp` again. On macOS/Linux, try `pip3 install yt-dlp`.

### The first run is extremely slow

This is normal! On the first run, the Whisper speech recognition model (~1.5 GB) is downloaded automatically. Subsequent runs will be much faster since the model is cached.

### Video download fails

This can happen if:

- **yt-dlp is outdated** — Fix: `pip install -U yt-dlp`
- **The video is region-locked or private** — Fix: Download the video manually and pass the local file path instead
- **Your internet connection dropped** — Fix: Try again

### Translation seems wrong or inconsistent

- The tool includes a Splatoon-specific glossary with thousands of game terms to ensure accuracy
- If a specific term is mistranslated, you can review and fix it in the [Web UI](#7-review-translations-in-the-web-ui-optional)
- Try a different model: add `--translation-model claude-sonnet-4-20250514` to your command

### "h264_nvenc not found" warning

This just means your computer doesn't have an NVIDIA GPU (or the drivers aren't set up). The tool automatically falls back to CPU encoding. The video will still be created — it just takes a bit longer. This is not an error.

### The web UI won't start

**Fix:**

1. Make sure Node.js is installed: `node --version` should show a version number
2. Try reinstalling the web dependencies:
   ```
   cd web
   npm install
   npm run dev
   ```

### Nothing here helped

Open an issue at https://github.com/Sandman-Ren/yaki-ika/issues with:

- What command you ran
- The full error message
- Your operating system (Windows/macOS/Linux)

---

## Quick Reference Card

| What you want to do | Command |
|---------------------|---------|
| Translate a YouTube video to Chinese | `uv run yaki-ika "URL"` |
| Translate to English | `uv run yaki-ika "URL" -l en` |
| Translate a local video | `uv run yaki-ika "path/to/video.mp4"` |
| Burn subtitles onto video | `uv run yaki-ika "URL" --burn` |
| Burn bilingual subtitles | `uv run yaki-ika "URL" --burn --burn-subtitle bilingual` |
| Add toggleable subtitles | `uv run yaki-ika "URL" --soft-subs` |
| Force CPU mode | `uv run yaki-ika "URL" --cpu` |
| Delete intermediate files | `uv run yaki-ika "URL" --no-intermediates` |
| Start the review web UI | `cd web && npm run dev` |
| Update the tool | `git pull && uv sync` |
| Update yt-dlp | `pip install -U yt-dlp` |
