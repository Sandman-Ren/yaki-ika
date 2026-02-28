import { useRef, useEffect, useCallback } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { useFilteredSegments } from '@/hooks/use-filtered-segments'
import { usePlaybackStore } from '@/stores/playback-store'
import { useUiStore } from '@/stores/ui-store'
import { SegmentRow } from './segment-row'

const ROW_HEIGHT = 64

export function SubtitleTable() {
  const filteredSegments = useFilteredSegments()
  const parentRef = useRef<HTMLDivElement>(null)
  const activeSegmentIndex = usePlaybackStore((s) => s.activeSegmentIndex)
  const selectedSegmentIndex = useUiStore((s) => s.selectedSegmentIndex)
  const setSelectedSegmentIndex = useUiStore((s) => s.setSelectedSegmentIndex)

  const virtualizer = useVirtualizer({
    count: filteredSegments.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 10,
  })

  // Auto-scroll to active segment when it changes
  useEffect(() => {
    if (activeSegmentIndex == null) return

    // Find the position in the filtered list
    const filteredIndex = filteredSegments.findIndex((seg) => seg.index === activeSegmentIndex)
    if (filteredIndex === -1) return

    virtualizer.scrollToIndex(filteredIndex, { align: 'center', behavior: 'smooth' })
  }, [activeSegmentIndex, filteredSegments, virtualizer])

  const handleSelect = useCallback(
    (index: number) => {
      setSelectedSegmentIndex(index)
    },
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
      {/* Header */}
      <div className="grid grid-cols-[3rem_5rem_1fr_1fr_6rem] gap-2 px-3 py-1.5 border-b bg-muted/50 text-xs font-medium text-muted-foreground sticky top-0 z-10">
        <span>#</span>
        <span>Time</span>
        <span>Japanese</span>
        <span>Translation</span>
        <span className="text-right">Status</span>
      </div>

      {/* Virtualized rows */}
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
                  isActive={activeSegmentIndex === segment.index}
                  isSelected={selectedSegmentIndex === segment.index}
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
