import { create } from 'zustand'
import type { SegmentStatus } from '@/types'

interface EditingCell {
  segmentIndex: number
  trackId: string
}

interface UiState {
  // Selection
  selectedSegmentIndex: number | null
  // Filtering
  statusFilter: SegmentStatus | 'all'
  searchQuery: string
  // Editing
  editingCell: EditingCell | null
  // Track display
  activeTrackId: string | null
  visibleTrackIds: string[]
  // Panels
  showWaveform: boolean
  showShortcutsHelp: boolean
}

interface UiActions {
  setSelectedSegmentIndex: (index: number | null) => void
  setStatusFilter: (filter: SegmentStatus | 'all') => void
  setSearchQuery: (query: string) => void
  setEditingCell: (cell: EditingCell | null) => void
  setActiveTrackId: (trackId: string | null) => void
  setVisibleTrackIds: (trackIds: string[]) => void
  setShowWaveform: (show: boolean) => void
  setShowShortcutsHelp: (show: boolean) => void
}

export const useUiStore = create<UiState & UiActions>()((set) => ({
  selectedSegmentIndex: null,
  statusFilter: 'all',
  searchQuery: '',
  editingCell: null,
  activeTrackId: null,
  visibleTrackIds: [],
  showWaveform: true,
  showShortcutsHelp: false,

  setSelectedSegmentIndex: (index) => set({ selectedSegmentIndex: index }),
  setStatusFilter: (filter) => set({ statusFilter: filter }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setEditingCell: (cell) => set({ editingCell: cell }),
  setActiveTrackId: (trackId) => set({ activeTrackId: trackId }),
  setVisibleTrackIds: (trackIds) => set({ visibleTrackIds: trackIds }),
  setShowWaveform: (show) => set({ showWaveform: show }),
  setShowShortcutsHelp: (show) => set({ showShortcutsHelp: show }),
}))
