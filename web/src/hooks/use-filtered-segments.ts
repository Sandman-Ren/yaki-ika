import { useMemo } from 'react'
import { useProjectStore } from '@/stores/project-store'
import { useUiStore } from '@/stores/ui-store'
import type { Segment } from '@/types'

export function useFilteredSegments(): Segment[] {
  const segments = useProjectStore((s) => s.segments)
  const statusFilter = useUiStore((s) => s.statusFilter)
  const searchQuery = useUiStore((s) => s.searchQuery)

  return useMemo(() => {
    let filtered = segments

    if (statusFilter !== 'all') {
      filtered = filtered.filter((seg) => seg.status === statusFilter)
    }

    if (searchQuery.trim()) {
      const query = searchQuery.trim().toLowerCase()
      filtered = filtered.filter(
        (seg) =>
          seg.original.toLowerCase().includes(query) ||
          seg.translated.toLowerCase().includes(query) ||
          (seg.editedTranslation?.toLowerCase().includes(query) ?? false)
      )
    }

    return filtered
  }, [segments, statusFilter, searchQuery])
}
