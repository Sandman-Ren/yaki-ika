import { memo, useState, useCallback, useRef, useEffect } from 'react'
import type { TrackEntry, SegmentStatus } from '@/types'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'

const STATUS_CONFIG: Record<SegmentStatus, { label: string; dot: string; className: string }> = {
  pending: {
    label: 'Pending',
    dot: 'bg-status-pending',
    className: 'bg-status-pending/15 text-status-pending border-status-pending/30 hover:bg-status-pending/25',
  },
  approved: {
    label: 'Approved',
    dot: 'bg-status-approved',
    className: 'bg-status-approved/15 text-status-approved border-status-approved/30 hover:bg-status-approved/25',
  },
  'needs-revision': {
    label: 'Revision',
    dot: 'bg-status-needs-revision',
    className: 'bg-status-needs-revision/15 text-status-needs-revision border-status-needs-revision/30 hover:bg-status-needs-revision/25',
  },
  rejected: {
    label: 'Rejected',
    dot: 'bg-status-rejected',
    className: 'bg-status-rejected/15 text-status-rejected border-status-rejected/30 hover:bg-status-rejected/25',
  },
}

const ALL_STATUSES: SegmentStatus[] = ['pending', 'approved', 'needs-revision', 'rejected']

interface TrackCellProps {
  entry: TrackEntry
  isEditing: boolean
  isActiveTrack: boolean
  onStartEdit: () => void
  onCommitEdit: (text: string) => void
  onCancelEdit: () => void
  onSetStatus: (status: SegmentStatus) => void
}

export const TrackCell = memo(function TrackCell({
  entry,
  isEditing,
  isActiveTrack,
  onStartEdit,
  onCommitEdit,
  onCancelEdit,
  onSetStatus,
}: TrackCellProps) {
  const [editText, setEditText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (isEditing) {
      setEditText(entry.edited ?? entry.original)
      // Focus after state update
      requestAnimationFrame(() => {
        textareaRef.current?.focus()
        textareaRef.current?.select()
      })
    }
  }, [isEditing, entry.edited, entry.original])

  const commitEdit = useCallback(() => {
    const trimmed = editText.trim()
    onCommitEdit(trimmed !== entry.original ? trimmed : '')
  }, [editText, entry.original, onCommitEdit])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        commitEdit()
      } else if (e.key === 'Escape') {
        e.preventDefault()
        onCancelEdit()
      }
    },
    [commitEdit, onCancelEdit]
  )

  const config = STATUS_CONFIG[entry.status]
  const displayText = entry.edited || entry.original

  if (isEditing) {
    return (
      <div className="min-w-0">
        <textarea
          ref={textareaRef}
          value={editText}
          onChange={(e) => setEditText(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={commitEdit}
          className="w-full resize-none rounded border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          rows={2}
        />
      </div>
    )
  }

  return (
    <div
      className={cn(
        'min-w-0 relative group',
        isActiveTrack && 'ring-1 ring-primary/20 rounded px-1 -mx-1'
      )}
      onDoubleClick={onStartEdit}
    >
      <span className={cn('leading-relaxed text-sm break-words', entry.edited && 'text-blue-600 dark:text-blue-400')}>
        {displayText}
      </span>

      {/* Status badge — bottom right, always visible */}
      <div className="flex items-center gap-1 mt-0.5">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              type="button"
              className="inline-flex items-center"
              onClick={(e) => e.stopPropagation()}
            >
              <Badge variant="outline" className={cn('cursor-pointer text-[10px] px-1.5 py-0', config.className)}>
                {config.label}
              </Badge>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="min-w-0">
            {ALL_STATUSES.map((status) => (
              <DropdownMenuItem
                key={status}
                onClick={(e) => {
                  e.stopPropagation()
                  onSetStatus(status)
                }}
              >
                <Badge variant="outline" className={cn('mr-2 text-xs', STATUS_CONFIG[status].className)}>
                  {STATUS_CONFIG[status].label}
                </Badge>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
})
