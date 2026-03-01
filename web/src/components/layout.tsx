import { Toolbar } from '@/components/toolbar'
import { VideoPlayer } from '@/components/video-player'
import { WelcomeScreen } from '@/components/welcome-screen'
import { WaveformTimeline } from '@/components/waveform-timeline'
import { FilterBar, SubtitleTable } from '@/components/subtitle-table'
import { StatusBar } from '@/components/status-bar'
import { ShortcutsHelpDialog } from '@/components/shortcuts-help-dialog'
import { useProjectStore } from '@/stores/project-store'

export function Layout() {
  const isLoaded = useProjectStore((s) => s.isLoaded)
  const videoUrl = useProjectStore((s) => s.videoUrl)

  return (
    <div className="flex flex-col h-screen">
      <Toolbar />
      {videoUrl ? <VideoPlayer /> : <WelcomeScreen />}
      {isLoaded && (
        <>
          <WaveformTimeline />
          <FilterBar />
          <SubtitleTable />
          <StatusBar />
        </>
      )}
      <ShortcutsHelpDialog />
    </div>
  )
}
