import { useRef, useEffect, useCallback, useMemo } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useFilteredSegments } from '@/hooks/use-filtered-segments'
import { useProjectStore } from '@/stores/project-store'
import { usePlaybackStore } from '@/stores/playback-store'
import { useUiStore } from '@/stores/ui-store'
import { TableHeader } from './table-header'
import { SegmentRow } from './segment-row'

const ROW_HEIGHT = 80

export function SubtitleTable() {
  const filteredSegments = useFilteredSegments()
  const parentRef = useRef<HTMLDivElement>(null)
  const activeSegmentIndex = usePlaybackStore((s) => s.activeSegmentIndex)
  const selectedSegmentIndex = useUiStore((s) => s.selectedSegmentIndex)
  const setSelectedSegmentIndex = useUiStore((s) => s.setSelectedSegmentIndex)
  const visibleTrackIds = useUiStore((s) => s.visibleTrackIds)
  const trackMetas = useProjectStore((s) => s.trackMetas)
  const projectName = useProjectStore((s) => s.meta?.name ?? '')

  const trackLabels = useMemo(() => {
    const labels: Record<string, string> = {}
    for (const t of trackMetas) {
      labels[t.id] = t.label
    }
    return labels
  }, [trackMetas])

  const virtualizer = useVirtualizer({
    count: filteredSegments.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 10,
  })

  // Auto-scroll to active segment
  useEffect(() => {
    if (activeSegmentIndex == null) return
    const filteredIndex = filteredSegments.findIndex((seg) => seg.index === activeSegmentIndex)
    if (filteredIndex === -1) return
    virtualizer.scrollToIndex(filteredIndex, { align: 'center', behavior: 'smooth' })
  }, [activeSegmentIndex, filteredSegments, virtualizer])

  const handleSelect = useCallback(
    (index: number) => setSelectedSegmentIndex(index),
    [setSelectedSegmentIndex]
  )

  if (filteredSegments.length === 0) {
    return (
      <div className="flex items-center justify-center flex-1 text-sm text-muted-foreground">
        No segments to display
      </div>
    )
  }

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <TableHeader trackMetas={trackMetas} visibleTrackIds={visibleTrackIds} />

      <div ref={parentRef} className="flex-1 overflow-auto">
        <div
          style={{
            height: `${virtualizer.getTotalSize()}px`,
            width: '100%',
            position: 'relative',
          }}
        >
          {virtualizer.getVirtualItems().map((virtualRow) => {
            const segment = filteredSegments[virtualRow.index]
            return (
              <div
                key={segment.index}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  height: `${virtualRow.size}px`,
                  transform: `translateY(${virtualRow.start}px)`,
                }}
              >
                <SegmentRow
                  segment={segment}
                  visibleTrackIds={visibleTrackIds}
                  trackLabels={trackLabels}
                  isActive={activeSegmentIndex === segment.index}
                  isSelected={selectedSegmentIndex === segment.index}
                  projectName={projectName}
                  onSelect={handleSelect}
                />
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
