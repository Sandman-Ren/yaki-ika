import { memo, useState, useCallback, useRef, useEffect } from 'react'
import type { Segment, SegmentStatus } from '@/types'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useProjectStore } from '@/stores/project-store'
import { usePlaybackStore } from '@/stores/playback-store'
import { useUiStore } from '@/stores/ui-store'
import { cn } from '@/lib/utils'
import { formatTime } from '@/lib/srt'

interface SegmentRowProps {
  segment: Segment
  isActive: boolean
  isSelected: boolean
  onSelect: (index: number) => void
  style?: React.CSSProperties
}

const STATUS_CONFIG: Record<SegmentStatus, { label: string; className: string }> = {
  pending: {
    label: 'Pending',
    className: 'bg-status-pending/15 text-status-pending border-status-pending/30 hover:bg-status-pending/25',
  },
  approved: {
    label: 'Approved',
    className: 'bg-status-approved/15 text-status-approved border-status-approved/30 hover:bg-status-approved/25',
  },
  'needs-revision': {
    label: 'Revision',
    className: 'bg-status-needs-revision/15 text-status-needs-revision border-status-needs-revision/30 hover:bg-status-needs-revision/25',
  },
  rejected: {
    label: 'Rejected',
    className: 'bg-status-rejected/15 text-status-rejected border-status-rejected/30 hover:bg-status-rejected/25',
  },
}

const ALL_STATUSES: SegmentStatus[] = ['pending', 'approved', 'needs-revision', 'rejected']

export const SegmentRow = memo(function SegmentRow({
  segment,
  isActive,
  isSelected,
  onSelect,
  style,
}: SegmentRowProps) {
  const updateTranslation = useProjectStore((s) => s.updateTranslation)
  const setSegmentStatus = useProjectStore((s) => s.setSegmentStatus)
  const requestSeek = usePlaybackStore((s) => s.requestSeek)
  const editingIndex = useUiStore((s) => s.editingSegmentIndex)
  const setEditingIndex = useUiStore((s) => s.setEditingSegmentIndex)

  const isEditing = editingIndex === segment.index
  const [editText, setEditText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const startEditing = useCallback(() => {
    setEditText(segment.editedTranslation ?? segment.translated)
    setEditingIndex(segment.index)
  }, [segment, setEditingIndex])

  useEffect(() => {
    if (isEditing && textareaRef.current) {
      textareaRef.current.focus()
      textareaRef.current.select()
    }
  }, [isEditing])

  const commitEdit = useCallback(() => {
    const trimmed = editText.trim()
    // Only save if changed from original
    if (trimmed !== segment.translated) {
      updateTranslation(segment.index, trimmed)
    } else {
      updateTranslation(segment.index, '')
    }
    setEditingIndex(null)
  }, [editText, segment, updateTranslation, setEditingIndex])

  const cancelEdit = useCallback(() => {
    setEditingIndex(null)
  }, [setEditingIndex])

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault()
        commitEdit()
      } else if (e.key === 'Escape') {
        cancelEdit()
      }
    },
    [commitEdit, cancelEdit]
  )

  const config = STATUS_CONFIG[segment.status]

  return (
    <div
      style={style}
      className={cn(
        'grid grid-cols-[3rem_5rem_1fr_1fr_6rem] gap-2 items-start px-3 py-2 border-b text-sm cursor-pointer transition-colors',
        isActive && 'bg-accent',
        isSelected && !isActive && 'bg-muted/50',
        !isActive && !isSelected && 'hover:bg-muted/30'
      )}
      onClick={() => {
        onSelect(segment.index)
        requestSeek(segment.startTime)
      }}
    >
      {/* Index */}
      <span className="text-muted-foreground text-xs tabular-nums pt-0.5">
        {segment.index + 1}
      </span>

      {/* Time */}
      <span className="text-muted-foreground text-xs tabular-nums pt-0.5">
        {formatTime(segment.startTime)}
      </span>

      {/* JP Original */}
      <div className="min-w-0 break-words leading-relaxed">{segment.original}</div>

      {/* Translation (editable) */}
      <div className="min-w-0" onDoubleClick={startEditing}>
        {isEditing ? (
          <textarea
            ref={textareaRef}
            value={editText}
            onChange={(e) => setEditText(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={commitEdit}
            className="w-full resize-none rounded border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            rows={2}
          />
        ) : (
          <span className={cn('leading-relaxed', segment.editedTranslation && 'text-blue-600 dark:text-blue-400')}>
            {segment.editedTranslation || segment.translated}
          </span>
        )}
      </div>

      {/* Status */}
      <div className="flex justify-end">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button type="button">
              <Badge variant="outline" className={cn('cursor-pointer text-xs', config.className)}>
                {config.label}
              </Badge>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            {ALL_STATUSES.map((status) => (
              <DropdownMenuItem
                key={status}
                onClick={(e) => {
                  e.stopPropagation()
                  setSegmentStatus(segment.index, status)
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
