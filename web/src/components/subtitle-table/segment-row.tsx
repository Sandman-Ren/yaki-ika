import { memo, useCallback, useMemo } from 'react'
import type { Segment, SegmentStatus } from '@/types'
import { useProjectStore } from '@/stores/project-store'
import { usePlaybackStore } from '@/stores/playback-store'
import { useUiStore } from '@/stores/ui-store'
import { cn } from '@/lib/utils'
import { formatTime } from '@/lib/srt'
import { TrackCell } from './track-cell'
import { ActionsCell } from './actions-cell'

interface SegmentRowProps {
  segment: Segment
  visibleTrackIds: string[]
  trackLabels: Record<string, string>
  isActive: boolean
  isSelected: boolean
  projectName: string
  onSelect: (index: number) => void
}

export const SegmentRow = memo(function SegmentRow({
  segment,
  visibleTrackIds,
  trackLabels,
  isActive,
  isSelected,
  projectName,
  onSelect,
}: SegmentRowProps) {
  const updateTranslation = useProjectStore((s) => s.updateTranslation)
  const setSegmentTrackStatus = useProjectStore((s) => s.setSegmentTrackStatus)
  const requestSeek = usePlaybackStore((s) => s.requestSeek)
  const editingCell = useUiStore((s) => s.editingCell)
  const setEditingCell = useUiStore((s) => s.setEditingCell)
  const activeTrackId = useUiStore((s) => s.activeTrackId)

  const handleClick = useCallback(() => {
    onSelect(segment.index)
    requestSeek(segment.startTime)
  }, [segment.index, segment.startTime, onSelect, requestSeek])

  // Build issue context for the active track
  const issueContext = useMemo(() => {
    const trackId = activeTrackId ?? visibleTrackIds[0]
    if (!trackId) return null
    const entry = segment.tracks[trackId]
    if (!entry) return null
    return {
      segmentIndex: segment.index,
      startTime: segment.startTime,
      endTime: segment.endTime,
      sourceText: segment.source,
      trackId,
      trackLabel: trackLabels[trackId] ?? trackId,
      currentTranslation: entry.edited ?? entry.original,
      projectName,
    }
  }, [segment, activeTrackId, visibleTrackIds, trackLabels, projectName])

  return (
    <div
      className={cn(
        'grid gap-2 items-start px-3 py-2 border-b text-sm cursor-pointer transition-colors',
        isActive && 'bg-accent',
        isSelected && !isActive && 'bg-muted/50',
        !isActive && !isSelected && 'hover:bg-muted/30'
      )}
      style={{
        gridTemplateColumns: `3rem 5rem 1fr ${visibleTrackIds.map(() => '1fr').join(' ')} auto`,
      }}
      onClick={handleClick}
    >
      {/* Index */}
      <span className="text-muted-foreground text-xs tabular-nums pt-0.5">
        {segment.index + 1}
      </span>

      {/* Time */}
      <span className="text-muted-foreground text-xs tabular-nums pt-0.5">
        {formatTime(segment.startTime)}
      </span>

      {/* Source (JP) */}
      <div className="min-w-0 break-words leading-relaxed">{segment.source}</div>

      {/* Track cells */}
      {visibleTrackIds.map((trackId) => {
        const entry = segment.tracks[trackId]
        if (!entry) return <div key={trackId} />

        const isCellEditing =
          editingCell?.segmentIndex === segment.index && editingCell?.trackId === trackId

        return (
          <TrackCell
            key={trackId}
            entry={entry}
            isEditing={isCellEditing}
            isActiveTrack={activeTrackId === trackId}
            onStartEdit={() => setEditingCell({ segmentIndex: segment.index, trackId })}
            onCommitEdit={(text) => {
              updateTranslation(segment.index, trackId, text)
              setEditingCell(null)
            }}
            onCancelEdit={() => setEditingCell(null)}
            onSetStatus={(status: SegmentStatus) => setSegmentTrackStatus(segment.index, trackId, status)}
          />
        )
      })}

      {/* Actions */}
      <div className="w-8">
        {issueContext && <ActionsCell issueContext={issueContext} />}
      </div>
    </div>
  )
})
