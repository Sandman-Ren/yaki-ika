import { Badge } from '@/components/ui/badge'
import { ImportDialog } from '@/components/import-dialog'
import { ExportButton } from '@/components/export-button'
import { useProjectStore } from '@/stores/project-store'

export function Toolbar() {
  const projectName = useProjectStore((s) => s.projectName)
  const segments = useProjectStore((s) => s.segments)
  const isLoaded = useProjectStore((s) => s.isLoaded)

  const approved = segments.filter((s) => s.status === 'approved').length
  const pending = segments.filter((s) => s.status === 'pending').length
  const rejected = segments.filter((s) => s.status === 'rejected').length
  const needsRevision = segments.filter((s) => s.status === 'needs-revision').length

  return (
    <div className="flex items-center gap-3 border-b px-4 py-2">
      <h1 className="text-sm font-semibold truncate min-w-0">
        {isLoaded ? projectName : 'Yaki-Ika Subtitle Review'}
      </h1>

      <div className="flex-1" />

      {isLoaded && (
        <div className="flex items-center gap-1.5">
          <Badge variant="outline" className="bg-status-approved/10 text-status-approved border-status-approved/30">
            {approved} approved
          </Badge>
          <Badge variant="outline" className="bg-status-pending/10 text-status-pending border-status-pending/30">
            {pending} pending
          </Badge>
          {needsRevision > 0 && (
            <Badge variant="outline" className="bg-status-needs-revision/10 text-status-needs-revision border-status-needs-revision/30">
              {needsRevision} revision
            </Badge>
          )}
          {rejected > 0 && (
            <Badge variant="outline" className="bg-status-rejected/10 text-status-rejected border-status-rejected/30">
              {rejected} rejected
            </Badge>
          )}
        </div>
      )}

      <ImportDialog />
      <ExportButton />
    </div>
  )
}
