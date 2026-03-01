import { useCallback } from 'react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useProjectStore } from '@/stores/project-store'
import { buildTrackSrt, buildBilingualSrt, buildReviewSummary } from '@/lib/srt'
import { Download } from 'lucide-react'

function downloadBlob(content: string, filename: string, type = 'text/plain;charset=utf-8') {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export function ExportMenu() {
  const segments = useProjectStore((s) => s.segments)
  const meta = useProjectStore((s) => s.meta)
  const trackMetas = useProjectStore((s) => s.trackMetas)
  const isLoaded = useProjectStore((s) => s.isLoaded)

  const projectName = meta?.name ?? 'subtitles'

  const exportTrack = useCallback(
    (trackId: string) => {
      const content = buildTrackSrt(segments, trackId)
      downloadBlob(content, `${projectName}.${trackId}.edited.srt`, 'text/srt;charset=utf-8')
    },
    [segments, projectName]
  )

  const exportBilingual = useCallback(
    (trackId: string) => {
      const content = buildBilingualSrt(segments, trackId)
      downloadBlob(content, `${projectName}.${trackId}.bilingual.srt`, 'text/srt;charset=utf-8')
    },
    [segments, projectName]
  )

  const exportAllTracks = useCallback(() => {
    for (const track of trackMetas) {
      const content = buildTrackSrt(segments, track.id)
      downloadBlob(content, `${projectName}.${track.id}.edited.srt`, 'text/srt;charset=utf-8')
    }
  }, [segments, trackMetas, projectName])

  const exportReview = useCallback(() => {
    if (!meta) return
    const content = buildReviewSummary(meta, segments, trackMetas)
    downloadBlob(content, `${projectName}.review.json`, 'application/json;charset=utf-8')
  }, [meta, segments, trackMetas, projectName])

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" disabled={!isLoaded}>
          <Download className="mr-2 h-4 w-4" />
          Export
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {trackMetas.map((track) => (
          <DropdownMenuItem key={`srt-${track.id}`} onClick={() => exportTrack(track.id)}>
            SRT: {track.label}
          </DropdownMenuItem>
        ))}

        {trackMetas.length > 1 && (
          <DropdownMenuItem onClick={exportAllTracks}>
            SRT: All tracks
          </DropdownMenuItem>
        )}

        <DropdownMenuSeparator />

        {trackMetas.map((track) => (
          <DropdownMenuItem key={`bi-${track.id}`} onClick={() => exportBilingual(track.id)}>
            Bilingual: JA + {track.label}
          </DropdownMenuItem>
        ))}

        <DropdownMenuSeparator />

        <DropdownMenuItem onClick={exportReview}>
          Review summary (JSON)
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
