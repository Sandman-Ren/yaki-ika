// ---- Language ----

/** Well-known language codes. Extensible via string union. */
export type LanguageCode = 'ja' | 'en' | 'zh-CN' | 'zh-TW' | (string & {})

/** Display labels for known languages */
export const LANGUAGE_LABELS: Record<string, string> = {
  ja: '日本語',
  en: 'English',
  'zh-CN': '简体中文',
  'zh-TW': '繁體中文',
}

// ---- Track metadata ----

export interface TrackMeta {
  /** Unique ID for this track within the project, e.g. "en", "zh-CN" */
  id: string
  /** Display label, e.g. "English" */
  label: string
  /** Language code */
  lang: LanguageCode
  /** Original filename the SRT was loaded from */
  sourceFile: string
}

// ---- Segment status ----

export type SegmentStatus = 'pending' | 'approved' | 'needs-revision' | 'rejected'

export const SEGMENT_STATUSES: SegmentStatus[] = ['pending', 'approved', 'needs-revision', 'rejected']

// ---- Per-track translation for a single segment ----

export interface TrackEntry {
  /** The machine-translated text as imported */
  original: string
  /** User's edited text, or null if unchanged */
  edited: string | null
  /** Review status for this specific track+segment combo */
  status: SegmentStatus
}

// ---- Core segment ----

export interface Segment {
  /** 0-based index matching SRT block number */
  index: number
  /** Start time in seconds */
  startTime: number
  /** End time in seconds */
  endTime: number
  /** Japanese source text */
  source: string
  /** Per-track translation data, keyed by track ID */
  tracks: Record<string, TrackEntry>
}

// ---- Glossary ----

export interface GlossaryTerm {
  jp: string
  target: string
  category: string
  notes?: string
}

// ---- Project metadata ----

export interface ProjectMeta {
  name: string
  createdAt: string
  lastModifiedAt: string
  /** Ordered track IDs for column display */
  trackOrder: string[]
}

// ---- Import types ----

export interface ImportTrackFile {
  file: File
  lang: LanguageCode
  label: string
}

export interface ImportFiles {
  video: File
  jaSrt: File
  translationSrts: ImportTrackFile[]
  termsFile?: File
}
