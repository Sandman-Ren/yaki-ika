# Web Review UI — Design Document

## Overview

A fully client-side web application for reviewing and editing bilingual subtitle translations produced by the Splatoon Translate pipeline. Deployed as a static site to GitHub Pages — no server required.

## Problem

The Python pipeline produces machine-translated subtitles that need human review. Currently, reviewing requires opening SRT files in a text editor alongside a video player — there's no integrated view showing video + original + translation synced together, and no way to mark segments as approved/rejected.

## Solution

A browser-based review tool that loads the pipeline's output files (video + SRTs + terms JSON) and provides:

- Video player synced with a bilingual subtitle table (JP original + translated)
- Inline editing of translations
- Segment-level status tracking (approve / reject / needs review)
- Glossary term highlighting in Japanese text
- Audio waveform timeline with draggable regions per segment
- Keyboard shortcuts for efficient review workflow
- Export of edited SRT files
- Persistence via IndexedDB (survives browser refresh)

## Tech Stack

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Build | Vite + React 19 + TypeScript | Static SPA output, fast HMR, no server needed |
| Video | Vidstack (`@vidstack/react`) | Modern React-native player, 53kB gzip, excellent cue API |
| Waveform | wavesurfer.js v7 + Regions | Draggable subtitle regions on waveform, 9.9k stars |
| SRT Parsing | subsrt-ts | Multi-format (SRT/VTT/ASS), zero deps, TypeScript |
| State | Zustand + zundo | Lightweight, undo/redo via temporal middleware |
| UI | shadcn/ui + Radix + Tailwind CSS | Accessible, customizable, copy-paste ownership |
| Virtual Scroll | @tanstack/react-virtual | Variable-height CJK rows without DOM bloat |
| Persistence | IndexedDB via idb | Structured async storage, no 4MB localStorage limit |
| Deployment | GitHub Pages via gh-pages | Zero cost, static hosting |

## Layout

```
+------------------------------------------------------------------+
|  Toolbar: project name | import | export | settings               |
+----------------------------+-------------------------------------+
|  Video Player              |  Glossary Panel (collapsible)       |
|  (Vidstack)                |  - matched terms list               |
|                            |  - term search                      |
|  [play/pause] [rate] [loop]|  - category badges                  |
+----------------------------+-------------------------------------+
|  Waveform Timeline (wavesurfer.js)                                |
|  [====green====][===gray===][==yellow==][====green====][===red===]|
+------------------------------------------------------------------+
|  Search: [________] | Filter: [All|Approved|Rejected|Unreviewed]  |
+------+----------+--------------------+------------------+---------+
|  #   | Time     | JP Original        | Translation      | Status  |
+------+----------+--------------------+------------------+---------+
|  1   | 0:00-0:02| はいどうもこんにちは| 大家好我是Resha   |   ✓     |
|  2*  | 0:02-0:06| 今回はXP3700...    | 这次是XP3700...   |   ?     |
|  3   | 0:06-0:08| ショクワンダー解説  | 触手攀升解说      |   ✗     |
+------+----------+--------------------+------------------+---------+
|  Status Bar: 107 segments | 89 approved | 3 rejected | 15 pending |
+------------------------------------------------------------------+
```

## Data Flow

```
[File inputs: video.mp4, .ja.srt, .zh.srt, .terms.json]
  |
  v
file-loader.ts -> srt-parser.ts -> pair by segment index -> BilingualEntry[]
  |
  v
project-store (Zustand + zundo)
  |-- entries: BilingualEntry[] (editable, undo/redo tracked)
  |-- terms: GlossaryTerm[] (read-only)
  |-- videoFile: File (for blob URL)
  |
  v
playback-store                      ui-store
  |-- currentTimeMs (from video)      |-- activeSegmentIndex (binary search)
  |-- isPlaying                        |-- searchQuery, statusFilter
  |-- playbackRate                     |-- selectedIndices
```

## Segment Status Workflow

```
Unreviewed (gray) -> Approved (green)
                  -> Rejected (red)    -> Re-edited -> Approved
                  -> Needs Review (yellow)
```

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Play / pause (when not editing) |
| Ctrl+Enter | Approve segment and advance |
| Ctrl+Shift+Enter | Reject segment and advance |
| Alt+Up/Down | Navigate segments |
| Alt+Left/Right | Seek video +/-5s |
| Ctrl+Z | Undo |
| Ctrl+Shift+Z | Redo |
| Ctrl+S | Save |
| Ctrl+F | Search |
| F1 | Keyboard shortcuts help |

## Key Decisions

1. **Three separate Zustand stores**: project-store (with undo/redo), playback-store (high-frequency, no undo), ui-store (transient). Prevents undo from capturing time changes.

2. **Waveform visualization-only mode**: Decode audio separately via Web Audio API, sync cursor position to Vidstack programmatically. Avoids conflicts from sharing the media element.

3. **Pair segments by index**: Pipeline guarantees 1:1 JP-to-translated mapping. If counts differ, pad with empty entries and warn.

4. **No server needed**: Video files loaded via File API + blob URL. State persisted in IndexedDB. Export via browser download. CJK fonts from Google Fonts CDN.

5. **Video not persisted in IndexedDB**: Too large. User re-imports video on reload; subtitle edits and review state are restored automatically.

## Implementation Phases

1. **Scaffold**: Vite + React + Tailwind + shadcn/ui setup
2. **Data layer**: Types, SRT parser, Zustand stores, file loader
3. **Import + layout**: File drop zone, resizable panel shell
4. **Video player**: Vidstack integration, time sync hook
5. **Subtitle table**: Virtual-scrolled bilingual table with editing
6. **Waveform**: wavesurfer.js timeline with colored regions
7. **Glossary**: Term highlighting, tooltip, side panel
8. **Export + persistence**: SRT export, IndexedDB auto-save
9. **Keyboard shortcuts**: Global shortcut handler
10. **Settings + polish**: Preferences, dark mode, help overlay
