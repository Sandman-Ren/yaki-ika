import { useEffect } from 'react'
import { MediaPlayer, MediaProvider, useMediaPlayer, useMediaRemote } from '@vidstack/react'
import { DefaultVideoLayout, defaultLayoutIcons } from '@vidstack/react/player/layouts/default'
import '@vidstack/react/player/styles/default/theme.css'
import '@vidstack/react/player/styles/default/layouts/video.css'
import { useProjectStore } from '@/stores/project-store'
import { usePlaybackStore } from '@/stores/playback-store'

export function VideoPlayer() {
  const videoUrl = useProjectStore((s) => s.videoUrl)

  if (!videoUrl) {
    return (
      <div className="flex items-center justify-center bg-muted/50 aspect-video max-h-[40vh]">
        <p className="text-sm text-muted-foreground">Import a project to begin</p>
      </div>
    )
  }

  return <VideoPlayerInner src={videoUrl} />
}

function VideoPlayerInner({ src }: { src: string }) {
  return (
    <MediaPlayer
      src={{ src, type: 'video/mp4' }}
      className="aspect-video max-h-[40vh] w-full bg-black"
    >
      <MediaProvider />
      <DefaultVideoLayout icons={defaultLayoutIcons} />
      <TimeSync />
      <SeekHandler />
    </MediaPlayer>
  )
}

function TimeSync() {
  const player = useMediaPlayer()
  const setCurrentTime = usePlaybackStore((s) => s.setCurrentTime)
  const setDuration = usePlaybackStore((s) => s.setDuration)
  const setIsPlaying = usePlaybackStore((s) => s.setIsPlaying)

  useEffect(() => {
    if (!player) return

    return player.subscribe(({ currentTime, duration, paused }) => {
      setCurrentTime(currentTime)
      setDuration(duration)
      setIsPlaying(!paused)
    })
  }, [player, setCurrentTime, setDuration, setIsPlaying])

  return null
}

/** Listens for seekTarget changes in playback store and dispatches seek */
function SeekHandler() {
  const remote = useMediaRemote()
  const seekTarget = usePlaybackStore((s) => s.seekTarget)
  const clearSeekTarget = usePlaybackStore((s) => s.clearSeekTarget)

  useEffect(() => {
    if (seekTarget != null) {
      remote.seek(seekTarget)
      clearSeekTarget()
    }
  }, [seekTarget, remote, clearSeekTarget])

  return null
}
