import { useEffect, useRef, useState, useCallback } from 'react'
import WaveSurfer from 'wavesurfer.js'
import RegionsPlugin, { type Region } from 'wavesurfer.js/dist/plugins/regions.js'
import { useProjectStore } from '@/stores/project-store'
import { usePlaybackStore } from '@/stores/playback-store'
import { useUiStore } from '@/stores/ui-store'
import type { SegmentStatus } from '@/types'

const STATUS_COLORS: Record<SegmentStatus, { normal: string; active: string }> = {
  approved: {
    normal: 'rgba(34, 197, 94, 0.25)',
    active: 'rgba(34, 197, 94, 0.5)',
  },
  pending: {
    normal: 'rgba(156, 163, 175, 0.25)',
    active: 'rgba(156, 163, 175, 0.5)',
  },
  'needs-revision': {
    normal: 'rgba(234, 179, 8, 0.25)',
    active: 'rgba(234, 179, 8, 0.5)',
  },
  rejected: {
    normal: 'rgba(239, 68, 68, 0.25)',
    active: 'rgba(239, 68, 68, 0.5)',
  },
}

export function WaveformTimeline() {
  const videoUrl = useProjectStore((s) => s.videoUrl)
  const showWaveform = useUiStore((s) => s.showWaveform)

  if (!videoUrl || !showWaveform) return null

  return <WaveformInner videoUrl={videoUrl} />
}

function WaveformInner({ videoUrl }: { videoUrl: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WaveSurfer | null>(null)
  const regionsRef = useRef<RegionsPlugin | null>(null)
  const regionMapRef = useRef<Map<number, Region>>(new Map())
  const lastSyncedTime = useRef(0)

  const [ready, setReady] = useState(false)
  const [minPxPerSec, setMinPxPerSec] = useState(0)

  const segments = useProjectStore((s) => s.segments)
  const activeSegmentIndex = usePlaybackStore((s) => s.activeSegmentIndex)
  const activeTrackId = useUiStore((s) => s.activeTrackId)
  const requestSeek = usePlaybackStore((s) => s.requestSeek)

  // Init / teardown wavesurfer
  useEffect(() => {
    if (!containerRef.current) return

    const regions = RegionsPlugin.create()
    regionsRef.current = regions

    const ws = WaveSurfer.create({
      container: containerRef.current,
      height: 128,
      waveColor: 'hsl(215, 20%, 55%)',
      progressColor: 'hsl(215, 50%, 45%)',
      cursorColor: 'hsl(215, 80%, 60%)',
      cursorWidth: 2,
      barWidth: 2,
      barGap: 1,
      barRadius: 2,
      normalize: true,
      interact: true,
      autoScroll: true,
      autoCenter: true,
      plugins: [regions],
    })

    wsRef.current = ws

    ws.on('ready', () => setReady(true))

    ws.on('interaction', (newTime: number) => {
      requestSeek(newTime)
    })

    ws.load(videoUrl)

    return () => {
      regionMapRef.current.clear()
      ws.destroy()
      wsRef.current = null
      regionsRef.current = null
      setReady(false)
    }
  }, [videoUrl, requestSeek])

  // Sync cursor to playback time
  useEffect(() => {
    if (!ready) return

    const unsub = usePlaybackStore.subscribe((state) => {
      const ws = wsRef.current
      if (!ws) return
      const time = state.currentTime
      if (Math.abs(time - lastSyncedTime.current) < 0.016) return
      lastSyncedTime.current = time
      ws.setTime(time)
    })

    return unsub
  }, [ready])

  // Create/update regions when segments change
  useEffect(() => {
    const regions = regionsRef.current
    if (!regions || !ready) return

    regions.clearRegions()
    regionMapRef.current.clear()

    for (const seg of segments) {
      // Use active track status for region color, fallback to first track
      const trackId = activeTrackId ?? Object.keys(seg.tracks)[0]
      const status = trackId ? (seg.tracks[trackId]?.status ?? 'pending') : 'pending'
      const colors = STATUS_COLORS[status]
      const isActive = seg.index === activeSegmentIndex

      const region = regions.addRegion({
        start: seg.startTime,
        end: seg.endTime,
        color: isActive ? colors.active : colors.normal,
        drag: false,
        resize: false,
        id: `seg-${seg.index}`,
      })
      regionMapRef.current.set(seg.index, region)
    }
  }, [segments, ready]) // eslint-disable-line react-hooks/exhaustive-deps

  // Update region colors when active segment or track changes
  const updateRegionColors = useCallback(() => {
    for (const seg of segments) {
      const region = regionMapRef.current.get(seg.index)
      if (!region) continue
      const trackId = activeTrackId ?? Object.keys(seg.tracks)[0]
      const status = trackId ? (seg.tracks[trackId]?.status ?? 'pending') : 'pending'
      const colors = STATUS_COLORS[status]
      const isActive = seg.index === activeSegmentIndex
      region.setOptions({ color: isActive ? colors.active : colors.normal })
    }
  }, [segments, activeSegmentIndex, activeTrackId])

  useEffect(() => {
    if (!ready) return
    updateRegionColors()
  }, [ready, updateRegionColors])

  // Zoom
  useEffect(() => {
    const ws = wsRef.current
    if (!ws || !ready) return
    ws.zoom(minPxPerSec)
  }, [minPxPerSec, ready])

  const zoomIn = () => setMinPxPerSec((prev) => Math.min(prev + 50, 500))
  const zoomOut = () => setMinPxPerSec((prev) => Math.max(prev - 50, 0))
  const zoomFit = () => setMinPxPerSec(0)

  return (
    <div className="relative border-b bg-background">
      <div className="absolute top-1 right-2 z-10 flex gap-1">
        <button
          onClick={zoomOut}
          className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted/80"
          title="Zoom out"
        >
          -
        </button>
        <button
          onClick={zoomFit}
          className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted/80"
          title="Fit to view"
        >
          Fit
        </button>
        <button
          onClick={zoomIn}
          className="rounded bg-muted px-1.5 py-0.5 text-xs text-muted-foreground hover:bg-muted/80"
          title="Zoom in"
        >
          +
        </button>
      </div>

      {!ready && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-background/80">
          <p className="text-sm text-muted-foreground">Decoding audio...</p>
        </div>
      )}

      <div ref={containerRef} className="h-[128px]" />
    </div>
  )
}
