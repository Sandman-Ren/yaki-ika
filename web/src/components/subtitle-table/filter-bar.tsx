import { useState, useEffect, useRef } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { useUiStore } from '@/stores/ui-store'
import { useFilteredSegments } from '@/hooks/use-filtered-segments'
import { useProjectStore } from '@/stores/project-store'
import { cn } from '@/lib/utils'
import { Search } from 'lucide-react'
import type { SegmentStatus } from '@/types'

const FILTERS: { value: SegmentStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'approved', label: 'Approved' },
  { value: 'needs-revision', label: 'Revision' },
  { value: 'rejected', label: 'Rejected' },
]

export function FilterBar() {
  const statusFilter = useUiStore((s) => s.statusFilter)
  const setStatusFilter = useUiStore((s) => s.setStatusFilter)
  const setSearchQuery = useUiStore((s) => s.setSearchQuery)
  const totalSegments = useProjectStore((s) => s.segments.length)
  const filteredSegments = useFilteredSegments()

  const [localSearch, setLocalSearch] = useState('')
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(null)

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current)
    debounceRef.current = setTimeout(() => {
      setSearchQuery(localSearch)
    }, 200)
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current)
    }
  }, [localSearch, setSearchQuery])

  return (
    <div className="flex items-center gap-2 border-b px-4 py-2">
      <div className="relative">
        <Search className="absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search..."
          value={localSearch}
          onChange={(e) => setLocalSearch(e.target.value)}
          className="pl-8 h-8 w-56"
        />
      </div>

      <div className="flex items-center gap-1">
        {FILTERS.map((filter) => (
          <Button
            key={filter.value}
            variant={statusFilter === filter.value ? 'secondary' : 'ghost'}
            size="sm"
            className={cn('h-7 text-xs', statusFilter === filter.value && 'font-medium')}
            onClick={() => setStatusFilter(filter.value)}
          >
            {filter.label}
          </Button>
        ))}
      </div>

      <span className="ml-auto text-xs text-muted-foreground">
        {filteredSegments.length === totalSegments
          ? `${totalSegments} segments`
          : `${filteredSegments.length} / ${totalSegments} segments`}
      </span>
    </div>
  )
}
