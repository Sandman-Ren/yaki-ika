import { useMemo } from 'react'
import { useProjectStore } from '@/stores/project-store'
import { useUiStore } from '@/stores/ui-store'

export function StatusBar() {
  const segments = useProjectStore((s) => s.segments)
  const trackMetas = useProjectStore((s) => s.trackMetas)
  const activeTrackId = useUiStore((s) => s.activeTrackId)

  const stats = useMemo(() => {
    const trackId = activeTrackId ?? trackMetas[0]?.id
    if (!trackId) return null

    const total = segments.length
    let approved = 0
    let pending = 0
    let needsRevision = 0
    let rejected = 0

    for (const seg of segments) {
      const entry = seg.tracks[trackId]
      if (!entry) continue
      switch (entry.status) {
        case 'approved': approved++; break
        case 'pending': pending++; break
        case 'needs-revision': needsRevision++; break
        case 'rejected': rejected++; break
      }
    }

    const pct = total > 0 ? Math.round((approved / total) * 100) : 0
    return { total, approved, pending, needsRevision, rejected, pct }
  }, [segments, trackMetas, activeTrackId])

  if (!stats) return null

  return (
    <div className="flex items-center gap-4 border-t bg-muted/30 px-4 py-1.5 text-xs text-muted-foreground">
      <span>{stats.total} segments</span>
      <span className="text-status-approved">{stats.approved} approved</span>
      <span className="text-status-pending">{stats.pending} pending</span>
      {stats.needsRevision > 0 && (
        <span className="text-status-needs-revision">{stats.needsRevision} needs revision</span>
      )}
      {stats.rejected > 0 && (
        <span className="text-status-rejected">{stats.rejected} rejected</span>
      )}
      <span className="ml-auto font-medium">{stats.pct}% complete</span>
    </div>
  )
}
