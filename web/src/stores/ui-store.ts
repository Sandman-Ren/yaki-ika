import { create } from 'zustand'
import type { SegmentStatus } from '@/types'

interface UiState {
  selectedSegmentIndex: number | null
  statusFilter: SegmentStatus | 'all'
  searchQuery: string
  editingSegmentIndex: number | null
}

interface UiActions {
  setSelectedSegmentIndex: (index: number | null) => void
  setStatusFilter: (filter: SegmentStatus | 'all') => void
  setSearchQuery: (query: string) => void
  setEditingSegmentIndex: (index: number | null) => void
}

export const useUiStore = create<UiState & UiActions>()((set) => ({
  selectedSegmentIndex: null,
  statusFilter: 'all',
  searchQuery: '',
  editingSegmentIndex: null,

  setSelectedSegmentIndex: (index) => set({ selectedSegmentIndex: index }),
  setStatusFilter: (filter) => set({ statusFilter: filter }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setEditingSegmentIndex: (index) => set({ editingSegmentIndex: index }),
}))
