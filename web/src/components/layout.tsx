import { Toolbar } from '@/components/toolbar'
import { VideoPlayer } from '@/components/video-player'
import { FilterBar } from '@/components/subtitle-table'
import { SubtitleTable } from '@/components/subtitle-table'
import { StatusBar } from '@/components/status-bar'
import { useProjectStore } from '@/stores/project-store'

export function Layout() {
  const isLoaded = useProjectStore((s) => s.isLoaded)

  return (
    <div className="flex flex-col h-screen">
      <Toolbar />
      <VideoPlayer />
      {isLoaded && (
        <>
          <FilterBar />
          <SubtitleTable />
          <StatusBar />
        </>
      )}
    </div>
  )
}
