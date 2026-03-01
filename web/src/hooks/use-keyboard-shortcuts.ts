import { useEffect, useCallback } from 'react'
import { useProjectStore } from '@/stores/project-store'
import { usePlaybackStore } from '@/stores/playback-store'
import { useUiStore } from '@/stores/ui-store'
import { useFilteredSegments } from '@/hooks/use-filtered-segments'
import { eventToShortcut } from '@/lib/keyboard'

export function useKeyboardShortcuts() {
  const filteredSegments = useFilteredSegments()

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      const shortcut = eventToShortcut(e)
      const { editingCell, selectedSegmentIndex, activeTrackId, visibleTrackIds } = useUiStore.getState()
      const isEditing = editingCell !== null

      // Don't intercept when typing in other inputs (search bar, dialogs)
      const target = e.target as HTMLElement
      if (target.tagName === 'INPUT' && !target.closest('[data-search-input]')) return
      if (target.tagName === 'SELECT') return

      // In edit mode, only handle Escape (cancel handled by TrackCell)
      if (isEditing) {
        // Let TrackCell handle Enter/Escape/Shift+Enter
        return
      }

      switch (shortcut) {
        case 'Space': {
          e.preventDefault()
          const { isPlaying, setIsPlaying } = usePlaybackStore.getState()
          setIsPlaying(!isPlaying)
          break
        }

        case 'Alt+ArrowLeft': {
          e.preventDefault()
          const { currentTime, requestSeek } = usePlaybackStore.getState()
          requestSeek(Math.max(0, currentTime - 5))
          break
        }

        case 'Alt+ArrowRight': {
          e.preventDefault()
          const { currentTime, duration, requestSeek } = usePlaybackStore.getState()
          requestSeek(Math.min(duration, currentTime + 5))
          break
        }

        case 'ArrowUp': {
          e.preventDefault()
          if (filteredSegments.length === 0) break
          const currentIdx = filteredSegments.findIndex((s) => s.index === selectedSegmentIndex)
          const newIdx = currentIdx <= 0 ? 0 : currentIdx - 1
          useUiStore.getState().setSelectedSegmentIndex(filteredSegments[newIdx].index)
          break
        }

        case 'ArrowDown': {
          e.preventDefault()
          if (filteredSegments.length === 0) break
          const currentIdx = filteredSegments.findIndex((s) => s.index === selectedSegmentIndex)
          const newIdx = currentIdx >= filteredSegments.length - 1 ? filteredSegments.length - 1 : currentIdx + 1
          useUiStore.getState().setSelectedSegmentIndex(filteredSegments[newIdx].index)
          break
        }

        case 'Tab': {
          e.preventDefault()
          if (visibleTrackIds.length === 0) break
          const currentTrackIdx = activeTrackId ? visibleTrackIds.indexOf(activeTrackId) : -1
          const nextIdx = (currentTrackIdx + 1) % visibleTrackIds.length
          useUiStore.getState().setActiveTrackId(visibleTrackIds[nextIdx])
          break
        }

        case 'Shift+Tab': {
          e.preventDefault()
          if (visibleTrackIds.length === 0) break
          const currentTrackIdx = activeTrackId ? visibleTrackIds.indexOf(activeTrackId) : 0
          const prevIdx = currentTrackIdx <= 0 ? visibleTrackIds.length - 1 : currentTrackIdx - 1
          useUiStore.getState().setActiveTrackId(visibleTrackIds[prevIdx])
          break
        }

        case 'Enter': {
          e.preventDefault()
          if (selectedSegmentIndex !== null && activeTrackId) {
            useUiStore.getState().setEditingCell({ segmentIndex: selectedSegmentIndex, trackId: activeTrackId })
          }
          break
        }

        case 'Ctrl+Enter': {
          e.preventDefault()
          if (selectedSegmentIndex !== null && activeTrackId) {
            useProjectStore.getState().setSegmentTrackStatus(selectedSegmentIndex, activeTrackId, 'approved')
            // Advance to next segment
            const currentIdx = filteredSegments.findIndex((s) => s.index === selectedSegmentIndex)
            if (currentIdx < filteredSegments.length - 1) {
              useUiStore.getState().setSelectedSegmentIndex(filteredSegments[currentIdx + 1].index)
            }
          }
          break
        }

        case 'Ctrl+Shift+Enter': {
          e.preventDefault()
          if (selectedSegmentIndex !== null && activeTrackId) {
            useProjectStore.getState().setSegmentTrackStatus(selectedSegmentIndex, activeTrackId, 'needs-revision')
            const currentIdx = filteredSegments.findIndex((s) => s.index === selectedSegmentIndex)
            if (currentIdx < filteredSegments.length - 1) {
              useUiStore.getState().setSelectedSegmentIndex(filteredSegments[currentIdx + 1].index)
            }
          }
          break
        }

        case 'Ctrl+Z': {
          e.preventDefault()
          useProjectStore.temporal.getState().undo()
          break
        }

        case 'Ctrl+Shift+Z': {
          e.preventDefault()
          useProjectStore.temporal.getState().redo()
          break
        }

        case 'Ctrl+F': {
          e.preventDefault()
          const searchInput = document.querySelector('[data-search-input]') as HTMLInputElement | null
          searchInput?.focus()
          break
        }

        case '?': {
          e.preventDefault()
          const { showShortcutsHelp, setShowShortcutsHelp } = useUiStore.getState()
          setShowShortcutsHelp(!showShortcutsHelp)
          break
        }
      }
    },
    [filteredSegments]
  )

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [handleKeyDown])
}
