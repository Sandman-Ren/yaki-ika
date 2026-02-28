export type SegmentStatus = 'pending' | 'approved' | 'needs-revision' | 'rejected'

export interface Segment {
  index: number
  startTime: number
  endTime: number
  original: string
  translated: string
  editedTranslation: string | null
  status: SegmentStatus
}

export interface GlossaryTerm {
  jp: string
  target: string
  category: string
  notes?: string
}
