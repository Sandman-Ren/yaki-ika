import { useProjectStore } from '@/stores/project-store'

export function StatusBar() {
  const segments = useProjectStore((s) => s.segments)

  const total = segments.length
  const approved = segments.filter((s) => s.status === 'approved').length
  const pending = segments.filter((s) => s.status === 'pending').length
  const needsRevision = segments.filter((s) => s.status === 'needs-revision').length
  const rejected = segments.filter((s) => s.status === 'rejected').length
  const pct = total > 0 ? Math.round((approved / total) * 100) : 0

  return (
    <div className="flex items-center gap-4 border-t bg-muted/30 px-4 py-1.5 text-xs text-muted-foreground">
      <span>{total} segments</span>
      <span className="text-status-approved">{approved} approved</span>
      <span className="text-status-pending">{pending} pending</span>
      {needsRevision > 0 && (
        <span className="text-status-needs-revision">{needsRevision} needs revision</span>
      )}
      {rejected > 0 && (
        <span className="text-status-rejected">{rejected} rejected</span>
      )}
      <span className="ml-auto font-medium">{pct}% complete</span>
    </div>
  )
}
