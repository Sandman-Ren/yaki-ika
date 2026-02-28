import { create } from 'zustand'

interface PlaybackState {
  currentTime: number
  duration: number
  isPlaying: boolean
  activeSegmentIndex: number | null
  seekTarget: number | null
}

interface PlaybackActions {
  setCurrentTime: (time: number) => void
  setDuration: (duration: number) => void
  setIsPlaying: (playing: boolean) => void
  setActiveSegmentIndex: (index: number | null) => void
  requestSeek: (time: number) => void
  clearSeekTarget: () => void
}

export const usePlaybackStore = create<PlaybackState & PlaybackActions>()((set) => ({
  currentTime: 0,
  duration: 0,
  isPlaying: false,
  activeSegmentIndex: null,
  seekTarget: null,

  setCurrentTime: (time) => set({ currentTime: time }),
  setDuration: (duration) => set({ duration }),
  setIsPlaying: (playing) => set({ isPlaying: playing }),
  setActiveSegmentIndex: (index) => set({ activeSegmentIndex: index }),
  requestSeek: (time) => set({ seekTarget: time }),
  clearSeekTarget: () => set({ seekTarget: null }),
}))
