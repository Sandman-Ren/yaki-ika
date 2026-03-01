import type { TrackMeta } from '@/types'
import { useUiStore } from '@/stores/ui-store'
import { cn } from '@/lib/utils'

interface TableHeaderProps {
  trackMetas: TrackMeta[]
  visibleTrackIds: string[]
}

export function TableHeader({ trackMetas, visibleTrackIds }: TableHeaderProps) {
  const activeTrackId = useUiStore((s) => s.activeTrackId)
  const setActiveTrackId = useUiStore((s) => s.setActiveTrackId)

  const visibleTracks = trackMetas.filter((t) => visibleTrackIds.includes(t.id))

  return (
    <div
      className="grid gap-2 px-3 py-1.5 border-b bg-muted/50 text-xs font-medium text-muted-foreground sticky top-0 z-10"
      style={{
        gridTemplateColumns: `3rem 5rem 1fr ${visibleTracks.map(() => '1fr').join(' ')} auto`,
      }}
    >
      <span>#</span>
      <span>Time</span>
      <span>Japanese</span>
      {visibleTracks.map((track) => (
        <span
          key={track.id}
          className={cn(
            'cursor-pointer hover:text-foreground transition-colors',
            activeTrackId === track.id && 'text-foreground font-semibold'
          )}
          onClick={() => setActiveTrackId(track.id)}
          title={`${track.label} (${track.lang})`}
        >
          {track.label}
        </span>
      ))}
      <span className="w-8" />
    </div>
  )
}
