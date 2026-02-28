import { parse, build } from 'subsrt-ts'
import type { Segment } from '@/types'

interface ContentCaption {
  type: 'caption'
  index: number
  start: number
  end: number
  duration: number
  content: string
  text: string
}

interface PairResult {
  segments: Segment[]
  warnings: string[]
}

export function pairSubtitles(jaContent: string, translatedContent: string): PairResult {
  const jaCaptions = parse(jaContent).filter((c): c is ContentCaption => c.type === 'caption')
  const translatedCaptions = parse(translatedContent).filter((c): c is ContentCaption => c.type === 'caption')
  const warnings: string[] = []

  const maxLen = Math.max(jaCaptions.length, translatedCaptions.length)

  if (jaCaptions.length !== translatedCaptions.length) {
    warnings.push(
      `Segment count mismatch: JP has ${jaCaptions.length}, translated has ${translatedCaptions.length}. Padding shorter file.`
    )
  }

  const segments: Segment[] = []

  for (let i = 0; i < maxLen; i++) {
    const ja = jaCaptions[i]
    const tr = translatedCaptions[i]

    segments.push({
      index: i,
      // subsrt-ts returns times in milliseconds — convert to seconds
      startTime: (ja?.start ?? tr?.start ?? 0) / 1000,
      endTime: (ja?.end ?? tr?.end ?? 0) / 1000,
      original: ja?.content ?? '',
      translated: tr?.content ?? '',
      editedTranslation: null,
      status: 'pending',
    })
  }

  return { segments, warnings }
}

export function buildSrt(segments: Segment[]): string {
  const captions = segments.map((seg, i) => ({
    type: 'caption' as const,
    index: i + 1,
    // Convert seconds back to milliseconds for subsrt-ts
    start: seg.startTime * 1000,
    end: seg.endTime * 1000,
    duration: (seg.endTime - seg.startTime) * 1000,
    content: seg.editedTranslation ?? seg.translated,
    text: seg.editedTranslation ?? seg.translated,
  }))

  return build(captions, { format: 'srt' })
}

export function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}
