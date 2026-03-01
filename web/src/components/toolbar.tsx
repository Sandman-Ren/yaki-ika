import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ImportDialog } from '@/components/import-dialog'
import { ExportMenu } from '@/components/export-menu'
import { useProjectStore } from '@/stores/project-store'
import { useUiStore } from '@/stores/ui-store'
import { Undo2, Redo2, Keyboard } from 'lucide-react'
import { useMemo } from 'react'

export function Toolbar() {
  const meta = useProjectStore((s) => s.meta)
  const segments = useProjectStore((s) => s.segments)
  const trackMetas = useProjectStore((s) => s.trackMetas)
  const isLoaded = useProjectStore((s) => s.isLoaded)
  const activeTrackId = useUiStore((s) => s.activeTrackId)
  const setShowShortcutsHelp = useUiStore((s) => s.setShowShortcutsHelp)

  // Per-track status counts for the active track
  const stats = useMemo(() => {
    if (!activeTrackId) return null
    let approved = 0
    let pending = 0
    let needsRevision = 0
    let rejected = 0
    for (const seg of segments) {
      const entry = seg.tracks[activeTrackId]
      if (!entry) continue
      switch (entry.status) {
        case 'approved': approved++; break
        case 'pending': pending++; break
        case 'needs-revision': needsRevision++; break
        case 'rejected': rejected++; break
      }
    }
    return { approved, pending, needsRevision, rejected }
  }, [segments, activeTrackId])

  const activeTrackLabel = trackMetas.find((t) => t.id === activeTrackId)?.label

  return (
    <div className="flex items-center gap-3 border-b px-4 py-2">
      <h1 className="text-sm font-semibold truncate min-w-0">
        {isLoaded && meta ? meta.name : 'Yaki-Ika Subtitle Review'}
      </h1>

      {activeTrackLabel && (
        <Badge variant="secondary" className="text-xs">
          {activeTrackLabel}
        </Badge>
      )}

      <div className="flex-1" />

      {isLoaded && stats && (
        <div className="flex items-center gap-1.5">
          <Badge variant="outline" className="bg-status-approved/10 text-status-approved border-status-approved/30">
            {stats.approved} approved
          </Badge>
          <Badge variant="outline" className="bg-status-pending/10 text-status-pending border-status-pending/30">
            {stats.pending} pending
          </Badge>
          {stats.needsRevision > 0 && (
            <Badge variant="outline" className="bg-status-needs-revision/10 text-status-needs-revision border-status-needs-revision/30">
              {stats.needsRevision} revision
            </Badge>
          )}
          {stats.rejected > 0 && (
            <Badge variant="outline" className="bg-status-rejected/10 text-status-rejected border-status-rejected/30">
              {stats.rejected} rejected
            </Badge>
          )}
        </div>
      )}

      {/* Undo/Redo */}
      {isLoaded && (
        <div className="flex items-center gap-0.5">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            title="Undo (Ctrl+Z)"
            onClick={() => useProjectStore.temporal.getState().undo()}
          >
            <Undo2 className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            title="Redo (Ctrl+Shift+Z)"
            onClick={() => useProjectStore.temporal.getState().redo()}
          >
            <Redo2 className="h-4 w-4" />
          </Button>
        </div>
      )}

      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7"
        title="Keyboard shortcuts (?)"
        onClick={() => setShowShortcutsHelp(true)}
      >
        <Keyboard className="h-4 w-4" />
      </Button>

      <ImportDialog />
      <ExportMenu />
    </div>
  )
}
