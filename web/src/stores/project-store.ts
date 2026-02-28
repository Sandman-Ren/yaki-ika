import { create } from 'zustand'
import type { Segment, SegmentStatus, GlossaryTerm } from '@/types'
import { pairSubtitles } from '@/lib/srt'
import { readFileAsText, parseTermsFile, createVideoUrl, revokeVideoUrl } from '@/lib/file-loader'

interface ProjectState {
  segments: Segment[]
  terms: GlossaryTerm[]
  videoUrl: string | null
  projectName: string
  isLoaded: boolean
  warnings: string[]
}

interface ProjectActions {
  loadProject: (files: {
    video: File
    jaSrt: File
    translatedSrt: File
    termsFile?: File
  }) => Promise<void>
  updateTranslation: (index: number, text: string) => void
  setSegmentStatus: (index: number, status: SegmentStatus) => void
  resetProject: () => void
}

const initialState: ProjectState = {
  segments: [],
  terms: [],
  videoUrl: null,
  projectName: '',
  isLoaded: false,
  warnings: [],
}

export const useProjectStore = create<ProjectState & ProjectActions>()((set, get) => ({
  ...initialState,

  loadProject: async ({ video, jaSrt, translatedSrt, termsFile }) => {
    // Clean up previous video URL
    const prevUrl = get().videoUrl
    if (prevUrl) revokeVideoUrl(prevUrl)

    const [jaContent, translatedContent] = await Promise.all([
      readFileAsText(jaSrt),
      readFileAsText(translatedSrt),
    ])

    const { segments, warnings } = pairSubtitles(jaContent, translatedContent)
    const terms = termsFile ? await parseTermsFile(termsFile) : []
    const videoUrl = createVideoUrl(video)

    // Derive project name from video filename (strip extension)
    const projectName = video.name.replace(/\.[^.]+$/, '')

    set({
      segments,
      terms,
      videoUrl,
      projectName,
      isLoaded: true,
      warnings,
    })
  },

  updateTranslation: (index, text) => {
    set((state) => ({
      segments: state.segments.map((seg) =>
        seg.index === index ? { ...seg, editedTranslation: text } : seg
      ),
    }))
  },

  setSegmentStatus: (index, status) => {
    set((state) => ({
      segments: state.segments.map((seg) =>
        seg.index === index ? { ...seg, status } : seg
      ),
    }))
  },

  resetProject: () => {
    const prevUrl = get().videoUrl
    if (prevUrl) revokeVideoUrl(prevUrl)
    set(initialState)
  },
}))
