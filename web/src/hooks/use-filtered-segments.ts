import { useMemo } from 'react'
import { useProjectStore } from '@/stores/project-store'
import { useUiStore } from '@/stores/ui-store'
import type { Segment } from '@/types'

export function useFilteredSegments(): Segment[] {
  const segments = useProjectStore((s) => s.segments)
  const statusFilter = useUiStore((s) => s.statusFilter)
  const searchQuery = useUiStore((s) => s.searchQuery)
  const activeTrackId = useUiStore((s) => s.activeTrackId)

  return useMemo(() => {
    let filtered = segments

    // Filter by status on the active track (or any track if none active)
    if (statusFilter !== 'all') {
      filtered = filtered.filter((seg) => {
        if (activeTrackId) {
          return seg.tracks[activeTrackId]?.status === statusFilter
        }
        // If no active track, match if any track has the status
        return Object.values(seg.tracks).some((t) => t.status === statusFilter)
      })
    }

    if (searchQuery.trim()) {
      const query = searchQuery.trim().toLowerCase()
      filtered = filtered.filter((seg) => {
        // Search source text
        if (seg.source.toLowerCase().includes(query)) return true
        // Search all track translations
        for (const entry of Object.values(seg.tracks)) {
          if (entry.original.toLowerCase().includes(query)) return true
          if (entry.edited?.toLowerCase().includes(query)) return true
        }
        return false
      })
    }

    return filtered
  }, [segments, statusFilter, searchQuery, activeTrackId])
}
