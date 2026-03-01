import { parse, build } from 'subsrt-ts'
import type { Segment, TrackEntry, TrackMeta } from '@/types'

interface ContentCaption {
  type: 'caption'
  index: number
  start: number
  end: number
  duration: number
  content: string
  text: string
}

// ---- Multi-track project builder ----

interface TrackInput {
  id: string
  label: string
  lang: string
  sourceFile: string
  content: string
}

interface BuildResult {
  segments: Segment[]
  trackMetas: TrackMeta[]
  warnings: string[]
}

/**
 * Build a multi-track project from a Japanese source SRT and N translated SRTs.
 * Pairs segments by index. Pads shorter tracks with empty entries.
 */
export function buildProject(jaContent: string, tracks: TrackInput[]): BuildResult {
  const jaCaptions = parse(jaContent).filter((c): c is ContentCaption => c.type === 'caption')
  const warnings: string[] = []

  const parsedTracks = tracks.map((t) => ({
    ...t,
    captions: parse(t.content).filter((c): c is ContentCaption => c.type === 'caption'),
  }))

  // Find max segment count across all files
  let maxLen = jaCaptions.length
  for (const t of parsedTracks) {
    if (t.captions.length !== jaCaptions.length) {
      warnings.push(
        `Segment count mismatch: JA has ${jaCaptions.length}, ${t.label} has ${t.captions.length}. Padding shorter file.`
      )
    }
    maxLen = Math.max(maxLen, t.captions.length)
  }

  const segments: Segment[] = []

  for (let i = 0; i < maxLen; i++) {
    const ja = jaCaptions[i]

    const trackEntries: Record<string, TrackEntry> = {}
    for (const t of parsedTracks) {
      const cap = t.captions[i]
      trackEntries[t.id] = {
        original: cap?.content ?? '',
        edited: null,
        status: 'pending',
      }
    }

    segments.push({
      index: i,
      startTime: (ja?.start ?? 0) / 1000,
      endTime: (ja?.end ?? 0) / 1000,
      source: ja?.content ?? '',
      tracks: trackEntries,
    })
  }

  const trackMetas: TrackMeta[] = parsedTracks.map((t) => ({
    id: t.id,
    label: t.label,
    lang: t.lang,
    sourceFile: t.sourceFile,
  }))

  return { segments, trackMetas, warnings }
}

// ---- Single-track SRT export ----

/** Build SRT for a single track, using edited text where available */
export function buildTrackSrt(segments: Segment[], trackId: string): string {
  const captions = segments.map((seg, i) => {
    const entry = seg.tracks[trackId]
    const text = entry?.edited ?? entry?.original ?? ''
    return {
      type: 'caption' as const,
      index: i + 1,
      start: seg.startTime * 1000,
      end: seg.endTime * 1000,
      duration: (seg.endTime - seg.startTime) * 1000,
      content: text,
      text,
    }
  })

  return build(captions, { format: 'srt' })
}

/** Build bilingual SRT (JP source + one track), two lines per block */
export function buildBilingualSrt(segments: Segment[], trackId: string): string {
  const captions = segments.map((seg, i) => {
    const entry = seg.tracks[trackId]
    const translated = entry?.edited ?? entry?.original ?? ''
    const content = `${seg.source}\n${translated}`
    return {
      type: 'caption' as const,
      index: i + 1,
      start: seg.startTime * 1000,
      end: seg.endTime * 1000,
      duration: (seg.endTime - seg.startTime) * 1000,
      content,
      text: content,
    }
  })

  return build(captions, { format: 'srt' })
}

/** Build review summary JSON with all edits and statuses */
export function buildReviewSummary(
  meta: { name: string; trackOrder: string[] },
  segments: Segment[],
  trackMetas: TrackMeta[]
): string {
  const summary = {
    project: meta.name,
    exportedAt: new Date().toISOString(),
    tracks: trackMetas.map((t) => ({ id: t.id, label: t.label, lang: t.lang })),
    segments: segments.map((seg) => {
      const trackData: Record<string, { original: string; edited: string | null; status: string }> = {}
      for (const t of trackMetas) {
        const entry = seg.tracks[t.id]
        if (entry) {
          trackData[t.id] = {
            original: entry.original,
            edited: entry.edited,
            status: entry.status,
          }
        }
      }
      return {
        index: seg.index,
        startTime: seg.startTime,
        endTime: seg.endTime,
        source: seg.source,
        tracks: trackData,
      }
    }),
  }
  return JSON.stringify(summary, null, 2)
}

// ---- Utilities ----

export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}
