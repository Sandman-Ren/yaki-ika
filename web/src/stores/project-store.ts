import { create } from 'zustand'
import { temporal } from 'zundo'
import type { Segment, SegmentStatus, GlossaryTerm, TrackMeta, ProjectMeta, ImportFiles } from '@/types'
import { buildProject } from '@/lib/srt'
import { readFileAsText, parseTermsFile, createVideoUrl, revokeVideoUrl } from '@/lib/file-loader'
import { saveProject as saveToIDB, loadLatestProject } from '@/lib/persistence'

interface ProjectState {
  meta: ProjectMeta | null
  segments: Segment[]
  trackMetas: TrackMeta[]
  terms: GlossaryTerm[]
  videoUrl: string | null
  videoFileName: string | null
  isLoaded: boolean
  warnings: string[]
}

interface ProjectActions {
  // Import
  loadProject: (files: ImportFiles) => Promise<void>
  reloadVideo: (file: File) => void

  // Multi-track editing
  updateTranslation: (segmentIndex: number, trackId: string, text: string) => void
  setSegmentTrackStatus: (segmentIndex: number, trackId: string, status: SegmentStatus) => void

  // Track management
  removeTrack: (trackId: string) => void
  reorderTracks: (trackOrder: string[]) => void

  // Project lifecycle
  resetProject: () => void

  // Persistence
  saveToIndexedDB: () => Promise<void>
  loadFromIndexedDB: () => Promise<boolean>
}

const initialState: ProjectState = {
  meta: null,
  segments: [],
  trackMetas: [],
  terms: [],
  videoUrl: null,
  videoFileName: null,
  isLoaded: false,
  warnings: [],
}

export const useProjectStore = create<ProjectState & ProjectActions>()(
  temporal(
    (set, get) => ({
      ...initialState,

      loadProject: async ({ video, jaSrt, translationSrts, termsFile }) => {
        // Clean up previous video URL
        const prevUrl = get().videoUrl
        if (prevUrl) revokeVideoUrl(prevUrl)

        // Read all files in parallel
        const [jaContent, ...translatedContents] = await Promise.all([
          readFileAsText(jaSrt),
          ...translationSrts.map((t) => readFileAsText(t.file)),
        ])

        // Build multi-track project
        const tracks = translationSrts.map((t, i) => ({
          id: t.lang,
          label: t.label,
          lang: t.lang,
          sourceFile: t.file.name,
          content: translatedContents[i],
        }))

        const { segments, trackMetas, warnings } = buildProject(jaContent, tracks)
        const terms = termsFile ? await parseTermsFile(termsFile) : []
        const videoUrl = createVideoUrl(video)
        const projectName = video.name.replace(/\.[^.]+$/, '')
        const now = new Date().toISOString()

        const meta: ProjectMeta = {
          name: projectName,
          createdAt: now,
          lastModifiedAt: now,
          trackOrder: trackMetas.map((t) => t.id),
        }

        set({
          meta,
          segments,
          trackMetas,
          terms,
          videoUrl,
          videoFileName: video.name,
          isLoaded: true,
          warnings,
        })
      },

      reloadVideo: (file) => {
        const prevUrl = get().videoUrl
        if (prevUrl) revokeVideoUrl(prevUrl)
        set({ videoUrl: createVideoUrl(file), videoFileName: file.name })
      },

      updateTranslation: (segmentIndex, trackId, text) => {
        set((state) => ({
          segments: state.segments.map((seg) =>
            seg.index === segmentIndex
              ? {
                  ...seg,
                  tracks: {
                    ...seg.tracks,
                    [trackId]: { ...seg.tracks[trackId], edited: text },
                  },
                }
              : seg
          ),
          meta: state.meta ? { ...state.meta, lastModifiedAt: new Date().toISOString() } : state.meta,
        }))
      },

      setSegmentTrackStatus: (segmentIndex, trackId, status) => {
        set((state) => ({
          segments: state.segments.map((seg) =>
            seg.index === segmentIndex
              ? {
                  ...seg,
                  tracks: {
                    ...seg.tracks,
                    [trackId]: { ...seg.tracks[trackId], status },
                  },
                }
              : seg
          ),
          meta: state.meta ? { ...state.meta, lastModifiedAt: new Date().toISOString() } : state.meta,
        }))
      },

      removeTrack: (trackId) => {
        set((state) => ({
          trackMetas: state.trackMetas.filter((t) => t.id !== trackId),
          meta: state.meta
            ? { ...state.meta, trackOrder: state.meta.trackOrder.filter((id) => id !== trackId) }
            : state.meta,
          segments: state.segments.map((seg) => {
            const { [trackId]: _, ...rest } = seg.tracks
            return { ...seg, tracks: rest }
          }),
        }))
      },

      reorderTracks: (trackOrder) => {
        set((state) => ({
          meta: state.meta ? { ...state.meta, trackOrder } : state.meta,
        }))
      },

      resetProject: () => {
        const prevUrl = get().videoUrl
        if (prevUrl) revokeVideoUrl(prevUrl)
        set(initialState)
      },

      saveToIndexedDB: async () => {
        const { meta, segments, trackMetas, terms, videoFileName } = get()
        if (!meta) return
        await saveToIDB(meta.name, {
          meta: { ...meta, lastModifiedAt: new Date().toISOString() },
          segments,
          trackMetas,
          terms,
          videoFileName,
        })
      },

      loadFromIndexedDB: async () => {
        const result = await loadLatestProject()
        if (!result) return false

        const { data } = result
        set({
          meta: data.meta,
          segments: data.segments,
          trackMetas: data.trackMetas,
          terms: data.terms,
          videoUrl: null,
          videoFileName: data.videoFileName,
          isLoaded: true,
          warnings: [],
        })
        return true
      },
    }),
    {
      // Only track segment changes for undo/redo
      partialize: (state) => ({ segments: state.segments }),
    }
  )
)
