import { useEffect } from 'react'
import { usePlaybackStore } from '@/stores/playback-store'
import { useProjectStore } from '@/stores/project-store'

/**
 * Syncs the active segment index based on current playback time.
 * Uses binary search for efficient lookup.
 */
export function useActiveSegment() {
  const currentTime = usePlaybackStore((s) => s.currentTime)
  const setActiveSegmentIndex = usePlaybackStore((s) => s.setActiveSegmentIndex)
  const segments = useProjectStore((s) => s.segments)

  useEffect(() => {
    if (segments.length === 0) {
      setActiveSegmentIndex(null)
      return
    }

    // Binary search for the segment containing currentTime
    let lo = 0
    let hi = segments.length - 1
    let result: number | null = null

    while (lo <= hi) {
      const mid = (lo + hi) >>> 1
      const seg = segments[mid]

      if (currentTime >= seg.startTime && currentTime < seg.endTime) {
        result = mid
        break
      } else if (currentTime < seg.startTime) {
        hi = mid - 1
      } else {
        lo = mid + 1
      }
    }

    setActiveSegmentIndex(result)
  }, [currentTime, segments, setActiveSegmentIndex])
}
